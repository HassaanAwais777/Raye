import { SentimentSummary } from "../api";

export default function SentimentSection({ summary }: { summary: SentimentSummary }) {
  return (
    <section className="card signal">
      <h2>
        The input signal — what Raye heard{" "}
        <span className="muted">— {summary.comments_total.toLocaleString()} live-scraped comments (EN / اردو / Roman-Urdu), scored in project 1</span>
      </h2>
      <p className="signal-intro">
        Raye scraped real customer comments and scored their sentiment. This voice-of-customer
        is <b>an input to the allocation above</b>: platforms whose audience speaks more
        positively get a slightly steeper response curve, so the optimizer leans into them.
        Everything below is measured — nothing is invented for unmeasured platforms.
      </p>

      <div className="kpi-grid">
        <div className="kpi">
          <span className="kpi-label">Global brand health</span>
          <span className={"kpi-value " + (summary.global.net_weighted >= 0 ? "good" : "bad")}>
            {summary.global.net_weighted >= 0 ? "+" : ""}
            {summary.global.net_weighted.toFixed(3)}
          </span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Products flagged at risk</span>
          <span className="kpi-value">{summary.products_risk.length}</span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Positive comments</span>
          <span className="kpi-value good">
            {(summary.languages.by_sentiment.positive ?? 0).toLocaleString()}
          </span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Negative comments</span>
          <span className="kpi-value bad">
            {(summary.languages.by_sentiment.negative ?? 0).toLocaleString()}
          </span>
        </div>
      </div>

      <h3>Platform evidence → budget factors</h3>
      <table className="tbl">
        <thead>
          <tr><th>Ad platform</th><th>Raye evidence</th><th>Comments</th><th>Voice (likes-weighted)</th><th>Shrunk deviation</th><th>Curve factor</th></tr>
        </thead>
        <tbody>
          {summary.platforms.map(p => (
            <tr key={p.platform}>
              <td className="platform">{p.platform}</td>
              <td>{p.evidence === "-" ? <span className="muted">global fallback</span> : p.evidence}</td>
              <td>{p.n_comments.toLocaleString()}</td>
              <td>{p.net_weighted >= 0 ? "+" : ""}{p.net_weighted.toFixed(4)}</td>
              <td>{p.deviation >= 0 ? "+" : ""}{(p.deviation * 100).toFixed(2)}%</td>
              <td><b>{p.factor.toFixed(4)}</b></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="footnote">
        YouTube is measured directly (ads run on the measured surface); Reddit proxies the
        discussion/research voice behind Google at half weight; unmeasured platforms fall back
        to the global brand index — no sentiment is invented.
      </p>

      <div className="two-col">
        <div>
          <h3>Strongest reputation</h3>
          <table className="tbl">
            <thead><tr><th>Product</th><th>n</th><th>Shrunk voice</th><th>Pos%</th></tr></thead>
            <tbody>
              {summary.products_top.map(p => (
                <tr key={p.slug}>
                  <td>{p.name}</td>
                  <td>{p.n_comments.toLocaleString()}</td>
                  <td><span className="good">+{p.net_shrunk.toFixed(3)}</span></td>
                  <td>{(p.positive_share * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h3>Sentiment risk board</h3>
          <table className="tbl">
            <thead><tr><th>Product</th><th>n</th><th>Shrunk voice</th><th>Neg%</th></tr></thead>
            <tbody>
              {summary.products_risk.length === 0
                ? <tr><td colSpan={4} className="muted">no products below the risk line</td></tr>
                : summary.products_risk.map(p => (
                  <tr key={p.slug}>
                    <td>{p.name}</td>
                    <td>{p.n_comments.toLocaleString()}</td>
                    <td><span className="bad">{p.net_shrunk.toFixed(3)}</span></td>
                    <td>{(p.negative_share * 100).toFixed(0)}%</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="footnote">
        Source: {String((summary.provenance as { source_project?: string }).source_project ?? "Raye")} —
        shrinkage pulls small-sample products toward the brand mean (empirical Bayes).
      </p>
    </section>
  );
}
