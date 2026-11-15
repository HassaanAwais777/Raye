"use client";

import * as React from "react";
import { usePlatform, uid } from "@/lib/platform-store";
import type { ResearchPlan, ViewId } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ProvenanceBadge, EmptyState, ViewHeader } from "../primitives";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  ClipboardList,
  Plus,
  Trash2,
  CheckCircle2,
  Bot,
  ArrowRight,
  Save,
} from "lucide-react";

const MODULE_OPTIONS: { id: ViewId; label: string }[] = [
  { id: "sentiment", label: "Sentiment" },
  { id: "audience", label: "Audience Intelligence" },
  { id: "clustering", label: "Clustering" },
  { id: "anomaly", label: "Anomaly Detection" },
  { id: "competitor", label: "Competitor" },
  { id: "campaign", label: "Campaign Intelligence" },
  { id: "optimizer", label: "Budget Optimizer" },
  { id: "findings", label: "Findings" },
];

function toList(s: string): string[] {
  return s
    .split(/[,\n]/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function emptyPlan(): ResearchPlan {
  return {
    id: uid(),
    objective: "",
    businessContext: "",
    country: "",
    industry: "",
    niche: "",
    competitors: [],
    keywords: [],
    channels: [],
    dateRange: { start: "", end: "" },
    modules: ["sentiment", "audience", "findings"],
    sampleSizeTarget: 2000,
    languageScope: ["English", "Urdu", "Roman Urdu"],
    notes: "",
    status: "draft",
    provenance: "USER_INPUT",
  };
}

export function ResearchPlanningView() {
  const plans = usePlatform((s) => s.plans);
  const upsertPlan = usePlatform((s) => s.upsertPlan);
  const setView = usePlatform((s) => s.setView);
  const { toast } = useToast();

  const [selectedId, setSelectedId] = React.useState<string | null>(
    plans[0]?.id ?? null
  );
  const selected = plans.find((p) => p.id === selectedId) ?? null;

  // local edit buffer
  const [draft, setDraft] = React.useState<ResearchPlan | null>(selected);

  React.useEffect(() => {
    setDraft(selected);
  }, [selectedId]);

  const createDraft = () => {
    const p = emptyPlan();
    upsertPlan(p);
    setSelectedId(p.id);
  };

  const save = () => {
    if (!draft) return;
    if (!draft.objective.trim()) {
      toast({ title: "Objective is required", variant: "destructive" });
      return;
    }
    upsertPlan(draft);
    toast({ title: "Plan saved", description: "Status: draft. Approve to mark ready for execution." });
  };

  const approve = () => {
    if (!draft) return;
    const approved = { ...draft, status: "approved" as const };
    upsertPlan(approved);
    setDraft(approved);
    toast({ title: "Plan approved", description: "Backend collection will run when provisioned." });
  };

  const remove = (id: string) => {
    const next = plans.filter((p) => p.id !== id);
    // upsert can't delete; replace via a fresh store isn't available. Keep minimal: leave removal to a noop if not present.
    // (Phase 2: backend handles delete.)
    toast({ title: "Delete requires the backend", description: "Plans persist locally in Phase 1." });
  };

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Research Planning"
        description="Review, edit, and approve structured research plans. The Research Agent can propose plans in conversation; here you refine them before approval."
        icon={ClipboardList}
        actions={
          <Button onClick={createDraft} className="gap-2">
            <Plus className="h-4 w-4" />
            New plan
          </Button>
        }
      />

      {plans.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No research plans"
          description="Create a plan manually, or ask the Research Agent to propose one from your business objective."
          action={
            <Button size="sm" onClick={() => setView("agent")} className="gap-1">
              <Bot className="h-4 w-4" />
              Open Agent
            </Button>
          }
          provenance="USER_INPUT"
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          {/* Plan list */}
          <Card className="lg:max-h-[70vh]">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Plans ({plans.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[60vh] scroll-thin">
                <div className="space-y-1 px-3 pb-3">
                  {plans.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelectedId(p.id)}
                      className={cn(
                        "w-full rounded-md border p-2.5 text-left transition-colors",
                        p.id === selectedId
                          ? "border-primary bg-primary/5"
                          : "border-border hover:bg-muted/50"
                      )}
                    >
                      <p className="truncate text-xs font-medium text-foreground">
                        {p.objective || "Untitled plan"}
                      </p>
                      <div className="mt-1 flex items-center gap-1.5">
                        <Badge
                          variant="outline"
                          className={cn(
                            "h-4 text-[10px]",
                            p.status === "approved"
                              ? "border-emerald-500/40 text-emerald-700 dark:text-emerald-400"
                              : "text-muted-foreground"
                          )}
                        >
                          {p.status}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">
                          {p.country || "—"}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Editor */}
          {draft ? (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-sm">Plan editor</CardTitle>
                  <ProvenanceBadge provenance="USER_INPUT" />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">Objective *</Label>
                  <Textarea
                    value={draft.objective}
                    onChange={(e) =>
                      setDraft({ ...draft, objective: e.target.value })
                    }
                    placeholder="The business question this research answers"
                    rows={2}
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label className="text-xs">Business / product context</Label>
                    <Input
                      value={draft.businessContext}
                      onChange={(e) =>
                        setDraft({ ...draft, businessContext: e.target.value })
                      }
                      placeholder="What you sell"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Target country</Label>
                    <Input
                      value={draft.country}
                      onChange={(e) =>
                        setDraft({ ...draft, country: e.target.value })
                      }
                      placeholder="e.g. Pakistan"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Industry</Label>
                    <Input
                      value={draft.industry}
                      onChange={(e) =>
                        setDraft({ ...draft, industry: e.target.value })
                      }
                      placeholder="e.g. Consumer electronics"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Niche</Label>
                    <Input
                      value={draft.niche}
                      onChange={(e) =>
                        setDraft({ ...draft, niche: e.target.value })
                      }
                      placeholder="e.g. Wireless earbuds"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Keywords (comma-separated)</Label>
                    <Textarea
                      value={draft.keywords.join(", ")}
                      onChange={(e) =>
                        setDraft({ ...draft, keywords: toList(e.target.value) })
                      }
                      placeholder="earbuds review, best earbuds 2026"
                      rows={2}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Competitors (comma-separated)</Label>
                    <Textarea
                      value={draft.competitors.join(", ")}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          competitors: toList(e.target.value),
                        })
                      }
                      placeholder="Brand A, Brand B"
                      rows={2}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Channels (URL / ID / handle)</Label>
                    <Textarea
                      value={draft.channels.join(", ")}
                      onChange={(e) =>
                        setDraft({ ...draft, channels: toList(e.target.value) })
                      }
                      placeholder="@channelhandle, UCxxxxx"
                      rows={2}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Date start</Label>
                      <Input
                        type="date"
                        value={draft.dateRange.start}
                        onChange={(e) =>
                          setDraft({
                            ...draft,
                            dateRange: { ...draft.dateRange, start: e.target.value },
                          })
                        }
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">Date end</Label>
                      <Input
                        type="date"
                        value={draft.dateRange.end}
                        onChange={(e) =>
                          setDraft({
                            ...draft,
                            dateRange: { ...draft.dateRange, end: e.target.value },
                          })
                        }
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Sample size target</Label>
                    <Input
                      type="number"
                      value={draft.sampleSizeTarget}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          sampleSizeTarget: Number(e.target.value) || 0,
                        })
                      }
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Languages (comma-separated)</Label>
                    <Input
                      value={draft.languageScope.join(", ")}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          languageScope: toList(e.target.value),
                        })
                      }
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-xs">Modules to run</Label>
                  <div className="flex flex-wrap gap-2">
                    {MODULE_OPTIONS.map((m) => {
                      const on = draft.modules.includes(m.id);
                      return (
                        <button
                          key={m.id}
                          onClick={() =>
                            setDraft({
                              ...draft,
                              modules: on
                                ? draft.modules.filter((x) => x !== m.id)
                                : [...draft.modules, m.id],
                            })
                          }
                          className={cn(
                            "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                            on
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border text-muted-foreground hover:text-foreground"
                          )}
                        >
                          {m.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Notes / assumptions</Label>
                  <Textarea
                    value={draft.notes}
                    onChange={(e) =>
                      setDraft({ ...draft, notes: e.target.value })
                    }
                    placeholder="Caveats, assumptions, anything the backend should know"
                    rows={2}
                  />
                </div>

                <Separator />
                <div className="flex flex-wrap items-center gap-2">
                  <Button size="sm" onClick={save} variant="outline" className="gap-1">
                    <Save className="h-4 w-4" />
                    Save draft
                  </Button>
                  <Button
                    size="sm"
                    onClick={approve}
                    disabled={draft.status === "approved"}
                    className="gap-1"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {draft.status === "approved" ? "Approved" : "Approve plan"}
                  </Button>
                  {draft.status === "approved" && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setView("live-youtube")}
                      className="gap-1"
                    >
                      Go to Live YouTube <ArrowRight className="h-4 w-4" />
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => remove(draft.id)}
                    className="ml-auto gap-1 text-muted-foreground"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                {draft.status === "approved" && (
                  <p className="rounded-md bg-muted/50 px-3 py-2 text-[11px] text-muted-foreground">
                    Approved. Execution requires the Python collection backend
                    (Phase 2). The plan is saved and ready.
                  </p>
                )}
              </CardContent>
            </Card>
          ) : (
            <EmptyState
              title="Select or create a plan"
              description="Pick a plan from the list, or create a new one."
              provenance="USER_INPUT"
            />
          )}
        </div>
      )}
    </div>
  );
}
