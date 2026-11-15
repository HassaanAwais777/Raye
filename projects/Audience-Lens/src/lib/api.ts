// Backend API client — calls the Python FastAPI backend via the Caddy gateway.
// The gateway routes ?XTransformPort=N to localhost:N; the backend runs on 8000.
// Relative paths only (per sandbox constraint).

import type { Provenance } from "./types";

const BACKEND_PORT = "8000";

function withPort(path: string): string {
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}XTransformPort=${BACKEND_PORT}`;
}

export class BackendError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(withPort(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const msg =
      (data && (data.detail || data.error)) ||
      `Backend ${res.status}: ${res.statusText}`;
    throw new BackendError(res.status, msg);
  }
  return data as T;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(withPort(path));
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new BackendError(
      res.status,
      (data && (data.detail || data.error)) || `Backend ${res.status}`
    );
  }
  return data as T;
}

// ---- Types (mirror the backend Pydantic models) ----

export interface SentimentResult {
  text: string;
  language: string;
  sentiment: "positive" | "negative" | "neutral" | "mixed" | "uncertain";
  score: number;
  confidence: number;
  n_sentiment_words: number;
  aspects: { name: string; label: string; mentions: number; sentiment: string; score: number; insufficient: boolean }[];
  provenance: string;
}

export interface BatchResult {
  results: SentimentResult[];
  count: number;
  distribution: Record<string, number>;
  distribution_pct: Record<string, number>;
  language_distribution: Record<string, number>;
  avg_score: number;
  topics: { topic: string; count: number }[];
  provenance: string;
  sample_disclaimer: string;
}

export interface ClusterResult {
  method: string;
  n_comments: number;
  n_clusters: number;
  silhouette: number | null;
  clusters: {
    cluster_id: number;
    label: string;
    size: number;
    share: number;
    avg_sentiment_score: number;
    top_terms: string[];
    sample_comments: string[];
    provenance: string;
  }[];
  noise_points: number;
  provenance: string;
  disclaimer: string;
  error?: string;
}

export interface OptimizeResult {
  allocation: { format: string; label: string; amount: number; share: number; marginal_roas: number }[];
  total_allocated: number;
  budget: number;
  objective: string;
  strategy: string;
  scenarios: Record<string, { expected_revenue: number; allocation: Record<string, number> }>;
  provenance: string;
  constraints: { sums_to_budget_exactly: boolean; no_negative_allocations: boolean };
}

export interface Finding {
  id: string;
  type: string;
  title: string;
  description: string;
  provenance: Provenance;
  supporting_metrics: { label: string; value: string }[];
  evidence: { label: string; value: string }[];
  methodology: string;
  confidence: number;
  recommended_action: string;
}

export interface FindingsResult {
  findings: Finding[];
  n_findings: number;
  n_comments: number;
  sentiment_distribution: Record<string, number>;
  provenance: string;
  disclaimer: string;
  error?: string;
}

export interface AnomalyResult {
  method: string;
  n_items: number;
  n_anomalies: number;
  anomalies: { label: string; anomaly: boolean; anomaly_score: number; features: number[] }[];
  provenance: string;
  note?: string;
  error?: string;
}

export interface YouTubeStatus {
  connected: boolean;
  quota: { used: number; total: number; remaining: number };
  provenance: Provenance;
  detail: string;
}

export interface YouTubeVideo {
  video_id: string;
  title: string;
  channel_id: string;
  channel_name: string;
  published_at: string;
  description?: string;
  thumbnail?: string;
  comment_count?: number;
  view_count?: number;
  like_count?: number;
}

export interface YouTubeResearchResult {
  query: string;
  country: string;
  videos: YouTubeVideo[];
  n_videos: number;
  comments: { comment_id: string; text: string; author: string; like_count: number; comment_url: string }[];
  n_comments: number;
  sentiment: BatchResult;
  quota: { used: number; total: number; remaining: number };
  provenance: Provenance;
  note: string;
}

export interface GoogleAdsStatus {
  connected: boolean;
  sdk_installed: boolean;
  developer_token_set: boolean;
  customer_id_set: boolean;
  refresh_token_set: boolean;
  provenance: Provenance;
  detail: string;
}

export interface ReportSection {
  id: string;
  title: string;
  provenance: Provenance;
  body: string;
  metrics?: { label: string; value: string }[];
  evidence?: { label: string; value: string }[];
  confidence?: number;
  recommended_action?: string;
  note?: string;
}

export interface ReportResult {
  meta: { title: string; objective: string; prepared_by: string; country: string; industry: string; generated_at: string };
  n_comments: number;
  n_findings: number;
  sentiment_distribution: Record<string, number>;
  sections: ReportSection[];
  provenance: Provenance;
  disclaimer: string;
  error?: string;
}

export interface HealthResult {
  status: string;
  version: string;
  modules: Record<string, string>;
  integrations: {
    youtube_connected: boolean;
    google_ads_connected: boolean;
    database: { enabled: boolean; connected: boolean; sqlalchemy_installed: boolean };
  };
}

export const api = {
  health: () => getJSON<HealthResult>("/api/v1/health"),
  nlpAnalyze: (text: string, catalog = "general") =>
    postJSON<{ sentiment: string; score: number; confidence: number; language: string }>("/api/v1/nlp/analyze", { text, aspect_catalog: catalog }),
  nlpAnalyzeBatch: (texts: string[], catalog = "general") =>
    postJSON<BatchResult>("/api/v1/nlp/analyze-batch", { texts, aspect_catalog: catalog }),
  cluster: (texts: string[], method = "kmeans", k?: number) =>
    postJSON<ClusterResult>("/api/v1/audience/cluster", { texts, method, k }),
  detectAnomalies: (series: { label: string; features: number[] }[]) =>
    postJSON<AnomalyResult>("/api/v1/audience/anomaly", { series }),
  optimize: (body: { budget: number; formats: string[]; objective: string; strategy: string }) =>
    postJSON<OptimizeResult>("/api/v1/optimizer/optimize", body),
  generateFindings: (texts: string[], aspectCatalog = "general", clusterMethod = "kmeans") =>
    postJSON<FindingsResult>("/api/v1/findings/generate", { texts, aspect_catalog: aspectCatalog, cluster_method: clusterMethod }),
  youtubeStatus: () => getJSON<YouTubeStatus>("/api/v1/youtube/status"),
  youtubeConfigure: (apiKey: string) =>
    postJSON<YouTubeStatus>("/api/v1/youtube/configure", { api_key: apiKey }),
  youtubeResearch: (query: string, country = "", maxVideos = 5, commentsPerVideo = 40, catalog = "general") =>
    postJSON<YouTubeResearchResult>("/api/v1/youtube/research", { query, country, max_videos: maxVideos, comments_per_video: commentsPerVideo, aspect_catalog: catalog }),
  googleAdsStatus: () => getJSON<GoogleAdsStatus>("/api/v1/google-ads/status"),
  reportGenerate: (texts: string[], meta: Record<string, string>, catalog = "general", method = "kmeans") =>
    postJSON<ReportResult>("/api/v1/reports/generate", { texts, meta, aspect_catalog: catalog, cluster_method: method }),
  reportExport: async (texts: string[], meta: Record<string, string>, format: "pdf" | "docx", catalog = "general", method = "kmeans"): Promise<Blob> => {
    const res = await fetch(withPort("/api/v1/reports/export"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texts, meta, format, aspect_catalog: catalog, cluster_method: method }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new BackendError(res.status, data?.detail || `Export failed (${res.status})`);
    }
    return await res.blob();
  },
};
