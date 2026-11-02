import { useCallback, useEffect, useState } from "react";
import { getAllComments, getComments } from "../api";
import type { AnalyzedComment, AspectScorecard, CommentsPage } from "../types";

const SENTIMENTS = ["positive", "negative", "mixed", "neutral"];

export default function CommentsTable({
  jobId,
  aspects,
  languages,
}: {
  jobId: string;
  aspects: AspectScorecard[];
  languages: { lang: string; label: string }[];
}) {
  const [data, setData] = useState<CommentsPage | null>(null);
  const [page, setPage] = useState(1);
  const [sentiment, setSentiment] = useState("");
  const [lang, setLang] = useState("");
  const [aspect, setAspect] = useState("");
  const [exporting, setExporting] = useState(false);
  const pageSize = 25;

  const load = useCallback(async () => {
    if (!jobId) return;
    try {
      const res = await getComments(jobId, { sentiment, lang, aspect, page, pageSize });
      setData(res);
    } catch {
      setData(null);
    }
  }, [jobId, sentiment, lang, aspect, page]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  const exportCsv = async () => {
    setExporting(true);
    try {
      const all = await getAllComments(jobId, 5000);
      const rows = [
        ["sentiment", "score", "lang", "aspects", "likes", "published", "platform", "text", "comment_url"],
        ...all.map((c: AnalyzedComment) => [
          c.sentiment,
          String(c.score),
          c.lang,
          c.aspects.map((a) => a.name).join("|"),
          String(c.likes),
          c.published,
          c.source.platform,
          `"${c.text_raw.replace(/"/g, '""').slice(0, 500)}"`,
          c.source.comment_url ?? "",
        ]),
      ];
      const csv = rows.map((r) => r.join(",")).join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `raye-comments-${jobId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <section className="card">
      <h2>
        All analyzed comments
        <span className="hint">{data ? `${data.total.toLocaleString()} matching` : "…"} · traceable to sources</span>
      </h2>

      <div className="filters">
        <select
          value={sentiment}
          onChange={(e) => {
            setSentiment(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All sentiments</option>
          {SENTIMENTS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={lang}
          onChange={(e) => {
            setLang(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All languages</option>
          {languages.map((l) => (
            <option key={l.lang} value={l.lang}>
              {l.label}
            </option>
          ))}
        </select>
        <select
          value={aspect}
          onChange={(e) => {
            setAspect(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All aspects</option>
          {aspects.map((a) => (
            <option key={a.name} value={a.name}>
              {a.label}
            </option>
          ))}
        </select>
        <button className="btn-ghost" onClick={exportCsv} disabled={exporting}>
          {exporting ? "Preparing…" : "⬇ Export CSV (≤5,000)"}
        </button>
      </div>

      <table className="comments">
        <thead>
          <tr>
            <th>Sentiment</th>
            <th>Comment</th>
            <th>Lang</th>
            <th>Aspects</th>
            <th>👍</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {(data?.items ?? []).map((c) => (
            <tr key={c.id}>
              <td className="sent-cell">
                <span
                  className="sent-dot"
                  style={{
                    background: { positive: "#34d399", negative: "#f87171", mixed: "#fbbf24", neutral: "#94a3b8" }[
                      c.sentiment
                    ],
                  }}
                />
                {c.sentiment}
                <div style={{ color: "#8d9ab5", fontSize: 11, marginLeft: 16 }}>{c.score.toFixed(2)}</div>
              </td>
              <td className="c-text" title={c.text_normalized}>
                {c.text_raw.slice(0, 260)}
                {c.text_raw.length > 260 ? "…" : ""}
              </td>
              <td>{c.lang}</td>
              <td>
                <div className="c-aspects">
                  {c.aspects.length === 0 && <span style={{ color: "#8d9ab5" }}>—</span>}
                  {c.aspects.map((a) => (
                    <span className="pill" key={a.name}>
                      {a.name}
                    </span>
                  ))}
                </div>
              </td>
              <td>{c.likes.toLocaleString()}</td>
              <td className="c-src">
                {c.source.comment_url ? (
                  <a href={c.source.comment_url} target="_blank" rel="noreferrer">
                    {c.source.platform} ↗
                  </a>
                ) : (
                  c.source.platform
                )}
              </td>
            </tr>
          ))}
          {data && data.items.length === 0 && (
            <tr>
              <td colSpan={6} className="empty">
                No comments match these filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="pager">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          ← Prev
        </button>
        <span>
          Page {page} / {totalPages}
        </span>
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
          Next →
        </button>
      </div>
    </section>
  );
}
