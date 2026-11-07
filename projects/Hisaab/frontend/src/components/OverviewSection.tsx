import { useEffect, useState } from "react";
import { api, Overview } from "../api";

const METRICS: { key: keyof Overview["totals"]; label: string; fmt: (v: number) => string }[] = [
  { key: "spend", label: "Spend", fmt: v => compact(v) },
  { key: "revenue", label: "Revenue", fmt: v => compact(v) },
  { key: "roas", label: "ROAS", fmt: v => v.toFixed(2) + "×" },
  { key: "ctr", label: "CTR", fmt: v => pct(v) },
  { key: "cpc", label: "CPC", fmt: v => v.toFixed(2) },
  { key: "cpa", label: "CPA", fmt: v => v.toFixed(1) },
  { key: "cvr", label: "CVR", fmt: v => pct(v) },
  { key: "conversions", label: "Conversions", fmt: v => compact(v) },
];

function compact(v: number): string {
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return v.toFixed(0);
}
function pct(v: number): string {
  return (v * 100).toFixed(v < 0.01 ? 3 : 2) + "%";
}

export default function OverviewSection({ datasetId }: { datasetId: string }) {
  const [ov, setOv] = useState<Overview | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    setOv(null);
    api.overview(datasetId, "platform").then(setOv).catch(e => setErr(String(e.message ?? e)));
  }, [datasetId]);

  if (err) return <section className="card"><p className="err">{err}</p></section>;
  if (!ov) return <section className="card"><p className="muted">loading overview…</p></section>;

  const groups = Object.entries(ov.groups).sort((a, b) => b[1].revenue - a[1].revenue);
  const maxSpend = Math.max(...groups.map(([, g]) => g.spend), 1);
  const maxRoas = Math.max(...groups.map(([, g]) => g.roas), 0.001);

  return (
    <section className="card">
      <h2>Platform performance <span className="muted">— cleaned view of {ov.rows_clean.toLocaleString()} rows ({ov.duplicates_removed.toLocaleString()} duplicates removed)</span></h2>
      <div className="kpi-grid">
        {METRICS.map(m => (
          <div className="kpi" key={m.key}>
            <span className="kpi-label">{m.label}</span>
            <span className="kpi-value">{m.fmt(ov.totals[m.key] as number)}</span>
          </div>
        ))}
      </div>
      <table className="tbl">
        <thead>
          <tr><th>Platform</th><th>Spend</th><th>Revenue</th><th>ROAS</th><th>CTR</th><th>CPC</th><th>CPA</th><th>Spend share</th></tr>
        </thead>
        <tbody>
          {groups.map(([p, g]) => (
            <tr key={p}>
              <td className="platform">{p}</td>
              <td>{compact(g.spend)}</td>
              <td>{compact(g.revenue)}</td>
              <td><span className={g.roas >= 2.5 ? "good" : g.roas >= 1.5 ? "ok" : "bad"}>{g.roas.toFixed(2)}×</span></td>
              <td>{pct(g.ctr)}</td>
              <td>{g.cpc.toFixed(2)}</td>
              <td>{g.cpa.toFixed(1)}</td>
              <td>
                <div className="bar"><div style={{ width: `${(g.spend / maxSpend) * 100}%` }} /></div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="footnote">Currency: {ov.currency}. ROAS bar shading: green ≥ 2.5, amber ≥ 1.5, red below.</p>
      <div className="roas-bars">
        {groups.map(([p, g]) => (
          <div key={p} className="roas-row">
            <span className="roas-label">{p}</span>
            <div className="roas-track">
              <div className={g.roas >= 2.5 ? "fill good" : g.roas >= 1.5 ? "fill ok" : "fill bad"}
                   style={{ width: `${(g.roas / maxRoas) * 100}%` }} />
            </div>
            <span className="roas-val">{g.roas.toFixed(2)}×</span>
          </div>
        ))}
      </div>
    </section>
  );
}
