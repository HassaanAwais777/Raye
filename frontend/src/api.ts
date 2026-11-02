import type { AnalyzedComment, CommentsPage, HistoryItem, JobStatus, PlatformMeta } from "./types";

const BASE = "/api";

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export async function getPlatforms(): Promise<PlatformMeta[]> {
  const data = await handle<{ platforms: PlatformMeta[] }>(
    await fetch(`${BASE}/platforms`)
  );
  return data.platforms;
}

export async function startAnalysis(payload: {
  query: string;
  platforms: string[];
  max_comments: number;
  sources_per_platform: number;
  comments_per_source: number;
  sort: string;
}): Promise<{ job_id: string }> {
  return handle(
    await fetch(`${BASE}/analyses`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
}

export async function getJob(jobId: string): Promise<JobStatus> {
  return handle(await fetch(`${BASE}/analyses/${jobId}`));
}

export async function getComments(
  jobId: string,
  filters: { sentiment?: string; lang?: string; aspect?: string; page: number; pageSize: number }
): Promise<CommentsPage> {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize),
  });
  if (filters.sentiment) params.set("sentiment", filters.sentiment);
  if (filters.lang) params.set("lang", filters.lang);
  if (filters.aspect) params.set("aspect", filters.aspect);
  return handle(await fetch(`${BASE}/analyses/${jobId}/comments?${params.toString()}`));
}

export async function getHistory(): Promise<HistoryItem[]> {
  const data = await handle<{ items: HistoryItem[] }>(await fetch(`${BASE}/analyses?limit=10`));
  return data.items;
}

/** Fetch up to `cap` comments across pages (for CSV export). */
export async function getAllComments(jobId: string, cap = 5000): Promise<AnalyzedComment[]> {
  const out: AnalyzedComment[] = [];
  let page = 1;
  while (out.length < cap) {
    const data = await getComments(jobId, { page, pageSize: 100 });
    out.push(...data.items);
    if (page * 100 >= data.total || data.items.length === 0) break;
    page += 1;
  }
  return out.slice(0, cap);
}
