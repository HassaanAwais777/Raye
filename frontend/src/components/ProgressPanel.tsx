import type { JobStatus } from "../types";

const PHASES = ["fetching", "analyzing", "aggregating", "done"];

export default function ProgressPanel({ job }: { job: JobStatus }) {
  const phaseIdx = Math.max(0, PHASES.indexOf(job.progress.phase || "fetching"));
  const entries = Object.entries(job.progress.per_platform || {});

  return (
    <section className="card">
      <h2>
        Live progress
        <span className="hint">real-time crawl of “{job.query}”</span>
      </h2>
      <div className="phase-steps">
        {PHASES.slice(0, 3).map((p, i) => (
          <span key={p} className={`phase ${i < phaseIdx ? "done" : i === phaseIdx ? "active" : ""}`}>
            {i < phaseIdx ? "✓ " : i === phaseIdx ? "● " : ""}
            {p}
          </span>
        ))}
      </div>

      <div className="stat-grid">
        <div className="stat">
          <div className="num">{job.progress.fetched.toLocaleString()}</div>
          <div className="lbl">comments fetched</div>
        </div>
        <div className="stat">
          <div className="num">{job.progress.analyzed.toLocaleString()}</div>
          <div className="lbl">analyzed (sentiment + aspects)</div>
        </div>
        <div className="stat">
          <div className="num">{job.progress.duplicates.toLocaleString()}</div>
          <div className="lbl">duplicates removed</div>
        </div>
        <div className="stat">
          <div className="num">{job.platforms.length}</div>
          <div className="lbl">platforms crawling</div>
        </div>
      </div>

      {entries.map(([id, s]) => (
        <div className="platform-row" key={id}>
          <span>
            <b>{id}</b> — {s.fetched.toLocaleString()} comments
          </span>
          <span className={`plat-status ${s.ok ? "ok" : s.error ? "err" : ""}`}>
            {s.ok ? "✓ done" : s.error ? `✗ ${s.error.slice(0, 80)}` : <span className="spinner" />}
          </span>
        </div>
      ))}

      <p className="empty" style={{ marginTop: 12 }}>
        Crawling is deliberately rate-limited to stay polite with the platforms. Large runs can take a
        while — this panel updates every 2 seconds.
      </p>
    </section>
  );
}
