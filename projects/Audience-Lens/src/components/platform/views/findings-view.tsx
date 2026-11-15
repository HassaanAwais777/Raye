"use client";

import * as React from "react";
import { api, BackendError, type FindingsResult, type Finding } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
} from "../primitives";
import { useToast } from "@/hooks/use-toast";
import {
  Lightbulb,
  Loader2,
  Play,
  Sparkles,
  Trash2,
  ArrowRight,
} from "lucide-react";
import type { Provenance } from "@/lib/types";

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
Disappointed with the delivery service
`;

const TYPE_ICON: Record<string, string> = {
  sentiment: "Sentiment",
  topics: "Topics",
  complaints: "Complaints",
  praise: "Praise",
  segments: "Segments",
  opportunity: "Opportunity",
  limitation: "Limitation",
};

export function FindingsView() {
  const [text, setText] = React.useState("");
  const [catalog, setCatalog] = React.useState("general");
  const [method, setMethod] = React.useState("kmeans");
  const [result, setResult] = React.useState<FindingsResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const { toast } = useToast();

  const run = async () => {
    const texts = text.split("\n").map((t) => t.trim()).filter(Boolean);
    if (texts.length < 3) {
      toast({ title: "Paste at least 3 comments", variant: "destructive" });
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await api.generateFindings(texts, catalog, method);
      setResult(res);
    } catch (e) {
      const msg = e instanceof BackendError ? e.message : "Network error reaching the backend.";
      toast({ title: "Findings generation failed", description: msg, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Findings & Recommendations"
        description="The capstone engine: runs sentiment (Project A) + clustering (Project 3) on the backend and synthesizes evidence-based finding cards. Every finding is traceable to the source sample."
        icon={Lightbulb}
      />

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Comment input</CardTitle>
            <ProvenanceBadge provenance="USER_INPUT" />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 lg:grid-cols-[1fr_220px]">
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={SAMPLE}
              rows={6}
              className="scroll-thin"
            />
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Aspect catalog</Label>
                <Select value={catalog} onValueChange={setCatalog}>
                  <SelectTrigger className="h-9">
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
              <div className="space-y-1.5">
                <Label className="text-xs">Cluster method</Label>
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
              <Button onClick={run} disabled={loading} className="w-full gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Generate
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setText(SAMPLE)} className="w-full gap-1">
                <Sparkles className="h-3.5 w-3.5" /> Load sample
              </Button>
              {text && (
                <Button variant="ghost" size="sm" onClick={() => { setText(""); setResult(null); }} className="w-full gap-1">
                  <Trash2 className="h-3.5 w-3.5" /> Clear
                </Button>
              )}
            </div>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Calls <code className="rounded bg-muted px-1">POST /api/v1/findings/generate</code> — runs NLP + clustering, returns evidence-based cards.
          </p>
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">{result.n_findings} findings</Badge>
            <span>· {result.n_comments} comments</span>
            <span>· sentiment: {Object.entries(result.sentiment_distribution).filter(([, v]) => v > 0).map(([k, v]) => `${k} ${v}%`).join(", ")}</span>
            <ProvenanceBadge provenance={result.provenance as Provenance} className="ml-auto" />
          </div>

          {result.findings.map((f) => (
            <FindingCard key={f.id} finding={f} />
          ))}

          <p className="text-[11px] italic text-muted-foreground">{result.disclaimer}</p>
        </div>
      )}

      {!result && !loading && (
        <EmptyState
          icon={Lightbulb}
          title="No findings generated yet"
          description="Paste comments and click Generate. The engine runs sentiment + clustering and returns evidence-based insight cards — verdict, topics, complaints, praise, segments, opportunities, and sample sufficiency."
          provenance="INSUFFICIENT_DATA"
        />
      )}
    </div>
  );
}

function FindingCard({ finding: f }: { finding: Finding }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex items-start gap-2">
            <Badge variant="secondary" className="mt-0.5 font-mono text-[10px]">{f.id}</Badge>
            <div>
              <p className="text-sm font-semibold text-foreground">{f.title}</p>
              <p className="text-[11px] text-muted-foreground">{TYPE_ICON[f.type] || f.type}</p>
            </div>
          </div>
          <ProvenanceBadge provenance={f.provenance} />
        </div>

        <p className="mt-2 text-sm text-foreground">{f.description}</p>

        {f.supporting_metrics.length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {f.supporting_metrics.map((m) => (
              <div key={m.label} className="rounded-md border border-border p-2">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{m.label}</p>
                <p className="text-sm font-semibold tabular-nums text-foreground">{m.value}</p>
              </div>
            ))}
          </div>
        )}

        {f.evidence.length > 0 && (
          <div className="mt-3 space-y-1">
            <SectionTitle>Evidence</SectionTitle>
            <ScrollArea className="max-h-32 scroll-thin">
              <div className="space-y-1 pr-2">
                {f.evidence.map((e, i) => (
                  <p key={i} className="rounded-md bg-muted/50 px-2 py-1 text-[11px] italic text-muted-foreground">
                    <span className="font-medium not-italic text-foreground">{e.label}:</span> “{e.value}”
                  </p>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}

        <div className="mt-3 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Confidence</span>
            <span className="tabular-nums">{Math.round(f.confidence * 100)}%</span>
          </div>
          <Progress value={f.confidence * 100} className="h-1.5" />
        </div>

        {f.methodology && (
          <p className="mt-2 text-[11px] text-muted-foreground">
            <span className="font-medium">Methodology:</span> {f.methodology}
          </p>
        )}

        {f.recommended_action && (
          <div className="mt-3 flex items-start gap-2 rounded-md border border-primary/20 bg-primary/5 p-2.5 text-xs">
            <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
            <div>
              <p className="font-medium text-foreground">Recommended action</p>
              <p className="text-muted-foreground">{f.recommended_action}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
