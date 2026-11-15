"use client";

import * as React from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, BackendError, type YouTubeStatus, type YouTubeResearchResult } from "@/lib/api";
import { usePlatform } from "@/lib/platform-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import {
  ViewHeader,
  QuotaBar,
  ConnectionPill,
  ProvenanceBadge,
  EmptyState,
  SectionTitle,
} from "../primitives";
import { useToast } from "@/hooks/use-toast";
import {
  Youtube,
  Search,
  Radio,
  AlertCircle,
  Clock,
  KeyRound,
  Loader2,
  ExternalLink,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import type { Provenance } from "@/lib/types";

const SENT_COLORS: Record<string, string> = {
  positive: "oklch(0.60 0.14 162)",
  negative: "oklch(0.62 0.21 16)",
  neutral: "oklch(0.55 0.01 160)",
  mixed: "oklch(0.75 0.15 75)",
  uncertain: "oklch(0.68 0.15 300)",
};

export function LiveYouTubeView() {
  const setConnection = usePlatform((s) => s.setConnection);
  const { toast } = useToast();

  const [status, setStatus] = React.useState<YouTubeStatus | null>(null);
  const [keyInput, setKeyInput] = React.useState("");
  const [connecting, setConnecting] = React.useState(false);

  const [form, setForm] = React.useState({
    query: "",
    country: "",
    maxVideos: "5",
    commentsPerVideo: "40",
    catalog: "general",
  });
  const [result, setResult] = React.useState<YouTubeResearchResult | null>(null);
  const [running, setRunning] = React.useState(false);

  const refreshStatus = React.useCallback(async () => {
    try {
      const s = await api.youtubeStatus();
      setStatus(s);
      setConnection("youtube", {
        status: s.connected ? "connected" : "disconnected",
        detail: s.detail,
        quotaUsed: s.quota.used,
        quotaTotal: s.quota.total,
      });
    } catch {
      setStatus(null);
    }
  }, [setConnection]);

  React.useEffect(() => { refreshStatus(); }, [refreshStatus]);

  const connect = async () => {
    if (!keyInput.trim()) {
      toast({ title: "Paste a YouTube Data API v3 key", variant: "destructive" });
      return;
    }
    setConnecting(true);
    try {
      const s = await api.youtubeConfigure(keyInput.trim());
      setStatus(s);
      setConnection("youtube", {
        status: s.connected ? "connected" : "disconnected",
        detail: s.detail,
        quotaUsed: s.quota.used,
        quotaTotal: s.quota.total,
      });
      setKeyInput("");
      toast({ title: s.connected ? "YouTube connected" : "Key not accepted", description: s.detail });
    } catch (e) {
      toast({ title: "Connection failed", description: e instanceof BackendError ? e.message : "error", variant: "destructive" });
    } finally {
      setConnecting(false);
    }
  };

  const runResearch = async () => {
    if (!form.query.trim()) {
      toast({ title: "Enter a search query", variant: "destructive" });
      return;
    }
    setRunning(true);
    setResult(null);
    try {
      const res = await api.youtubeResearch(
        form.query.trim(),
        form.country.trim(),
        Number(form.maxVideos) || 5,
        Number(form.commentsPerVideo) || 40,
        form.catalog,
      );
      setResult(res);
      toast({ title: `Collected ${res.n_comments} comments from ${res.n_videos} videos` });
      refreshStatus();
    } catch (e) {
      const msg = e instanceof BackendError ? e.message : "Network error reaching the backend.";
      toast({ title: "Collection failed", description: msg, variant: "destructive" });
    } finally {
      setRunning(false);
    }
  };

  const connected = status?.connected ?? false;
  const distData = result
    ? Object.entries(result.sentiment.distribution).map(([k, v]) => ({
        name: k, count: v, pct: result.sentiment.distribution_pct[k],
      }))
    : [];

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Live YouTube Research"
        description="Collect videos and public comments via the official YouTube Data API v3, then run the multilingual NLP pipeline on them in one integrated call. No scraping. Collection is periodic, not real-time."
        icon={Youtube}
        actions={
          <Button variant="outline" size="sm" className="gap-1" onClick={refreshStatus}>
            <RefreshCw className="h-4 w-4" /> Refresh status
          </Button>
        }
      />

      {/* Status strip */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">YouTube Data API</p>
              <ConnectionPill status={connected ? "connected" : "disconnected"} />
            </div>
            <p className="mt-1.5 text-[11px] text-muted-foreground">{status?.detail ?? "Checking…"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Daily quota</p>
            <QuotaBar used={status?.quota.used ?? 0} total={status?.quota.total ?? 10000} />
          </CardContent>
        </Card>
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="flex items-start gap-2 p-4 text-[11px] text-amber-800 dark:text-amber-300">
            <Clock className="mt-0.5 h-4 w-4 shrink-0" />
            <span>Organic YouTube metrics only — <strong>not</strong> ad impressions, cost, or ROAS. Never blend with paid Google Ads data.</span>
          </CardContent>
        </Card>
      </div>

      {/* Connect panel (shown when not connected) */}
      {!connected && (
        <Card className="border-primary/30">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <KeyRound className="h-4 w-4 text-primary" /> Connect your YouTube Data API v3 key
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              The key is held in the backend process memory for this session only — never persisted or logged.
              Use the <code className="rounded bg-muted px-1">YOUTUBE_API_KEY</code> env var for production.
            </p>
            <div className="flex items-end gap-2">
              <div className="flex-1 space-y-1.5">
                <Label className="text-xs">API key</Label>
                <Input
                  type="password"
                  placeholder="AIza…"
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                />
              </div>
              <Button onClick={connect} disabled={connecting} className="gap-2">
                {connecting ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                Connect
              </Button>
            </div>
            <a
              href="https://developers.google.com/youtube/v3/getting-started"
              target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-[11px] text-primary hover:underline"
            >
              Get a key from Google Cloud Console <ExternalLink className="h-3 w-3" />
            </a>
          </CardContent>
        </Card>
      )}

      {/* Research form (shown when connected) */}
      {connected && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Integrated collection → analysis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs">Search query (keyword / brand / topic)</Label>
              <Textarea
                value={form.query}
                onChange={(e) => setForm({ ...form, query: e.target.value })}
                placeholder="e.g. wireless earbuds review"
                rows={2}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Country</Label>
                <Input value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} placeholder="PK" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Max videos</Label>
                <Input type="number" value={form.maxVideos} onChange={(e) => setForm({ ...form, maxVideos: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Comments / video</Label>
                <Input type="number" value={form.commentsPerVideo} onChange={(e) => setForm({ ...form, commentsPerVideo: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Aspect catalog</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={form.catalog}
                  onChange={(e) => setForm({ ...form, catalog: e.target.value })}
                >
                  <option value="general">General</option>
                  <option value="product">Product review</option>
                  <option value="youtube">YouTube content</option>
                  <option value="fashion">Fashion / e-commerce</option>
                </select>
              </div>
            </div>
            <Button onClick={runResearch} disabled={running} className="gap-2">
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radio className="h-4 w-4" />}
              {running ? "Collecting + analyzing…" : "Run research"}
            </Button>
            <p className="text-[11px] text-muted-foreground">
              Calls <code className="rounded bg-muted px-1">POST /api/v1/youtube/research</code> — searches videos, fetches comments, runs the NLP batch in one call.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">{result.n_videos} videos</Badge>
            <Badge variant="outline">{result.n_comments} comments</Badge>
            <span>· quota used {result.quota.used}</span>
            <ProvenanceBadge provenance={result.provenance as Provenance} className="ml-auto" />
          </div>

          {/* Sentiment distribution from collected comments */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Sentiment of collected comments</CardTitle>
                <ProvenanceBadge provenance="MODEL_PREDICTION" />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {result.n_comments > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={distData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v: number, _n, p) => [`${v} (${p.payload.pct}%)`, "count"]} />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {distData.map((d) => (<Cell key={d.name} fill={SENT_COLORS[d.name] || "oklch(0.5 0 0)"} />))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div className="flex flex-wrap gap-1.5">
                    {result.sentiment.topics.slice(0, 8).map((t) => (
                      <Badge key={t.topic} variant="secondary" className="font-normal text-[10px]">{t.topic} · {t.count}</Badge>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No comments collected (comments may be disabled on these videos). Try broadening the query or increasing the video count.</p>
              )}
            </CardContent>
          </Card>

          {/* Video cards */}
          <Card>
            <CardHeader className="pb-3">
              <SectionTitle icon={Youtube}>Collected videos</SectionTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-80 scroll-thin">
                <div className="grid gap-2 pr-2 sm:grid-cols-2">
                  {result.videos.map((v) => (
                    <a
                      key={v.video_id}
                      href={`https://www.youtube.com/watch?v=${v.video_id}`}
                      target="_blank" rel="noopener noreferrer"
                      className="flex gap-2 rounded-md border border-border p-2 hover:border-primary/40"
                    >
                      {v.thumbnail ? (
                        <img src={v.thumbnail} alt="" className="h-12 w-20 shrink-0 rounded object-cover" />
                      ) : (
                        <div className="flex h-12 w-20 shrink-0 items-center justify-center rounded bg-muted"><Youtube className="h-4 w-4 text-muted-foreground" /></div>
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-2 text-xs font-medium text-foreground">{v.title}</p>
                        <p className="mt-0.5 truncate text-[10px] text-muted-foreground">{v.channel_name} · {v.comment_count ?? 0} comments</p>
                      </div>
                    </a>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Sample analyzed comments */}
          {result.n_comments > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">Analyzed comments</CardTitle>
                  <ProvenanceBadge provenance="MODEL_PREDICTION" />
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-72 scroll-thin">
                  <div className="space-y-2 pr-2">
                    {result.sentiment.results.slice(0, 30).map((r, i) => (
                      <div key={i} className="rounded-md border border-border p-2 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-foreground">{r.text}</p>
                          <span className="prov-badge shrink-0 border" style={{ borderColor: SENT_COLORS[r.sentiment] + "55", background: SENT_COLORS[r.sentiment] + "1a", color: SENT_COLORS[r.sentiment] }}>{r.sentiment}</span>
                        </div>
                        <p className="mt-1 text-[10px] text-muted-foreground">score {r.score} · lang {r.language}</p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}

          <p className="text-[11px] italic text-muted-foreground">{result.note}</p>
        </div>
      )}

      {!result && !running && connected && (
        <EmptyState
          icon={Search}
          title="Ready to collect"
          description="Enter a search query and run research. Videos, comments, and the sentiment distribution appear here — all LIVE_DATA."
          provenance="INSUFFICIENT_DATA"
        />
      )}
    </div>
  );
}
