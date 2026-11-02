import { useCallback, useEffect, useRef, useState } from "react";
import { getHistory, getJob, getPlatforms, startAnalysis } from "./api";
import AspectBreakdown from "./components/AspectBreakdown";
import CommentsTable from "./components/CommentsTable";
import EvidenceQuotes from "./components/EvidenceQuotes";
import HistoryList from "./components/HistoryList";
import ProgressPanel from "./components/ProgressPanel";
import SearchForm, { SearchOptions } from "./components/SearchForm";
import SourceList from "./components/SourceList";
import VerdictCard from "./components/VerdictCard";
import type { AnalysisResult, JobStatus, PlatformMeta } from "./types";

type View = "idle" | "running" | "done";

export default function App() {
  const [platforms, setPlatforms] = useState<PlatformMeta[]>([]);
  const [view, setView] = useState<View>("idle");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<{ id: string; query: string; created_at: string }[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastOptionsRef = useRef<SearchOptions | null>(null);

  const refreshHistory = useCallback(() => {
    getHistory()
      .then((items) => setHistory(items.map((h) => ({ id: h.id, query: h.query, created_at: h.created_at }))))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    getPlatforms().then(setPlatforms).catch((e) => setError(`Could not reach the Raye API: ${e.message}`));
    refreshHistory();
  }, [refreshHistory]);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const beginPolling = useCallback((jobId: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const status = await getJob(jobId);
        setJob(status);
        if (status.status === "done") {
          stopPolling();
          setResult(status.result);
          setView("done");
          refreshHistory();
        } else if (status.status === "failed") {
          stopPolling();
          setError(status.error || "The analysis job failed.");
          setView("idle");
        }
      } catch {
        /* transient network error — keep polling */
      }
    }, 2000);
  }, [refreshHistory]);

  useEffect(() => stopPolling, []);

  const onSearch = async (opts: SearchOptions) => {
    setError(null);
    setResult(null);
    setJob(null);
    lastOptionsRef.current = opts;
    try {
      const { job_id } = await startAnalysis({
        query: opts.query,
        platforms: opts.platforms,
        max_comments: opts.maxComments,
        sources_per_platform: opts.sourcesPerPlatform,
        comments_per_source: opts.commentsPerSource,
        sort: opts.sort,
      });
      setView("running");
      beginPolling(job_id);
    } catch (e: any) {
      setError(e.message || "Failed to start the analysis.");
    }
  };

  const openHistoryJob = (jobId: string) => {
    setError(null);
    getJob(jobId)
      .then((status) => {
        setJob(status);
        if (status.status === "done" && status.result) {
          setResult(status.result);
          setView("done");
        } else {
          setView("running");
          beginPolling(jobId);
        }
      })
      .catch((e) => setError(e.message));
  };

  return (
    <div className="container">
      <header className="header">
        <div className="brand">
          <div className="brand-logo">R</div>
          <div>
            <h1>Raye</h1>
            <div className="tagline">Evidence-based product review sentiment analysis — real comments, traceable verdicts.</div>
          </div>
        </div>
        <a
          className="github-link"
          href="https://github.com/HassaanAwais777/Raye"
          target="_blank"
          rel="noreferrer"
        >
          ★ GitHub · HassaanAwais777/Raye
        </a>
      </header>

      {error && <div className="error-banner">⚠ {error}</div>}

      <SearchForm
        platforms={platforms}
        busy={view === "running"}
        onSearch={onSearch}
      />

      {view === "idle" && history.length > 0 && (
        <HistoryList items={history} onOpen={openHistoryJob} />
      )}

      {view === "running" && job && <ProgressPanel job={job} />}

      {view === "done" && result && (
        <>
          <VerdictCard result={result} />
          <EvidenceQuotes evidence={result.evidence} />
          {result.aspects.length > 0 && <AspectCard result={result} />}
          <CommentsTable jobId={result ? (job?.job_id ?? "") : ""} aspects={result.aspects} languages={result.languages} />
          {result.sources.length > 0 && <SourceList sources={result.sources} />}
        </>
      )}

      <footer className="footer">
        Raye · English · اردو · Roman Urdu · code-mixed — every claim links back to its source comment.
        <br />
        Author: Muhammad Hassaan Mustaqeem Awais ·{" "}
        <a href="https://github.com/HassaanAwais777/Raye" target="_blank" rel="noreferrer">
          github.com/HassaanAwais777/Raye
        </a>
      </footer>
    </div>
  );
}

function AspectCard({ result }: { result: AnalysisResult }) {
  return (
    <section className="card">
      <h2>
        Aspect breakdown
        <span className="hint">what exactly do reviewers praise or criticise?</span>
      </h2>
      <AspectBreakdown aspects={result.aspects} />
    </section>
  );
}
