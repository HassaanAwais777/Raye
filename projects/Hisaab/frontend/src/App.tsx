import { useCallback, useEffect, useState } from "react";
import { api, DatasetRecord, SentimentSummary } from "./api";
import BudgetDecision from "./components/BudgetDecision";
import OverviewSection from "./components/OverviewSection";
import SentimentSection from "./components/SentimentSection";
import BenchmarkSection from "./components/BenchmarkSection";

export default function App() {
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [sentiment, setSentiment] = useState<SentimentSummary | null>(null);
  const [error, setError] = useState<string>("");

  const loadDatasets = useCallback(() => {
    api.datasets()
      .then((ds) => {
        setDatasets(ds);
        setSelected((cur) => {
          if (cur && ds.some((d) => d.id === cur)) return cur;
          const usable = ds.filter((d) => d.rows >= 10_000);
          if (usable.length) return usable.sort((a, b) => b.rows - a.rows)[0].id;
          return ds.length ? ds[ds.length - 1].id : "";
        });
      })
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  useEffect(() => {
    loadDatasets();
    api.sentiment().then(setSentiment).catch(() => setSentiment(null));
  }, [loadDatasets]);

  return (
    <div className="shell">
      <header className="hero">
        <div className="hero-inner">
          <svg className="logo" viewBox="0 0 48 48" aria-hidden>
            <rect x="4" y="4" width="40" height="40" rx="9" fill="#4f46e5" />
            <path d="M15 30c3.2 2.6 6.4 3.9 9.6 3.9 4.2 0 6.9-2 6.9-5 0-2.7-1.9-4.2-6.2-5.3l-2.9-.8c-5-1.3-7.6-3.8-7.6-7.6 0-4.8 4-8 9.8-8 3.2 0 6.2.9 8.9 2.7l-2.1 3.7c-2.2-1.5-4.5-2.3-6.9-2.3-3.7 0-6.1 1.7-6.1 4.3 0 2.2 1.7 3.5 5.6 4.5l2.9.8c5.4 1.4 8.2 4 8.2 8.3 0 5.4-4.4 8.9-11.1 8.9-4.1 0-7.9-1.3-11.4-3.9z" fill="#fff" transform="scale(0.82) translate(5,5)" />
          </svg>
          <div>
            <h1>
              Hisaab <span className="urdu">حساب</span>
            </h1>
            <p>
              <b>Project 2 of 2 — the decision.</b> Project 1 (<a href="https://github.com/HassaanAwais777/Raye" target="_blank" rel="noreferrer">Raye</a>)
              listened: {sentiment ? sentiment.comments_total.toLocaleString() : "210,511"} live-scraped
              product comments (EN / اردو / Roman-Urdu) scored for sentiment. Hisaab decides:
              given your ad-spend history and that voice-of-customer, exactly where the
              next rupee of budget should go.
            </p>
          </div>
          <a className="gh" href="https://github.com/HassaanAwais777/Hisaab" target="_blank" rel="noreferrer">
            github.com/HassaanAwais777/Hisaab
          </a>
        </div>
      </header>

      {error && <div className="banner-error">API unreachable: {error} — start everything with <code>uvicorn app.main:app --port 8000</code> and open http://localhost:8000</div>}

      <main>
        {/* 1. THE DECISION — the whole point of the product */}
        <BudgetDecision
          datasets={datasets}
          selected={selected}
          onSelect={setSelected}
          onDatasetsChanged={loadDatasets}
          commentsTotal={sentiment?.comments_total ?? null}
        />

        {/* 2. THE INPUT SIGNAL — what Raye heard (feeds the decision above) */}
        {sentiment && <SentimentSection summary={sentiment} />}

        {/* 3. EVIDENCE — the analysis, demoted to a collapsible section */}
        <details className="evidence">
          <summary>
            Evidence &amp; benchmarks — platform analysis, engine scaling, cloud costs
            <span className="hint-inline"> (the engineering layer behind the decision)</span>
          </summary>
          <div className="evidence-body">
            {selected && <OverviewSection datasetId={selected} />}
            <BenchmarkSection />
          </div>
        </details>
      </main>

      <footer>
        Hisaab · built by MUHAMMAD HASSAAN MUSTAQEEM AWAIS · S2023376018 ·
        companion project: <a href="https://github.com/HassaanAwais777/Raye" target="_blank" rel="noreferrer">Raye</a>
      </footer>
    </div>
  );
}
