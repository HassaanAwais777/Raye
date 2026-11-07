/** Typed API client for the Hisaab backend. */

export interface DatasetRecord {
  id: string;
  rows: number;
  locale: string;
  seed: number;
  currency: string;
  generation_seconds: number;
  csv_rows: number;
}

export interface DerivedSums {
  rows: number;
  impressions: number;
  clicks: number;
  spend: number;
  conversions: number;
  revenue: number;
  ctr: number;
  cpc: number;
  cpa: number;
  cvr: number;
  roas: number;
}

export interface Overview {
  dataset: DatasetRecord;
  rows_raw: number;
  rows_clean: number;
  duplicates_removed: number;
  totals: DerivedSums;
  groups: Record<string, DerivedSums>;
  currency: string;
}

export interface AllocRow {
  platform: string;
  allocated: number;
  share_pct: number;
  expected_incremental_revenue: number;
  marginal_roas: number;
  curve_alpha: number;
  curve_beta: number;
  curve_r2: number;
  weekly_points: number;
  alpha_ci?: [number, number] | null;
  beta_ci?: [number, number] | null;
}

export interface PlatformSentiment {
  platform: string;
  evidence: string;
  n_comments: number;
  net_weighted: number;
  deviation: number;
  factor: number;
}

export interface SentimentOverlay {
  enabled: boolean;
  source: string;
  comments_total: number;
  global_brand_health: number;
  platforms: PlatformSentiment[];
  allocation: { platform: string; allocated: number; share_pct: number;
                expected_incremental_revenue: number; factor: number }[];
  expected_incremental_revenue: number;
  revenue_delta_vs_l3: number;
  note: string;
}

export interface Baseline {
  allocation: Record<string, number>;
  expected_incremental_revenue: number;
}

export interface Recommendation {
  dataset: string;
  currency: string;
  budget: number;
  weekly_points: number;
  allocation: AllocRow[];
  expected_incremental_revenue: number;
  blended_incremental_roas: number;
  baselines: Record<string, Baseline>;
  sentiment?: SentimentOverlay;
  warnings: string[];
  method: string;
}

export interface SentimentSummary {
  provenance: Record<string, unknown>;
  comments_total: number;
  global: { net_weighted: number; n: number };
  platforms: PlatformSentiment[];
  products_top: ProductRow[];
  products_risk: ProductRow[];
  languages: { n: number; by_sentiment: Record<string, number> };
}

export interface ProductRow {
  slug: string;
  name: string;
  category: string;
  n_comments: number;
  net_weighted: number;
  net_shrunk: number;
  positive_share: number;
  negative_share: number;
  flag: "risk" | "tailwind" | "neutral";
}

export interface BenchmarkPoint { seconds: number | null; peak_mb: number | null;
                                 error?: string; sums_ok?: boolean }
export interface BenchmarkPayload {
  generated_at: string;
  locale: string;
  scales: number[];
  repeat: number;
  machine: string;
  results: Record<string, Record<string, BenchmarkPoint>>;
  cost_model?: CostRow[];
}
export interface CostRow {
  engine: string;
  config: string;
  estimated_node_hours: number;
  estimated_cost_usd: number;
  data_gb: number;
  note: string;
  measured_local_seconds: number | null;
}

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error((detail as { detail?: string }).detail ?? `${r.status} ${r.statusText}`);
  }
  return r.json() as Promise<T>;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => j<{ status: string; version: string }>("/api/health"),
  datasets: () => j<DatasetRecord[]>("/api/datasets"),
  createDataset: (rows: number, locale = "pk") =>
    j<DatasetRecord>("/api/datasets", post({ rows, locale, seed: 42, with_csv: true })),
  overview: (id: string, by = "platform") =>
    j<Overview>(`/api/datasets/${id}/overview?by=${by}`),
  recommend: (dataset: string, budget: number, withCi: boolean, sentimentAware: boolean) =>
    j<Recommendation>("/api/recommend", post({
      dataset, budget, with_ci: withCi, sentiment_aware: sentimentAware })),
  sentiment: () => j<SentimentSummary>("/api/sentiment/summary"),
  benchmark: () => j<BenchmarkPayload>("/api/benchmark/latest"),
};
