import { useState } from "react";
import type { PlatformMeta } from "../types";

export interface SearchOptions {
  query: string;
  platforms: string[];
  maxComments: number;
  sourcesPerPlatform: number;
  commentsPerSource: number;
  sort: string;
}

const MAX_OPTIONS = [500, 2000, 10000, 50000, 200000];

export default function SearchForm({
  platforms,
  busy,
  onSearch,
}: {
  platforms: PlatformMeta[];
  busy: boolean;
  onSearch: (opts: SearchOptions) => void;
}) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [maxComments, setMaxComments] = useState(2000);
  const [sourcesPerPlatform, setSourcesPerPlatform] = useState(10);
  const [commentsPerSource, setCommentsPerSource] = useState(200);
  const [sort, setSort] = useState("top");
  const [advanced, setAdvanced] = useState(false);

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q || busy) return;
    const enabledDefaults = platforms.filter((p) => p.enabled_by_default).map((p) => p.id);
    onSearch({
      query: q,
      platforms: selected.length ? selected : enabledDefaults,
      maxComments,
      sourcesPerPlatform,
      commentsPerSource,
      sort,
    });
  };

  return (
    <section className="card">
      <form onSubmit={submit}>
        <div className="search-row">
          <input
            className="search-input"
            placeholder='Type a product — e.g. "Infinix Note 40", "Galaxy S24", "Airpods Pro 2"…'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={busy}
          />
          <button className="btn-primary" type="submit" disabled={busy || !query.trim()}>
            {busy ? "Analyzing…" : "Analyze reviews"}
          </button>
        </div>

        <div className="platform-toggles">
          {platforms.map((p) => (
            <span
              key={p.id}
              className={`chip-toggle ${selected.includes(p.id) || (!selected.length && p.enabled_by_default) ? "on" : ""}`}
              onClick={() => !busy && toggle(p.id)}
            >
              <span className="dot" />
              {p.id}
              {p.experimental && <span className="badge-exp">experimental</span>}
            </span>
          ))}
          <span className="chip-toggle" onClick={() => setAdvanced((a) => !a)}>
            {advanced ? "− fewer options" : "＋ advanced"}
          </span>
        </div>

        {advanced && (
          <div className="advanced">
            <label>
              Max comments
              <select value={maxComments} onChange={(e) => setMaxComments(Number(e.target.value))}>
                {MAX_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n.toLocaleString()}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Sources / platform
              <select
                value={sourcesPerPlatform}
                onChange={(e) => setSourcesPerPlatform(Number(e.target.value))}
              >
                {[3, 5, 10, 20, 40].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Comments / source
              <select
                value={commentsPerSource}
                onChange={(e) => setCommentsPerSource(Number(e.target.value))}
              >
                {[50, 100, 200, 500, 1000].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Comment sort
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                <option value="top">top</option>
                <option value="new">new</option>
              </select>
            </label>
            <span className="note">
              Scale note: 200k comments is the ceiling — full runs take hours because crawling is deliberately rate-limited.
            </span>
          </div>
        )}
      </form>
    </section>
  );
}
