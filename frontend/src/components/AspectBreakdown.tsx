import type { AspectScorecard } from "../types";

export default function AspectBreakdown({ aspects }: { aspects: AspectScorecard[] }) {
  return (
    <div>
      {aspects.map((a) => {
        const total = Math.max(1, a.positive + a.negative + a.mixed + a.neutral);
        return (
          <div className="aspect-row" key={a.name}>
            <div className="aspect-top">
              <span className="aspect-name">{a.label}</span>
              <span className="aspect-meta">
                {a.mentions} mentions · avg score {a.avg_score.toFixed(2)}
                {a.status === "insufficient_mentions" && (
                  <span className="mini-badge" style={{ marginLeft: 8 }}>
                    not enough mentions for a reliable score
                  </span>
                )}
              </span>
            </div>
            <div className="stacked">
              <div style={{ width: `${(a.positive / total) * 100}%`, background: "#34d399" }} />
              <div style={{ width: `${(a.negative / total) * 100}%`, background: "#f87171" }} />
              <div style={{ width: `${(a.mixed / total) * 100}%`, background: "#fbbf24" }} />
              <div style={{ width: `${(a.neutral / total) * 100}%`, background: "#94a3b8" }} />
            </div>
            {a.sample_quote && (
              <div className="aspect-quote">
                “{a.sample_quote.text.slice(0, 160)}
                {a.sample_quote.text.length > 160 ? "…" : ""}” —{" "}
                <a href={a.sample_quote.comment_url ?? "#"} target="_blank" rel="noreferrer">
                  source ↗
                </a>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
