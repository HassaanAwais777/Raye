import type { HistoryItem } from "../types";

export default function HistoryList({
  items,
  onOpen,
}: {
  items: { id: string; query: string; created_at: string }[];
  onOpen: (id: string) => void;
}) {
  return (
    <section className="card">
      <h2>
        Recent analyses
        <span className="hint">stored locally in SQLite — click to reopen</span>
      </h2>
      {items.map((h) => (
        <div className="history-row" key={h.id}>
          <span className="q" onClick={() => onOpen(h.id)}>
            {h.query}
          </span>
          <span className="m">{new Date(h.created_at).toLocaleString()}</span>
        </div>
      ))}
    </section>
  );
}
