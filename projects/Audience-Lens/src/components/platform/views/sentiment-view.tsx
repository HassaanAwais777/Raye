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
import { usePlatform } from "@/lib/platform-store";
import { api, BackendError, type BatchResult } from "@/lib/api";
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
import {
  ViewHeader,
  ProvenanceBadge,
  EmptyState,
  SectionTitle,
  SampleDisclaimer,
} from "../primitives";
import { useToast } from "@/hooks/use-toast";
import { Smile, Loader2, Play, Trash2, Sparkles } from "lucide-react";
import type { Provenance } from "@/lib/types";

const SENT_COLORS: Record<string, string> = {
  positive: "oklch(0.60 0.14 162)",
  negative: "oklch(0.62 0.21 16)",
  neutral: "oklch(0.55 0.01 160)",
  mixed: "oklch(0.75 0.15 75)",
  uncertain: "oklch(0.68 0.15 300)",
};

const SAMPLE = `This phone camera is amazing, best purchase ever
Battery life is terrible, worst phone I have used
Price is too high, not worth it
Great value for money, highly recommend
Screen broke in a week, useless product
Love the design, beautiful phone
Slow performance, laggy interface
Good battery but camera is bad
Amazing quality, worth every penny
Waste of money, scam and fake product`;

export function SentimentView() {
  const [text, setText] = React.useState("");
  const [catalog, setCatalog] = React.useState("general");
  const [result, setResult] = React.useState<BatchResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const { toast } = useToast();

  const run = async () => {
    const texts = text.split("\n").map((t) => t.trim()).filter(Boolean);
    if (texts.length === 0) {
      toast({ title: "Paste at least one comment", variant: "destructive" });
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await api.nlpAnalyzeBatch(texts, catalog);
      setResult(res);
    } catch (e) {
      const msg = e instanceof BackendError ? e.message : "Network error reaching the backend.";
      toast({ title: "Analysis failed", description: msg, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const distData = result
    ? Object.entries(result.distribution).map(([k, v]) => ({
        name: k,
        count: v,
        pct: result.distribution_pct[k],
      }))
    : [];

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Multilingual Sentiment Intelligence"
        description="Real multilingual NLP (English, Urdu script, Roman Urdu, code-mixed) running on the Python backend. Paste comments to analyze — results are MODEL_PREDICTION, never fabricated."
        icon={Smile}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        {/* Input */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Comment input</CardTitle>
              <ProvenanceBadge provenance="USER_INPUT" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label className="text-xs">
                Paste comments — one per line (EN / Urdu / Roman Urdu / mixed)
              </Label>
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={SAMPLE}
                rows={10}
                className="scroll-thin"
              />
            </div>
            <div className="flex items-center gap-2">
              <Label className="text-xs">Aspect catalog</Label>
              <Select value={catalog} onValueChange={setCatalog}>
                <SelectTrigger className="h-8 w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">General</SelectItem>
                  <SelectItem value="product">Product review</SelectItem>
                  <SelectItem value="youtube">YouTube content</SelectItem>
                  <SelectItem value="fashion">Fashion / e-commerce</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={run} disabled={loading} className="gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Analyze {text.split("\n").filter((t) => t.trim()).length || 0} comments
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setText(SAMPLE)} className="gap-1">
                <Sparkles className="h-3.5 w-3.5" /> Load sample
              </Button>
              {text && (
                <Button variant="ghost" size="sm" onClick={() => { setText(""); setResult(null); }} className="gap-1">
                  <Trash2 className="h-3.5 w-3.5" /> Clear
                </Button>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground">
              Calls <code className="rounded bg-muted px-1">POST /api/v1/nlp/analyze-batch</code> on the Python backend (Raye pipeline).
            </p>
          </CardContent>
        </Card>

        {/* Distribution chart */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Sentiment distribution</CardTitle>
              {result && <ProvenanceBadge provenance="MODEL_PREDICTION" />}
            </div>
          </CardHeader>
          <CardContent>
            {!result && !loading && (
              <EmptyState
                icon={Smile}
                title="No analysis yet"
                description="Paste comments and click Analyze. The distribution across 5 classes appears here."
                provenance="INSUFFICIENT_DATA"
              />
            )}
            {loading && (
              <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Running NLP on the backend…
              </div>
            )}
            {result && (
              <div className="space-y-3">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={distData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                      formatter={(v: number, _n, p) => [`${v} (${p.payload.pct}%)`, "count"]}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {distData.map((d) => (
                        <Cell key={d.name} fill={SENT_COLORS[d.name] || "oklch(0.5 0 0)"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-md border border-border p-2">
                    <p className="text-muted-foreground">Avg. score</p>
                    <p className="font-semibold tabular-nums">{result.avg_score}</p>
                  </div>
                  <div className="rounded-md border border-border p-2">
                    <p className="text-muted-foreground">Languages</p>
                    <p className="font-semibold">
                      {Object.entries(result.language_distribution)
                        .map(([k, v]) => `${k}:${v}`)
                        .join(" ") || "—"}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Topics + classified comments */}
      {result && (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <Card>
            <CardHeader className="pb-3">
              <SectionTitle icon={Sparkles}>Top topics</SectionTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-1.5">
              {result.topics.map((t) => (
                <Badge key={t.topic} variant="secondary" className="font-normal">
                  {t.topic} · {t.count}
                </Badge>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Classified comments ({result.count})</CardTitle>
                <ProvenanceBadge provenance="MODEL_PREDICTION" />
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-80 scroll-thin">
                <div className="space-y-2 pr-3">
                  {result.results.map((r, i) => (
                    <div key={i} className="rounded-md border border-border p-2.5">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs text-foreground">{r.text}</p>
                        <span
                          className="prov-badge shrink-0 border"
                          style={{
                            borderColor: SENT_COLORS[r.sentiment] + "55",
                            background: SENT_COLORS[r.sentiment] + "1a",
                            color: SENT_COLORS[r.sentiment],
                          }}
                        >
                          {r.sentiment}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span>score {r.score}</span>
                        <span>conf {r.confidence}</span>
                        <span>lang {r.language}</span>
                        {r.aspects.length > 0 && (
                          <span>aspects: {r.aspects.map((a) => `${a.name}:${a.sentiment}`).join(", ")}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      )}

      {result && <SampleDisclaimer>{result.sample_disclaimer}</SampleDisclaimer>}
    </div>
  );
}
