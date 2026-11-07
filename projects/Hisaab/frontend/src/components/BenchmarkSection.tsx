import { useEffect, useState } from "react";
import { api, BenchmarkPayload } from "../api";

export default function BenchmarkSection() {
  const [bm, setBm] = useState<BenchmarkPayload | null>(null);

  useEffect(() => {
    api.benchmark().then(setBm).catch(() => setBm(null));
  }, []);

  if (!bm) return null;
  const engines = Object.keys(bm.results);

  return (
    <section className="card">
      <h2>Engine scaling benchmark <span className="muted">— median of {bm.repeat} isolated runs · {bm.machine}</span></h2>
      <table className="tbl">
        <thead>
          <tr>
            <th>Engine</th>
            {bm.scales.map(s => <th key={s}>{s.toLocaleString()} rows</th>)}
          </tr>
        </thead>
        <tbody>
          {engines.map(e => (
            <tr key={e}>
              <td className="platform">{e}</td>
              {bm.scales.map(s => {
                const p = bm.results[e]?.[String(s)];
                return (
                  <td key={s}>
                    {p?.seconds != null
                      ? <><b>{p.seconds.toFixed(p.seconds < 1 ? 3 : 2)}s</b> <span className="muted">/ {p.peak_mb?.toFixed(0)}MB</span></>
                      : <span className="bad">{p?.error?.slice(0, 30) ?? "—"}</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {bm.cost_model && (
        <>
          <h3>Cloud cost model — running the {bm.scales[bm.scales.length - 1].toLocaleString()}-row job</h3>
          <table className="tbl">
            <thead>
              <tr><th>Engine</th><th>Cloud config</th><th>Local (measured)</th><th>Node-hours</th><th>Est. cost</th></tr>
            </thead>
            <tbody>
              {bm.cost_model.map(c => (
                <tr key={c.engine}>
                  <td className="platform">{c.engine}</td>
                  <td>{c.config}</td>
                  <td>{c.measured_local_seconds != null ? `${c.measured_local_seconds.toFixed(2)}s` : "—"}</td>
                  <td>{c.estimated_node_hours.toFixed(3)}</td>
                  <td><b>${c.estimated_cost_usd.toFixed(3)}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="footnote">On-demand list pricing (us-east-1); teaching the shape of the
          trade-off, not a procurement quote.</p>
        </>
      )}

      <p className="footnote">
        Full results: <code>/results/scalability.md</code> · chart:{" "}
        <a href="/results/runtime_chart.png" target="_blank" rel="noreferrer">runtime_chart.png</a>
      </p>
    </section>
  );
}
