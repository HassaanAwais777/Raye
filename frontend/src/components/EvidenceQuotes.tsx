import type { EvidenceItem } from "../types";

export default function EvidenceQuotes({
  evidence,
}: {
  evidence: { positive: EvidenceItem[]; negative: EvidenceItem[]; mixed: EvidenceItem[] };
}) {
  const cols = [
    { key: "positive", title: "Positive evidence", cls: "pos", items: evidence.positive },
    { key: "negative", title: "Negative evidence", cls: "neg", items: evidence.negative },
    { key: "mixed", title: "Mixed evidence", cls: "mix", items: evidence.mixed },
  ] as const;

  return (
    <section className="card">
      <h2>
        Evidence — real comments behind the verdict
        <span className="hint">every quote links to the exact comment</span>
      </h2>
      <div className="evidence-grid">
        {cols.map((c) => (
          <div className={`evidence-col ${c.cls}`} key={c.key}>
            <h3>{c.title}</h3>
            {c.items.length === 0 && <div className="empty">No {c.key} comments long enough to quote.</div>}
            {c.items.map((it) => (
              <div className="quote-card" key={it.comment_id}>
                <div className="quote-text">“{it.text}”</div>
                <div className="quote-meta">
                  <span className={`pill ${it.sentiment === "neutral" ? "neu" : it.sentiment.slice(0, 3)}`}>
                    {it.sentiment}
                  </span>
                  <span>👍 {it.likes.toLocaleString()}</span>
                  {it.lang && <span>{langLabel(it.lang)}</span>}
                  {it.comment_url ? (
                    <a href={it.comment_url} target="_blank" rel="noreferrer">
                      view source ↗
                    </a>
                  ) : (
                    it.source_url && (
                      <a href={it.source_url} target="_blank" rel="noreferrer">
                        {it.platform} ↗
                      </a>
                    )
                  )}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

function langLabel(lang: string): string {
  return { en: "English", ur: "اردو", "ur-Roman": "Roman Urdu", "code-mixed": "code-mixed" }[lang] ?? lang;
}
