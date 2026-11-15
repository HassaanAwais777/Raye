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
import { api, BackendError, type AnomalyResult } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ViewHeader, ProvenanceBadge, EmptyState } from "../primitives";
import { useToast } from "@/hooks/use-toast";
import { Activity, Loader2, Play, Sparkles, Trash2 } from "lucide-react";

const SAMPLE = `12,14,11,13,15,12,14,48,13,12,14,11,15,62,13,12,14,13,12,15`;

export function AnomalyView() {
  const [raw, setRaw] = React.useState("");
  const [result, setResult] = React.useState<AnomalyResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const { toast } = useToast();

  const run = async () => {
    const nums = raw.split(/[,\s\n]+/).map((x) => Number(x.trim())).filter((x) => Number.isFinite(x));
    if (nums.length < 4) {
      toast({ title: "Enter at least 4 numeric values", variant: "destructive" });
      return;
    }
    const series = nums.map((v, i) => ({ label: `t${i + 1}`, features: [v] }));
    setLoading(true);
    setResult(null);
    try {
      const res = await api.detectAnomalies(series);
      setResult(res);
    } catch (e) {
      const msg = e instanceof BackendError ? e.message : "Network error reaching the backend.";
      toast({ title: "Anomaly detection failed", description: msg, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const chartData = result
    ? result.anomalies.map((a) => ({
        name: a.label,
        value: a.features[0] ?? 0,
        anomaly: a.anomaly,
        score: a.anomaly_score,
      }))
    : [];

  const anomaliesOnly = result?.anomalies.filter((a) => a.anomaly) ?? [];

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Anomaly Detection"
        description="Real Isolation Forest on the Python backend. Paste a numeric series (e.g. daily comment volume, view counts, or engagement deltas) to surface unusual points — each with a score and supporting evidence."
        icon={Activity}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Series input</CardTitle>
              <ProvenanceBadge provenance="USER_INPUT" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Numeric series (comma / space / newline separated)</Label>
              <Textarea
                value={raw}
                onChange={(e) => setRaw(e.target.value)}
                placeholder={SAMPLE}
                rows={5}
                className="scroll-thin"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={run} disabled={loading} className="gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Detect anomalies
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setRaw(SAMPLE)} className="gap-1">
                <Sparkles className="h-3.5 w-3.5" /> Load sample
              </Button>
              {raw && (
                <Button variant="ghost" size="sm" onClick={() => { setRaw(""); setResult(null); }} className="gap-1">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground">
              Calls <code className="rounded bg-muted px-1">POST /api/v1/audience/anomaly</code> (Isolation Forest, contamination=0.2).
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Anomaly chart</CardTitle>
              {result && <ProvenanceBadge provenance="INFERENCE" />}
            </div>
          </CardHeader>
          <CardContent>
            {!result && !loading && (
              <EmptyState
                icon={Activity}
                title="No series analyzed"
                description="Paste a numeric series and detect. Anomalies are highlighted in rose; normal points in emerald."
                provenance="INSUFFICIENT_DATA"
              />
            )}
            {loading && (
              <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Running Isolation Forest…
              </div>
            )}
            {result && chartData.length > 0 && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline">{result.method}</Badge>
                  <span>· {result.n_items} points</span>
                  <span>· {result.n_anomalies} anomalies</span>
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={1} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                      formatter={(v: number, _n, p) => [
                        `${v} ${p.payload.anomaly ? "(anomaly, score " + p.payload.score + ")" : ""}`,
                        "value",
                      ]}
                    />
                    <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                      {chartData.map((d, i) => (
                        <Cell key={i} fill={d.anomaly ? "oklch(0.62 0.21 16)" : "oklch(0.60 0.14 162)"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {result && anomaliesOnly.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Detected anomalies ({anomaliesOnly.length})</CardTitle>
              <ProvenanceBadge provenance="INFERENCE" />
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="max-h-64 scroll-thin">
              <div className="space-y-2 pr-2">
                {anomaliesOnly.map((a) => (
                  <div key={a.label} className="flex items-center justify-between rounded-md border border-rose-500/30 bg-rose-500/5 p-2.5">
                    <div>
                      <p className="text-sm font-medium text-foreground">{a.label}</p>
                      <p className="text-[11px] text-muted-foreground">value {a.features[0]} · score {a.anomaly_score}</p>
                    </div>
                    <Badge className="bg-rose-500/15 text-rose-700 dark:text-rose-400">anomaly</Badge>
                  </div>
                ))}
              </div>
            </ScrollArea>
            {result.note && <p className="mt-2 text-[11px] text-muted-foreground">{result.note}</p>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
