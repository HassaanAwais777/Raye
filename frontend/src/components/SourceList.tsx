import type { SourceRef } from "../types";

export default function SourceList({ sources }: { sources: (SourceRef & { comments: number })[] }) {
  return (
    <section className="card">
      <h2>
        Sources crawled
        <span className="hint">the exact videos / posts / products these comments came from</span>
      </h2>
      {sources.map((s) => (
        <div className="source-row" key={`${s.platform}-${s.source_id}`}>
          <div>
            <div className="source-title">
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.title}
              </a>
            </div>
            <div className="source-sub">
              {s.platform} · {s.channel || "unknown channel"}
            </div>
          </div>
          <span className="pill">{s.comments.toLocaleString()} comments</span>
        </div>
      ))}
    </section>
  );
}
