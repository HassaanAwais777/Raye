// Types mirroring the Raye backend API contract (app/analysis/verdict.py).

export type Sentiment = "positive" | "negative" | "mixed" | "neutral";

export interface SourceRef {
  platform: string;
  source_id: string;
  title: string;
  url: string;
  channel: string;
  comment_url?: string;
}

export interface CommentAspect {
  name: string;
  label: string;
  sentiment: Sentiment;
  score: number;
}

export interface AnalyzedComment {
  id: string;
  text_raw: string;
  text_normalized: string;
  lang: string;
  sentiment: Sentiment;
  score: number;
  aspects: CommentAspect[];
  likes: number;
  published: string;
  fetched_at: string;
  source: SourceRef;
}

export interface EvidenceItem {
  comment_id: string;
  text: string;
  sentiment: Sentiment;
  score: number;
  likes: number;
  lang: string | null;
  platform: string | null;
  source_title: string | null;
  source_url: string | null;
  comment_url: string | null;
}

export interface AspectScorecard {
  name: string;
  label: string;
  mentions: number;
  positive: number;
  negative: number;
  mixed: number;
  neutral: number;
  dominant: Sentiment;
  avg_score: number;
  status: "ok" | "insufficient_mentions";
  sample_quote: EvidenceItem | null;
}

export interface Verdict {
  status: "sufficient" | "insufficient_evidence";
  label: string;
  headline: string;
  summary: string;
  overall_score: number;
  sentiment_counts: Record<Sentiment, number>;
  shares: Record<Sentiment, number>;
  confidence: {
    score: number;
    tier: "high" | "medium" | "low" | "insufficient";
    min_reliable_n: number;
    factors: {
      sample_size: number;
      verdict_clarity: number;
      platform_diversity: number;
      language_coverage: number;
    };
  };
  recommendations: string[];
}

export interface AnalysisResult {
  query: string;
  generated_at: string;
  verdict: Verdict;
  totals: {
    fetched: number;
    analyzed: number;
    duplicates_removed: number;
    sources: number;
    duration_seconds: number;
  };
  platforms: { id: string; label: string; experimental: boolean; fetched: number; ok: boolean; error: string | null }[];
  languages: { lang: string; label: string; count: number; share: number }[];
  aspects: AspectScorecard[];
  evidence: { positive: EvidenceItem[]; negative: EvidenceItem[]; mixed: EvidenceItem[] };
  sources: (SourceRef & { comments: number })[];
  warnings: string[];
}

export interface JobProgress {
  fetched: number;
  analyzed: number;
  duplicates: number;
  phase: string;
  per_platform: Record<string, { fetched: number; ok: boolean; error: string | null }>;
}

export interface JobStatus {
  job_id: string;
  query: string;
  status: "running" | "done" | "failed";
  phase: string;
  progress: JobProgress;
  result: AnalysisResult | null;
  error: string | null;
  platforms: string[];
}

export interface PlatformMeta {
  id: string;
  label: string;
  experimental: boolean;
  enabled_by_default: boolean;
  rate_limit_rps: number;
}

export interface CommentsPage {
  total: number;
  page: number;
  page_size: number;
  items: AnalyzedComment[];
}

export interface HistoryItem {
  id: string;
  query: string;
  status: string;
  phase: string;
  progress: { analyzed?: number };
  created_at: string;
}
