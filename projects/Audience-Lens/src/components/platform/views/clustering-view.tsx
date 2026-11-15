"use client";

import * as React from "react";
import { usePlatform } from "@/lib/platform-store";
import { api, BackendError, type ClusterResult } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import {
  ViewHeader,
  ProvenanceBadge,
  EmptyState,
  SectionTitle,
} from "../primitives";
import { useToast } from "@/hooks/use-toast";
import { GitFork, Loader2, Play, Sparkles, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const SAMPLE = `This phone camera is amazing, best purchase ever
Battery life is terrible, worst phone I have used
Price is too high, not worth it
Great value for money, highly recommend
Screen broke in a week, useless product
Love the design, beautiful phone
Slow performance, laggy interface
Good battery but camera is bad
Amazing quality, worth every penny
Waste of money, scam and fake product
Best budget phone, highly satisfied
Disappointed with the delivery service`;

const SEG_COLORS = [
  "oklch(0.60 0.14 162)",
  "oklch(0.62 0.21 16)",
  "oklch(0.75 0.15 75)",
  "oklch(0.68 0.15 300)",
  "oklch(0.70 0.16 50)",
  "oklch(0.55 0.13 195)",
];

export function ClusteringView() {
  const [text, setText] = React.useState("");
  const [method, setMethod] = React.useState("kmeans");
  const [k, setK] = React.useState("");
  const [result, setResult] = React.useState<ClusterResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const { toast } = useToast();

  const run = async () => {
    const texts = text.split("\n").map((t) => t.trim()).filter(Boolean);
    if (texts.length < 3) {
      toast({ title: "Paste at least 3 comments for clustering", variant: "destructive" });
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await api.cluster(texts, method, k ? Number(k) : undefined);
      setResult(res);
      if (res.error) {
        toast({ title: "Clustering note", description: res.error });
      }
    } catch (e) {
      const msg = e instanceof BackendError ? e.message : "Network error reaching the backend.";
      toast({ title: "Clustering failed", description: msg, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Audience Clustering"
        description="Real sklearn clustering (K-Means / DBSCAN / Hierarchical) on the Python backend, using TF-IDF + sentiment + intent features. Segments are analytical clusters — not verified demographics."
        icon={GitFork}
      />

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        {/* Input */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Comments</CardTitle>
              <ProvenanceBadge provenance="USER_INPUT" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={SAMPLE}
              rows={10}
              className="scroll-thin"
            />
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Method</Label>
                <Select value={method} onValueChange={setMethod}>
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="kmeans">K-Means</SelectItem>
                    <SelectItem value="dbscan">DBSCAN</SelectItem>
                    <SelectItem value="hierarchical">Hierarchical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">k (optional)</Label>
                <Input
                  type="number"
                  value={k}
                  onChange={(e) => setK(e.target.value)}
                  placeholder="auto"
                />
              </div>
            </div>
            <Button onClick={run} disabled={loading} className="w-full gap-2">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Cluster comments
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setText(SAMPLE)} className="w-full gap-1">
              <Sparkles className="h-3.5 w-3.5" /> Load sample
            </Button>
            <p className="text-[11px] text-muted-foreground">
              Calls <code className="rounded bg-muted px-1">POST /api/v1/audience/cluster</code> (Project 3 engine).
            </p>
          </CardContent>
        </Card>

        {/* Results */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Audience segments</CardTitle>
              {result && <ProvenanceBadge provenance="INFERENCE" />}
            </div>
          </CardHeader>
          <CardContent>
            {!result && !loading && (
              <EmptyState
                icon={Users}
                title="No clusters yet"
                description="Paste at least 3 comments and run clustering. Segment cards with sizes, sentiment, and top terms appear here."
                provenance="INSUFFICIENT_DATA"
              />
            )}
            {loading && (
              <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Clustering on the backend…
              </div>
            )}
            {result && !result.error && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline">{result.method}</Badge>
                  <span>{result.n_comments} comments</span>
                  <span>· {result.n_clusters} clusters</span>
                  {result.silhouette !== null && <span>· silhouette {result.silhouette}</span>}
                  {result.noise_points > 0 && <span>· {result.noise_points} noise</span>}
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {result.clusters.map((c, i) => {
                    const color = SEG_COLORS[i % SEG_COLORS.length];
                    return (
                      <div
                        key={c.cluster_id}
                        className="rounded-lg border p-3"
                        style={{ borderColor: color + "44" }}
                      >
                        <div className="flex items-center justify-between">
                          <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{ background: color }}
                            />
                            {c.label}
                          </p>
                          <span className="text-xs tabular-nums text-muted-foreground">
                            {c.size} · {c.share}%
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {c.top_terms.map((t) => (
                            <Badge key={t} variant="secondary" className="text-[10px] font-normal">
                              {t}
                            </Badge>
                          ))}
                        </div>
                        <p className="mt-2 text-[11px] text-muted-foreground">
                          avg sentiment score: <span className="tabular-nums">{c.avg_sentiment_score}</span>
                        </p>
                        <ScrollArea className="mt-1 max-h-24 scroll-thin">
                          <div className="space-y-1 pr-2">
                            {c.sample_comments.map((s, j) => (
                              <p key={j} className="text-[11px] italic text-muted-foreground">
                                “{s}”
                              </p>
                            ))}
                          </div>
                        </ScrollArea>
                      </div>
                    );
                  })}
                </div>
                <p className="text-[11px] italic text-muted-foreground">
                  {result.disclaimer}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
