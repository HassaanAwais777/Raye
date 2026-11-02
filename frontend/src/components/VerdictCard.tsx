import type { AnalysisResult, Sentiment } from "../types";

const SENTIMENT_COLOR: Record<Sentiment, string> = {
  positive: "#34d399",
  negative: "#f87171",
  mixed: "#fbbf24",
  neutral: "#94a3b8",
};

function labelClass(label: string): string {
  if (label.startsWith("Positive")) return "pos";
  if (label.startsWith("Negative")) return "neg";
  if (label.startsWith("Mixed")) return "mix";
  return "insuf";
}

export default function VerdictCard({ result }: { result: AnalysisResult }) {
  const v = result.verdict;
  const counts = v.sentiment_counts;
  const total = Math.max(1, counts.positive + counts.negative + counts.mixed + counts.neutral);

  // SVG donut
  const R = 52;
  const C = 2 * Math.PI * R;
  let offset = 0;
  const segments = (Object.keys(SENTIMENT_COLOR) as Sentiment[]).map((k) => {
    const frac = (counts[k] || 0) / total;
    const seg = { key: k, frac, offset };
    offset += frac;
    return seg;
  });

  return (
    <section className="card">
      <div className="verdict-head">
        <div className="verdict-main">
          <span className={`verdict-label ${labelClass(v.label)}`}>{v.label}</span>
          <div className="headline">{v.headline}</div>
          <div className="summary">{v.summary}</div>

          {v.status === "insufficient_evidence" && (
            <div className="insufficient-box">
              <b>Honest verdict: not enough data yet.</b> Raye will not pretend to conclude from{" "}
              {result.totals.analyzed.toLocaleString()} comments (minimum{" "}
              {v.confidence.min_reliable_n}). Recommendations:
              <ul>
                {v.recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="donut-wrap">
            <svg width="132" height="132" viewBox="0 0 132 132">
              <circle cx="66" cy="66" r={R} fill="none" stroke="#1a2336" strokeWidth="16" />
              {segments.map(
                (s) =>
                  s.frac > 0 && (
                    <circle
                      key={s.key}
                      cx="66"
                      cy="66"
                      r={R}
                      fill="none"
                      stroke={SENTIMENT_COLOR[s.key]}
                      strokeWidth="16"
                      strokeDasharray={`${s.frac * C} ${C}`}
                      strokeDashoffset={-s.offset * C}
                      transform="rotate(-90 66 66)"
                    />
                  )
              )}
              <text x="66" y="62" textAnchor="middle" fill="#e6ebf5" fontSize="22" fontWeight="800">
                {result.totals.analyzed.toLocaleString()}
              </text>
              <text x="66" y="80" textAnchor="middle" fill="#8d9ab5" fontSize="10.5">
                comments analyzed
              </text>
            </svg>
            <div className="legend">
              {(Object.keys(SENTIMENT_COLOR) as Sentiment[]).map((k) => (
                <div className="row" key={k}>
                  <span className="swatch" style={{ background: SENTIMENT_COLOR[k] }} />
                  {k} <span className="pct">{v.shares[k] ?? 0}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className="lang-chips">
            {result.languages.slice(0, 6).map((l) => (
              <span className="lang-chip" key={l.lang}>
                {l.label} <b>{l.share}%</b>
              </span>
            ))}
            <span className="lang-chip">
              ⏱ {result.totals.duration_seconds}s · {result.totals.sources} sources
            </span>
          </div>
        </div>

        <div className="confidence-block">
          <div className="confidence-num">
            {Math.round(v.confidence.score * 100)}
            <small> / 100 confidence · {v.confidence.tier}</small>
          </div>
          <div className="conf-bar">
            <div className="conf-fill" style={{ width: `${v.confidence.score * 100}%` }} />
          </div>
          <div className="factor-row">
            <span>Sample size</span>
            <b>{Math.round(v.confidence.factors.sample_size * 100)}%</b>
          </div>
          <div className="factor-row">
            <span>Verdict clarity</span>
            <b>{Math.round(v.confidence.factors.verdict_clarity * 100)}%</b>
          </div>
          <div className="factor-row">
            <span>Platform diversity</span>
            <b>{Math.round(v.confidence.factors.platform_diversity * 100)}%</b>
          </div>
          <div className="factor-row">
            <span>Language coverage</span>
            <b>{Math.round(v.confidence.factors.language_coverage * 100)}%</b>
          </div>
          <div className="actions-row" style={{ marginTop: 12 }}>
            <button className="btn-ghost" onClick={() => exportJson(result)}>
              ⬇ Export JSON
            </button>
          </div>
        </div>
      </div>

      {result.warnings.length > 0 && (
        <ul className="warn-list">
          {result.warnings.map((w, i) => (
            <li key={i}>⚠ {w}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function exportJson(result: AnalysisResult) {
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `raye-${result.query.replace(/\W+/g, "-").toLowerCase()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
