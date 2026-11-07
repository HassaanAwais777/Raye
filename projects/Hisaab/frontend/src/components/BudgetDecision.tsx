import { useMemo, useState } from "react";
import { api, AllocRow, DatasetRecord, Recommendation } from "../api";

const QUICK: number[] = [50_000, 100_000, 500_000, 1_000_000];

const COLORS: Record<string, string> = {
  google: "#4f46e5", facebook: "#1877f2", instagram: "#e1306c",
  tiktok: "#0d9488", youtube: "#dc2626",
};
const colorOf = (p: string) => COLORS[p] ?? "#64748b";

function fmtMoney(currency: string): (v: number) => string {
  // PKR uses South-Asian lakh/crore grouping (Rs 1,00,000); others standard.
  const sym = currency === "PKR" ? "Rs " : currency === "USD" ? "$" : currency + " ";
  const n = new Intl.NumberFormat(currency === "PKR" ? "en-IN" : "en-US",
    { maximumFractionDigits: 0 });
  return (v: number) => sym + n.format(Math.round(v));
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

type Tone = "good" | "ok" | "bad" | "muted";
function sliceStatus(a: AllocRow): { label: string; tone: Tone } {
  if (a.allocated <= 0)
    return { label: "unfunded at this budget — its curve starts lower", tone: "muted" };
  const avg = a.expected_incremental_revenue / a.allocated;
  if (a.marginal_roas > avg * 1.15)
    return { label: "headroom — next rupee still earns more here", tone: "good" };
  if (a.marginal_roas < avg * 0.85)
    return { label: "saturating — marginal returns thinning", tone: "ok" };
  return { label: "balanced — at the efficient edge", tone: "ok" };
}

/** Donut of the budget split. */
function Donut({ rec, size = 190 }: { rec: Recommendation; size?: number }) {
  const r = 70, C = 2 * Math.PI * r;
  let acc = 0;
  const segs = rec.allocation
    .filter(a => a.share_pct > 0.05)
    .map(a => {
      const len = (a.share_pct / 100) * C;
      const seg = { color: colorOf(a.platform), dash: `${len} ${C - len}`, off: -acc, pct: a.share_pct };
      acc += len;
      return seg;
    });
  return (
    <svg width={size} height={size} viewBox="0 0 180 180" role="img"
         aria-label="budget allocation donut">
      <g transform="rotate(-90 90 90)">
        <circle cx="90" cy="90" r={r} fill="none" stroke="#eef0f6" strokeWidth="26" />
        {segs.map((s, i) => (
          <circle key={i} cx="90" cy="90" r={r} fill="none" stroke={s.color} strokeWidth="26"
                  strokeDasharray={s.dash} strokeDashoffset={s.off} />
        ))}
      </g>
      <text x="90" y="84" textAnchor="middle" className="donut-big">
        {rec.allocation[0] ? rec.allocation[0].share_pct.toFixed(0) + "%" : ""}
      </text>
      <text x="90" y="102" textAnchor="middle" className="donut-small">
        {rec.allocation[0] ? "to " + rec.allocation[0].platform : ""}
      </text>
    </svg>
  );
}

export default function BudgetDecision(props: {
  datasets: DatasetRecord[];
  selected: string;
  onSelect: (id: string) => void;
  onDatasetsChanged: () => void;
  commentsTotal: number | null;
}) {
  const { datasets, selected, onSelect, onDatasetsChanged, commentsTotal } = props;
  const [budget, setBudget] = useState(100_000);
  const [withCi, setWithCi] = useState(true);
  const [sentAware, setSentAware] = useState(true);
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [err, setErr] = useState("");

  const currency = rec?.currency
    ?? datasets.find(d => d.id === selected)?.currency ?? "PKR";
  const money = useMemo(() => fmtMoney(currency), [currency]);

  const createDemo = () => {
    setCreating(true);
    setErr("");
    api.createDataset(100_000, "pk")
      .then(() => onDatasetsChanged())
      .catch(e => setErr(String(e.message ?? e)))
      .finally(() => setCreating(false));
  };

  const run = () => {
    setBusy(true);
    setErr("");
    api.recommend(selected, budget, withCi, sentAware)
      .then(setRec)
      .catch(e => setErr(String(e.message ?? e)))
      .finally(() => setBusy(false));
  };

  // ---- derived narrative pieces ----
  const top = rec?.allocation[0];
  const zeros = rec?.allocation.filter(a => a.allocated <= 0) ?? [];
  const l0 = rec?.baselines?.l0_equal_split?.expected_incremental_revenue;
  const gain = rec && l0 ? ((rec.expected_incremental_revenue - l0) / l0) * 100 : null;
  const movedByRaye = rec?.sentiment
    ? rec.sentiment.allocation.reduce((s, a) => {
        const base = rec.allocation.find(x => x.platform === a.platform)?.allocated ?? 0;
        return s + Math.abs(a.allocated - base);
      }, 0) / 2
    : 0;

  return (
    <section className="card decision" id="decision">
      <div className="decision-head">
        <h2>The decision</h2>
        <p className="decision-q">
          You have <b>{money(budget)}</b> for next month's ads. Where does each rupee go?
        </p>
      </div>

      <div className="controls-row budget-row">
        <label>
          Your budget ({currency})
          <input type="number" min={1000} step={10000} value={budget}
                 onChange={e => setBudget(Math.max(0, Number(e.target.value)))} />
        </label>
        <div className="chips" role="group" aria-label="quick budget presets">
          {QUICK.map(q => (
            <button key={q} type="button"
                    className={"chip" + (budget === q ? " chip-on" : "")}
                    onClick={() => setBudget(q)}>
              {fmtMoney(currency)(q).replace(/\.00$/, "")}
              {q === 100_000 && <span className="chip-note"> 1 lakh</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="controls-row">
        <label>
          Campaign history
          <select value={selected} onChange={e => onSelect(e.target.value)}>
            {datasets.map(d => (
              <option key={d.id} value={d.id}>
                {d.id} — {d.rows.toLocaleString()} rows ({d.locale.toUpperCase()})
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={sentAware}
                 onChange={e => setSentAware(e.target.checked)} />
          Include Raye voice-of-customer
          {commentsTotal != null && <span className="hint-inline"> ({commentsTotal.toLocaleString()} live-scraped comments)</span>}
        </label>
        <label className="check">
          <input type="checkbox" checked={withCi}
                 onChange={e => setWithCi(e.target.checked)} />
          uncertainty bands
        </label>
        <button className="primary" onClick={run} disabled={busy || !selected}>
          {busy ? "optimizing…" : "Allocate my budget →"}
        </button>
        {datasets.length === 0 && (
          <button className="ghost" onClick={createDemo} disabled={creating}>
            {creating ? "generating…" : "no data yet? create a 100k-row demo dataset"}
          </button>
        )}
      </div>

      {err && <p className="err">{err}</p>}
      {rec?.warnings.map((w, i) => <p className="warn" key={i}>⚠ {w}</p>)}

      {!rec && !busy && (
        <div className="decision-preview">
          <p>
            Press <b>Allocate my budget</b> and Hisaab will answer in plain numbers:
            fit each platform's <i>revenue-response curve</i> from your campaign history,
            then water-fill your budget until every platform's <i>marginal return</i> is
            equal — putting the next rupee where it earns the most, and starving platforms
            that have already saturated.
          </p>
        </div>
      )}

      {rec && (
        <div className="answer">
          <p className="verdict">
            {top && <>Put <b style={{ color: colorOf(top.platform) }}>{cap(top.platform)}</b>{" "}
              <b>{money(top.allocated)}</b> ({top.share_pct.toFixed(1)}%) first.
              {zeros.length > 0 && <> The rest stay unfunded at this budget — their first rupee
              returns less than {cap(top.platform)}'s last.{budget < 500_000 && <> A larger
              budget unlocks them (try the 5,00,000 chip).</>}</>}
            </>}
          </p>

          <div className="answer-grid">
            <div className="donut-wrap">
              <Donut rec={rec} />
            </div>

            <div className="alloc-list">
              {rec.allocation.map((a, i) => {
                const st = sliceStatus(a);
                return (
                  <div className="alloc-row" key={a.platform}>
                    <span className="alloc-rank">{i + 1}</span>
                    <span className="alloc-name">
                      <span className="dot" style={{ background: colorOf(a.platform) }} />
                      {cap(a.platform)}
                    </span>
                    <span className="alloc-amount">
                      <b>{money(a.allocated)}</b>
                      <span className="alloc-share">{a.share_pct.toFixed(1)}%</span>
                    </span>
                    <span className={"tone " + st.tone}>{st.label}</span>
                    <details className="why">
                      <summary>why?</summary>
                      <div className="why-body">
                        <p>
                          <b>{money(a.expected_incremental_revenue)}</b> expected
                          incremental revenue from this slice
                          ({(a.expected_incremental_revenue / Math.max(a.allocated, 1)).toFixed(2)}×
                          on this spend) · marginal ROAS at the allocation edge:{" "}
                          <b>{a.marginal_roas.toFixed(3)}×</b>
                        </p>
                        <p className="mono">
                          curve R(s) = α·ln(1 + s/β) + c &nbsp;→&nbsp; α={a.curve_alpha.toFixed(1)},
                          β={a.curve_beta.toFixed(1)}, R²={a.curve_r2.toFixed(3)},
                          {a.weekly_points} weekly points fitted
                          {a.alpha_ci && <> · α 95% CI [{a.alpha_ci[0].toFixed(1)}, {a.alpha_ci[1].toFixed(1)}]</>}
                        </p>
                        {rec.sentiment && (() => {
                          const f = rec.sentiment.platforms.find(x => x.platform === a.platform);
                          if (!f) return null;
                          return f.evidence === "-" ? (
                            <p>
                              Raye sentiment: <b>no direct measurement</b> for this platform —
                              falls back to the global brand index (factor 1.000). No sentiment is invented.
                            </p>
                          ) : (
                            <p>
                              Raye sentiment: <b>{f.n_comments.toLocaleString()}</b> live-scraped{" "}
                              {f.evidence} comments, brand voice {f.net_weighted >= 0 ? "+" : ""}
                              {f.net_weighted.toFixed(3)} ({f.deviation >= 0 ? "+" : ""}
                              {(f.deviation * 100).toFixed(2)}% vs global) → curve scaled{" "}
                              <b>×{f.factor.toFixed(4)}</b>.
                            </p>
                          );
                        })()}
                      </div>
                    </details>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="proof">
            <div className="proof-title">Same budget, split three ways — scored on the same fitted curves:</div>
            <div className="proof-grid">
              {[
                { key: "l0_equal_split", label: "Equal split (gut feel)", v: l0, tone: "bad" as Tone },
                { key: "l2_bayes_shrunk", label: "ROAS-proportional (smarter guess)", v: rec.baselines?.l2_bayes_shrunk?.expected_incremental_revenue, tone: "ok" as Tone },
                { key: "l3", label: "Hisaab water-fill (this allocation)", v: rec.expected_incremental_revenue, tone: "good" as Tone },
              ].map(row => (
                <div className={"proof-cell tone-border-" + row.tone} key={row.key}>
                  <span className="proof-label">{row.label}</span>
                  <span className="proof-val">{row.v != null ? money(row.v) : "—"}</span>
                  <span className="proof-roas">
                    {row.v != null && rec.budget > 0
                      ? (row.v / rec.budget).toFixed(2) + "× incremental ROAS"
                      : ""}
                  </span>
                </div>
              ))}
            </div>
            {gain != null && (
              <p className="proof-line">
                The <b>same {money(rec.budget)}</b>, split equally, leaves{" "}
                <b>{money(Math.max(0, (rec.expected_incremental_revenue ?? 0) - (l0 ?? 0)))}</b> on the table —
                Hisaab's split earns <b>{gain >= 0 ? "+" : ""}{gain.toFixed(1)}%</b> more revenue. No extra budget, just a better answer.
              </p>
            )}
          </div>

          {rec.sentiment && (
            <div className="overlay">
              <h3>Did Raye's 210k-comment voice change the answer?</h3>
              <div className="overlay-grid">
                <div>
                  <div className="overlay-col-title">Performance data only</div>
                  {rec.allocation.map(a => (
                    <div className="mini-row" key={a.platform}>
                      <span className="mini-name">{cap(a.platform)}</span>
                      <div className="mini-track">
                        <div style={{ width: `${a.share_pct * 2}%`, background: colorOf(a.platform) }} />
                      </div>
                      <span className="mini-val">{money(a.allocated)}</span>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="overlay-col-title">
                    With Raye voice-of-customer {movedByRaye > 0.5 && <span className="hint-inline">({money(movedByRaye)} re-allocated)</span>}
                  </div>
                  {rec.sentiment.allocation.map(a => (
                    <div className="mini-row" key={a.platform}>
                      <span className="mini-name">{cap(a.platform)}</span>
                      <div className="mini-track">
                        <div style={{ width: `${a.share_pct * 2}%`, background: colorOf(a.platform) }} />
                      </div>
                      <span className="mini-val">{money(a.allocated)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <p className="overlay-note">
                Expected revenue: {money(rec.expected_incremental_revenue)} →{" "}
                <b>{money(rec.sentiment.expected_incremental_revenue)}</b>{" "}
                ({rec.sentiment.revenue_delta_vs_l3 >= 0 ? "+" : ""}
                {money(rec.sentiment.revenue_delta_vs_l3)} under the same curves). Both columns are scored
                identically — the overlay only re-weights the curves by what{" "}
                {rec.sentiment.comments_total.toLocaleString()} real customers said.
              </p>
            </div>
          )}

          <details className="method">
            <summary>How this answer was computed</summary>
            <p className="footnote">{rec.method}</p>
          </details>
        </div>
      )}
    </section>
  );
}
