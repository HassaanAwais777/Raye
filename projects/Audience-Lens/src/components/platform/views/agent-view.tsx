"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import { usePlatform, useCurrentConversation, uid } from "@/lib/platform-store";
import type { ChatMessage, ResearchPlan } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ProvenanceBadge } from "../primitives";
import { api, BackendError } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import {
  Bot,
  Send,
  Sparkles,
  Plus,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Loader2,
  AlertCircle,
  Download,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Plan extraction + card
// ---------------------------------------------------------------------------

function extractPlan(content: string): { plan: ResearchPlan | null; text: string } {
  const fence = /```json\s*([\s\S]*?)```/i.exec(content);
  if (!fence) return { plan: null, text: content };
  try {
    const parsed = JSON.parse(fence[1]);
    if (parsed && typeof parsed.objective === "string" && Array.isArray(parsed.modules)) {
      const plan: ResearchPlan = {
        id: uid(),
        objective: parsed.objective ?? "",
        businessContext: parsed.businessContext ?? "",
        country: parsed.country ?? "",
        industry: parsed.industry ?? "",
        niche: parsed.niche ?? "",
        competitors: Array.isArray(parsed.competitors) ? parsed.competitors : [],
        keywords: Array.isArray(parsed.keywords) ? parsed.keywords : [],
        channels: Array.isArray(parsed.channels) ? parsed.channels : [],
        dateRange: parsed.dateRange ?? { start: "", end: "" },
        modules: parsed.modules,
        sampleSizeTarget: parsed.sampleSizeTarget ?? 1000,
        languageScope: Array.isArray(parsed.languageScope) ? parsed.languageScope : [],
        notes: parsed.notes ?? "",
        status: "proposed",
        provenance: "USER_INPUT",
      };
      const text = content.replace(fence[0], "").trim();
      return { plan, text };
    }
  } catch {
    /* fall through */
  }
  return { plan: null, text: content };
}

// ---------------------------------------------------------------------------
// Tool-run extraction + card (shows what backend tools the agent executed)
// ---------------------------------------------------------------------------

interface ToolRun {
  name: string;
  summary: string;
  args?: { texts?: string[]; meta?: Record<string, string> };
}

function extractToolRuns(content: string): { tools: ToolRun[] | null; text: string } {
  const fence = /```tools\s*([\s\S]*?)```/i.exec(content);
  if (!fence) return { tools: null, text: content };
  try {
    const parsed = JSON.parse(fence[1]);
    if (Array.isArray(parsed) && parsed.length > 0) {
      const runs: ToolRun[] = parsed
        .filter((r: unknown) => r && typeof (r as ToolRun).name === "string")
        .map((r: any) => ({
          name: r.name,
          summary: r.summary || "",
          ...(r.args ? { args: r.args } : {}),
        }));
      if (runs.length > 0) {
        return { tools: runs, text: content.replace(fence[0], "").trim() };
      }
    }
  } catch {
    /* fall through */
  }
  return { tools: null, text: content };
}

const TOOL_LABELS: Record<string, string> = {
  analyze_sentiment: "Sentiment analysis",
  cluster_comments: "Clustering",
  generate_findings: "Findings",
  youtube_research: "YouTube research",
  generate_report: "Report",
};

function ToolRunsCard({ runs }: { runs: ToolRun[] }) {
  const [exporting, setExporting] = React.useState<string | null>(null);
  const { toast } = useToast();

  const download = async (r: ToolRun, format: "pdf" | "docx") => {
    if (!r.args?.texts) return;
    setExporting(format);
    try {
      const blob = await api.reportExport(r.args.texts, r.args.meta || {}, format);
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
    <div className="mt-3 space-y-1.5">
      <p className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        <Sparkles className="h-3 w-3" />
        Backend tools executed
      </p>
      {runs.map((r, i) => (
        <div key={i} className="rounded-md border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-xs">
          <div className="flex items-start gap-2">
            <Badge className="shrink-0 bg-primary/15 text-primary">{TOOL_LABELS[r.name] || r.name}</Badge>
            <span className="text-foreground">{r.summary}</span>
          </div>
          {r.name === "generate_report" && r.args?.texts && (
            <div className="mt-1.5 flex gap-1.5">
              <Button size="sm" variant="outline" className="h-6 gap-1 text-[11px]" onClick={() => download(r, "pdf")} disabled={!!exporting}>
                {exporting === "pdf" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />} PDF
              </Button>
              <Button size="sm" variant="outline" className="h-6 gap-1 text-[11px]" onClick={() => download(r, "docx")} disabled={!!exporting}>
                {exporting === "docx" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />} DOCX
              </Button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function PlanCard({ plan }: { plan: ResearchPlan }) {
  const upsertPlan = usePlatform((s) => s.upsertPlan);
  const approvePlan = usePlatform((s) => s.approvePlan);
  const setView = usePlatform((s) => s.setView);
  const plans = usePlatform((s) => s.plans);
  const existing = plans.find((p) => p.id === plan.id);
  const approved = existing?.status === "approved";

  return (
    <Card className="mt-3 border-primary/30">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <ClipboardList className="h-4 w-4 text-primary" />
            Proposed research plan
          </CardTitle>
          <ProvenanceBadge provenance="USER_INPUT" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Objective
          </p>
          <p className="text-foreground">{plan.objective}</p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Field label="Country" value={plan.country} />
          <Field label="Industry" value={plan.industry} />
          <Field label="Niche" value={plan.niche} />
          <Field label="Sample target" value={String(plan.sampleSizeTarget)} />
          <Field
            label="Date range"
            value={
              plan.dateRange.start || plan.dateRange.end
                ? `${plan.dateRange.start || "?"} → ${plan.dateRange.end || "?"}`
                : "—"
            }
          />
          <Field label="Languages" value={plan.languageScope.join(", ") || "—"} />
        </div>
        {plan.keywords.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Keywords
            </p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {plan.keywords.map((k, i) => (
                <Badge key={i} variant="secondary" className="font-normal">
                  {k}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {plan.competitors.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Competitors
            </p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {plan.competitors.map((k, i) => (
                <Badge key={i} variant="outline" className="font-normal">
                  {k}
                </Badge>
              ))}
            </div>
          </div>
        )}
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Modules
          </p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {plan.modules.map((m) => (
              <Badge key={m} className="font-normal">
                {m}
              </Badge>
            ))}
          </div>
        </div>
        {plan.notes && (
          <p className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
            {plan.notes}
          </p>
        )}
        <Separator />
        <div className="flex flex-wrap items-center gap-2">
          {approved ? (
            <Badge className="gap-1 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Approved — pending backend collection
            </Badge>
          ) : (
            <Button
              size="sm"
              onClick={() => {
                upsertPlan({ ...plan, status: "approved" });
                approvePlan(plan.id);
              }}
            >
              <CheckCircle2 className="h-4 w-4" />
              Approve plan
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              upsertPlan(plan);
              setView("research-planning");
            }}
          >
            <ArrowRight className="h-4 w-4" />
            Edit in Research Planning
          </Button>
        </div>
        <p className="text-[11px] text-muted-foreground">
          On approval, the backend collects via the official YouTube Data API v3.
          Collection runs periodically — not in real time.
        </p>
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="truncate text-foreground">{value || "—"}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  const afterPlan = isUser
    ? { plan: null as ResearchPlan | null, text: msg.content }
    : extractPlan(msg.content);
  const { plan, text: textAfterPlan } = afterPlan;
  const { tools, text } = isUser
    ? { tools: null as ToolRun[] | null, text: textAfterPlan }
    : extractToolRuns(textAfterPlan);

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-secondary text-secondary-foreground"
            : "bg-primary text-primary-foreground"
        )}
      >
        {isUser ? <span className="text-xs font-semibold">You</span> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "max-w-[85%] space-y-2 rounded-lg px-3.5 py-2.5 text-sm",
          isUser
            ? "bg-secondary text-secondary-foreground"
            : "bg-card text-card-foreground border border-border"
        )}
      >
        {text ? (
          <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-1 prose-p:leading-relaxed prose-ul:my-1 prose-li:my-0 prose-headings:mb-1 prose-headings:mt-2 prose-strong:font-semibold prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:before:content-none prose-code:after:content-none">
            <ReactMarkdown>{text}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-muted-foreground italic">…</p>
        )}
        {plan && <PlanCard plan={plan} />}
        {tools && <ToolRunsCard runs={tools} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Conversation switcher
// ---------------------------------------------------------------------------

function ConversationBar() {
  const conversations = usePlatform((s) => s.conversations);
  const currentId = usePlatform((s) => s.currentConversationId);
  const setCurrent = usePlatform((s) => s.setCurrentConversation);
  const createConversation = usePlatform((s) => s.createConversation);

  return (
    <div className="flex items-center gap-2 overflow-x-auto border-b border-border px-4 py-2 scroll-thin">
      <span className="text-xs font-medium text-muted-foreground shrink-0">
        Sessions
      </span>
      {conversations.map((c) => (
        <button
          key={c.id}
          onClick={() => setCurrent(c.id)}
          className={cn(
            "shrink-0 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
            c.id === currentId
              ? "border-primary bg-primary/10 text-primary"
              : "border-border text-muted-foreground hover:text-foreground"
          )}
        >
          {c.title}
        </button>
      ))}
      <Button
        size="sm"
        variant="ghost"
        className="h-7 shrink-0 gap-1 px-2 text-xs"
        onClick={() => createConversation()}
      >
        <Plus className="h-3.5 w-3.5" />
        New
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Quick-start suggestions
// ---------------------------------------------------------------------------

const SUGGESTIONS = [
  "Analyze these comments and tell me what people complain about vs. praise: amazing product love it; battery is terrible worst phone; price too high not worth it; great value highly recommend; screen broke useless; love the design beautiful.",
  "I sell wireless earbuds in Pakistan and want to understand what YouTube viewers complain about vs. praise.",
  "Run a full findings analysis on these: great camera; laggy performance; best purchase ever; waste of money scam; good battery but camera bad; highly recommend satisfied.",
  "Plan YouTube audience research for a 90-day earbuds campaign in PKR, then tell me which segments to target.",
];

// ---------------------------------------------------------------------------
// Main view
// ---------------------------------------------------------------------------

export function AgentView() {
  const conversation = useCurrentConversation();
  const addMessage = usePlatform((s) => s.addMessage);
  const updateLastAssistant = usePlatform((s) => s.updateLastAssistant);
  const agentBusy = usePlatform((s) => s.agentBusy);
  const setAgentBusy = usePlatform((s) => s.setAgentBusy);
  const [input, setInput] = React.useState("");
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const convId = conversation?.id ?? null;

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [conversation?.messages.length, agentBusy]);

  const send = async (text: string) => {
    if (!text.trim() || !convId || agentBusy) return;
    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: text.trim(),
      createdAt: new Date().toISOString(),
    };
    addMessage(convId, userMsg);
    setInput("");

    const placeholder: ChatMessage = {
      id: uid(),
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
    };
    addMessage(convId, placeholder);
    setAgentBusy(true);

    try {
      const history = (conversation?.messages ?? [])
        .filter((m) => m.role !== "system")
        .concat(userMsg)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });
      const data = await res.json();
      if (!res.ok) {
        updateLastAssistant(
          convId,
          `I couldn't reach the analysis backend just now: ${data?.error ?? "unknown error"}. Please retry in a moment.`
        );
      } else {
        updateLastAssistant(convId, data.content as string);
      }
    } catch (e) {
      updateLastAssistant(
        convId,
        `A network error occurred${e instanceof Error ? `: ${e.message}` : ""}. Please retry.`
      );
    } finally {
      setAgentBusy(false);
    }
  };

  const messages = conversation?.messages ?? [];
  const onlyWelcome = messages.length <= 1;

  return (
    <div className="flex h-full flex-col">
      <ConversationBar />
      <ScrollArea className="flex-1 scroll-thin" ref={scrollRef}>
        <div className="mx-auto max-w-3xl space-y-5 px-4 py-6">
          {messages.map((m) => (
            <MessageBubble key={m.id} msg={m} />
          ))}
          {agentBusy && (
            <div className="flex items-center gap-2 pl-11 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Agent is thinking…
            </div>
          )}
          {onlyWelcome && !agentBusy && (
            <div className="space-y-2 pl-11">
              <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5" />
                Try one of these to start
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-lg border border-border bg-card p-3 text-left text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
      <div className="border-t border-border bg-background">
        <div className="mx-auto max-w-3xl px-4 py-3">
          <div className="flex items-end gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              placeholder="Describe your business, product, target market, and what you want to learn…"
              className="min-h-[44px] max-h-32 resize-none scroll-thin"
              rows={1}
              disabled={agentBusy}
            />
            <Button
              onClick={() => send(input)}
              disabled={!input.trim() || agentBusy}
              size="icon"
              className="h-11 w-11 shrink-0"
              aria-label="Send message"
            >
              {agentBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="mt-1.5 flex items-center gap-1 text-[10px] text-muted-foreground">
            <AlertCircle className="h-3 w-3" />
            The agent plans and explains; you approve before any data is collected.
            Press Enter to send, Shift+Enter for a new line.
          </p>
        </div>
      </div>
    </div>
  );
}
