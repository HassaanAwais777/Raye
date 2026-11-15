"use client";

import * as React from "react";
import { api, BackendError, type ReportResult, type ReportSection } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ViewHeader,
  ProvenanceBadge,
  EmptyState,
  SectionTitle,
} from "../primitives";
import { useToast } from "@/hooks/use-toast";
import {
  FileText,
  Loader2,
  Play,
  Sparkles,
  Download,
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
Disappointed with the delivery service`;

export function ReportsView() {
  const [meta, setMeta] = React.useState({
    title: "YouTube Audience Intelligence Report",
    objective: "",
    prepared_by: "",
    country: "",
    industry: "",
  });
  const [text, setText] = React.useState("");
  const [catalog, setCatalog] = React.useState("general");
  const [report, setReport] = React.useState<ReportResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [exporting, setExporting] = React.useState<"pdf" | "docx" | null>(null);
  const { toast } = useToast();

  const generate = async () => {
    const texts = text.split("\n").map((t) => t.trim()).filter(Boolean);
    if (texts.length < 3) {
      toast({ title: "Paste at least 3 comments", variant: "destructive" });
      return;
    }
    setLoading(true);
    setReport(null);
    try {
      const res = await api.reportGenerate(texts, meta, catalog);
      setReport(res);
    } catch (e) {
      toast({ title: "Report generation failed", description: e instanceof BackendError ? e.message : "error", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (format: "pdf" | "docx") => {
    const texts = text.split("\n").map((t) => t.trim()).filter(Boolean);
    if (texts.length < 3) {
      toast({ title: "Paste at least 3 comments first", variant: "destructive" });
      return;
    }
    setExporting(format);
    try {
      const blob = await api.reportExport(texts, meta, format, catalog);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audience-intelligence-report.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast({ title: `${format.toUpperCase()} downloaded`, description: `${(blob.size / 1024).toFixed(1)} KB` });
    } catch (e) {
      toast({ title: "Export failed", description: e instanceof BackendError ? e.message : "error", variant: "destructive" });
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Reports"
        description="Compile research into a structured, evidence-backed report — then download it as a real PDF or DOCX. Every section carries a provenance label; no fabricated metrics."
        icon={FileText}
      />

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Report inputs</CardTitle>
            <ProvenanceBadge provenance="USER_INPUT" />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Report title</Label>
              <Input value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Objective</Label>
              <Input value={meta.objective} onChange={(e) => setMeta({ ...meta, objective: e.target.value })} placeholder="Understand earbuds sentiment" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Prepared by</Label>
              <Input value={meta.prepared_by} onChange={(e) => setMeta({ ...meta, prepared_by: e.target.value })} placeholder="AudienceLens" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Country</Label>
              <Input value={meta.country} onChange={(e) => setMeta({ ...meta, country: e.target.value })} placeholder="PK" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Industry</Label>
              <Input value={meta.industry} onChange={(e) => setMeta({ ...meta, industry: e.target.value })} placeholder="Consumer electronics" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Aspect catalog</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={catalog}
                onChange={(e) => setCatalog(e.target.value)}
              >
                <option value="general">General</option>
                <option value="product">Product review</option>
                <option value="youtube">YouTube content</option>
                <option value="fashion">Fashion / e-commerce</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Comments — one per line</Label>
            <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={SAMPLE} rows={6} className="scroll-thin" />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={generate} disabled={loading} className="gap-2">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Generate report
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setText(SAMPLE)} className="gap-1">
              <Sparkles className="h-3.5 w-3.5" /> Load sample
            </Button>
            <span className="text-[11px] text-muted-foreground ml-2">
              Calls <code className="rounded bg-muted px-1">POST /api/v1/reports/generate</code> (backend reportlab + python-docx for export).
            </span>
          </div>
        </CardContent>
      </Card>

      {report && !report.error && (
        <div className="space-y-4">
          {/* Download bar */}
          <Card className="border-primary/30 bg-primary/5">
            <CardContent className="flex flex-wrap items-center gap-3 p-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground">{report.meta.title}</p>
                <p className="text-[11px] text-muted-foreground">
                  {report.n_comments} comments · {report.n_findings} findings · {report.sections.length} sections · generated {report.meta.generated_at.slice(0, 10)}
                </p>
              </div>
              <Button size="sm" onClick={() => exportReport("pdf")} disabled={!!exporting} className="gap-1.5">
                {exporting === "pdf" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                PDF
              </Button>
              <Button size="sm" variant="outline" onClick={() => exportReport("docx")} disabled={!!exporting} className="gap-1.5">
                {exporting === "docx" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                DOCX
              </Button>
              <ProvenanceBadge provenance={report.provenance as Provenance} />
            </CardContent>
          </Card>

          {/* Report sections */}
          {report.sections.map((sec) => (
            <ReportSectionCard key={sec.id} section={sec} />
          ))}

          <p className="text-[11px] italic text-muted-foreground">{report.disclaimer}</p>
        </div>
      )}

      {!report && !loading && (
        <EmptyState
          icon={FileText}
          title="No report generated yet"
          description="Paste comments, fill in the metadata, and click Generate. The full structured report appears here and can be downloaded as PDF or DOCX."
          provenance="INSUFFICIENT_DATA"
        />
      )}
    </div>
  );
}

function ReportSectionCard({ section: s }: { section: ReportSection }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-foreground">{s.title}</h3>
          <ProvenanceBadge provenance={s.provenance} />
        </div>
        {s.body && <p className="mt-2 text-sm text-foreground">{s.body}</p>}

        {s.metrics && s.metrics.length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {s.metrics.map((m) => (
              <div key={m.label} className="rounded-md border border-border p-2">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{m.label}</p>
                <p className="text-sm font-semibold tabular-nums text-foreground">{m.value}</p>
              </div>
            ))}
          </div>
        )}

        {s.evidence && s.evidence.length > 0 && (
          <div className="mt-3 space-y-1">
            <SectionTitle>Evidence</SectionTitle>
            {s.evidence.map((ev, i) => (
              <p key={i} className="rounded-md bg-muted/50 px-2 py-1 text-[11px] italic text-muted-foreground">
                <span className="font-medium not-italic text-foreground">{ev.label}:</span> “{ev.value}”
              </p>
            ))}
          </div>
        )}

        {typeof s.confidence === "number" && (
          <div className="mt-3 space-y-1">
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Confidence</span>
              <span className="tabular-nums">{Math.round(s.confidence * 100)}%</span>
            </div>
            <Progress value={s.confidence * 100} className="h-1.5" />
          </div>
        )}

        {s.recommended_action && (
          <div className="mt-3 flex items-start gap-2 rounded-md border border-primary/20 bg-primary/5 p-2.5 text-xs">
            <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
            <div>
              <p className="font-medium text-foreground">Recommended action</p>
              <p className="text-muted-foreground">{s.recommended_action}</p>
            </div>
          </div>
        )}

        {s.note && <p className="mt-2 text-[11px] italic text-muted-foreground">{s.note}</p>}
      </CardContent>
    </Card>
  );
}
