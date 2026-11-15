"use client";

import * as React from "react";
import { usePlatform } from "@/lib/platform-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  KpiCard,
  ViewHeader,
  ProvenanceBadge,
  ConnectionPill,
  EmptyState,
  SectionTitle,
} from "../primitives";
import { api, type HealthResult } from "@/lib/api";
import {
  MessageSquare,
  Users,
  Smile,
  Wallet,
  Bot,
  ArrowRight,
  Youtube,
  Megaphone,
  Database,
  Activity,
  ClipboardList,
  Plug,
} from "lucide-react";

export function DashboardView() {
  const plans = usePlatform((s) => s.plans);
  const connections = usePlatform((s) => s.connections);
  const setView = usePlatform((s) => s.setView);
  const conversations = usePlatform((s) => s.conversations);

  const approvedPlans = plans.filter((p) => p.status === "approved");
  const totalMessages = conversations.reduce((n, c) => n + c.messages.length, 0);

  const [health, setHealth] = React.useState<HealthResult | null>(null);
  React.useEffect(() => {
    let alive = true;
    api.health().then((h) => { if (alive) setHealth(h); }).catch(() => {});
    return () => { alive = false; };
  }, []);

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Dashboard"
        description="Operational overview of your YouTube audience & campaign intelligence workspace. All metrics are sourced from authorized live APIs — never fabricated."
        icon={Activity}
        actions={
          <Button onClick={() => setView("agent")} className="gap-2">
            <Bot className="h-4 w-4" />
            Open Research Agent
          </Button>
        }
      />

      {/* Backend service status — live from the Python FastAPI process */}
      <Card className={health ? "border-emerald-500/30" : "border-muted"}>
        <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-2 p-4 text-xs">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            <span className="font-medium text-foreground">Backend service</span>
            <ConnectionPill status={health ? "connected" : "unknown"} label={health ? `v${health.version} · online` : "checking…"} />
          </div>
          {health && (
            <>
              <span className="text-muted-foreground">Modules: <span className="font-medium text-foreground">{Object.keys(health.modules).length}</span> ({Object.keys(health.modules).join(", ")})</span>
              <span className="flex items-center gap-1.5"><Youtube className="h-3.5 w-3.5" /> <ConnectionPill status={health.integrations.youtube_connected ? "connected" : "disconnected"} /></span>
              <span className="flex items-center gap-1.5"><Megaphone className="h-3.5 w-3.5" /> <ConnectionPill status={health.integrations.google_ads_connected ? "connected" : "disconnected"} /></span>
              <span className="flex items-center gap-1.5"><Database className="h-3.5 w-3.5" /> <ConnectionPill status={health.integrations.database.connected ? "connected" : "disconnected"} /></span>
            </>
          )}
          <ProvenanceBadge provenance="LIVE_DATA" className="ml-auto" />
        </CardContent>
      </Card>

      {/* KPIs — all INSUFFICIENT_DATA until the backend collects */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Comments analyzed"
          value="0"
          sub="Across all research sessions"
          provenance="INSUFFICIENT_DATA"
          icon={MessageSquare}
        />
        <KpiCard
          label="Audience segments"
          value="—"
          sub="Awaiting clustering run"
          provenance="INSUFFICIENT_DATA"
          icon={Users}
        />
        <KpiCard
          label="Avg. sentiment"
          value="—"
          sub="No NLP results yet"
          provenance="INSUFFICIENT_DATA"
          icon={Smile}
        />
        <KpiCard
          label="Budget scenarios"
          value={String(plans.length ? 0 : 0)}
          sub="Optimizer not yet run"
          provenance="INSUFFICIENT_DATA"
          icon={Wallet}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent plans */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <ClipboardList className="h-4 w-4 text-primary" />
                Research plans
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs"
                onClick={() => setView("research-planning")}
              >
                View all <ArrowRight className="h-3 w-3" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {plans.length === 0 ? (
              <EmptyState
                icon={ClipboardList}
                title="No research plans yet"
                description="Start a conversation with the Research Agent. It will propose a structured plan you can review and approve before any data is collected."
                action={
                  <Button size="sm" onClick={() => setView("agent")} className="gap-1">
                    <Bot className="h-4 w-4" />
                    Open Agent
                  </Button>
                }
                provenance="USER_INPUT"
              />
            ) : (
              <div className="space-y-3">
                {plans.slice(0, 4).map((p) => (
                  <div
                    key={p.id}
                    className="flex items-start justify-between gap-3 rounded-lg border border-border p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {p.objective || "Untitled plan"}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">
                        {p.country || "—"} · {p.keywords.length} keywords ·{" "}
                        {p.modules.length} modules
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <ProvenanceBadge provenance="USER_INPUT" />
                      <Badge
                        variant="outline"
                        className={
                          p.status === "approved"
                            ? "border-emerald-500/40 text-emerald-700 dark:text-emerald-400"
                            : "text-muted-foreground"
                        }
                      >
                        {p.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Connections */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <Plug className="h-4 w-4 text-primary" />
                Integrations
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => setView("settings")}
              >
                Manage
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {connections.map((c) => {
              const Icon =
                c.id === "youtube"
                  ? Youtube
                  : c.id === "googleAds"
                  ? Megaphone
                  : c.id === "database"
                  ? Database
                  : Bot;
              return (
                <div
                  key={c.id}
                  className="flex items-start gap-2.5 rounded-lg border border-border p-2.5"
                >
                  <div className="rounded-md bg-muted p-1.5 text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-xs font-medium text-foreground">
                        {c.label}
                      </p>
                      <ConnectionPill status={c.status} />
                    </div>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      {c.detail}
                    </p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* Live-data policy banner */}
      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="flex items-start gap-3 p-4">
          <div className="rounded-md bg-primary/10 p-2 text-primary">
            <Activity className="h-4 w-4" />
          </div>
          <div className="text-sm">
            <p className="font-medium text-foreground">Strict live-data policy</p>
            <p className="mt-0.5 text-muted-foreground">
              Every figure in this platform is labeled with its provenance —{" "}
              <ProvenanceBadge provenance="LIVE_DATA" />,{" "}
              <ProvenanceBadge provenance="MODEL_PREDICTION" />,{" "}
              <ProvenanceBadge provenance="ESTIMATED_SCENARIO" />,{" "}
              <ProvenanceBadge provenance="INFERENCE" />,{" "}
              <ProvenanceBadge provenance="USER_INPUT" />, or{" "}
              <ProvenanceBadge provenance="INSUFFICIENT_DATA" />. No synthetic
              data, demo seeding, or fabricated metrics are ever shown as live.
            </p>
          </div>
        </CardContent>
      </Card>

      <Separator />
      <SectionTitle icon={Activity}>Session activity</SectionTitle>
      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard
          label="Conversations"
          value={String(conversations.length)}
          sub="Agent sessions"
          provenance="USER_INPUT"
          icon={Bot}
        />
        <KpiCard
          label="Messages exchanged"
          value={String(totalMessages)}
          sub="Across all sessions"
          provenance="USER_INPUT"
          icon={MessageSquare}
        />
        <KpiCard
          label="Approved plans"
          value={String(approvedPlans.length)}
          sub="Awaiting backend execution"
          provenance="USER_INPUT"
          icon={ClipboardList}
        />
      </div>
    </div>
  );
}
