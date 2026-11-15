"use client";

import * as React from "react";
import { usePlatform } from "@/lib/platform-store";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { AppSidebar } from "@/components/platform/sidebar";
import { AgentView } from "@/components/platform/views/agent-view";
import { DashboardView } from "@/components/platform/views/dashboard-view";
import { SettingsView } from "@/components/platform/views/settings-view";
import { ResearchPlanningView } from "@/components/platform/views/research-planning-view";
import { LiveYouTubeView } from "@/components/platform/views/live-youtube-view";
import { OptimizerView } from "@/components/platform/views/optimizer-view";
import { SentimentView } from "@/components/platform/views/sentiment-view";
import { ClusteringView } from "@/components/platform/views/clustering-view";
import { AnomalyView } from "@/components/platform/views/anomaly-view";
import { FindingsView } from "@/components/platform/views/findings-view";
import { ReportsView } from "@/components/platform/views/reports-view";
import {
  AudienceView,
  CompetitorView,
  CampaignView,
  HistoryView,
} from "@/components/platform/views/analytics-views";
import type { ViewId } from "@/lib/types";
import {
  Bot,
  Plus,
  type LucideIcon,
} from "lucide-react";

const VIEW_TITLES: Record<ViewId, string> = {
  agent: "Research Agent",
  dashboard: "Dashboard",
  "research-planning": "Research Planning",
  "live-youtube": "Live YouTube Research",
  sentiment: "Sentiment",
  audience: "Audience Intelligence",
  clustering: "Clustering",
  anomaly: "Anomaly Detection",
  competitor: "Competitor",
  campaign: "Campaign Intelligence",
  optimizer: "Budget Optimizer",
  findings: "Findings",
  history: "Research History",
  reports: "Reports",
  settings: "Settings",
};

function renderView(view: ViewId): React.ReactNode {
  switch (view) {
    case "agent":
      return <AgentView />;
    case "dashboard":
      return <DashboardView />;
    case "research-planning":
      return <ResearchPlanningView />;
    case "live-youtube":
      return <LiveYouTubeView />;
    case "sentiment":
      return <SentimentView />;
    case "audience":
      return <AudienceView />;
    case "clustering":
      return <ClusteringView />;
    case "anomaly":
      return <AnomalyView />;
    case "competitor":
      return <CompetitorView />;
    case "campaign":
      return <CampaignView />;
    case "optimizer":
      return <OptimizerView />;
    case "findings":
      return <FindingsView />;
    case "history":
      return <HistoryView />;
    case "reports":
      return <ReportsView />;
    case "settings":
      return <SettingsView />;
    default:
      return <DashboardView />;
  }
}

export default function Home() {
  const activeView = usePlatform((s) => s.activeView);
  const setView = usePlatform((s) => s.setView);
  const createConversation = usePlatform((s) => s.createConversation);
  const isAgent = activeView === "agent";

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <AppSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        {!isAgent && (
          <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/95 pl-14 pr-4 backdrop-blur lg:pl-6">
            <h1 className="text-sm font-semibold text-foreground">
              {VIEW_TITLES[activeView]}
            </h1>
            <div className="ml-auto flex items-center gap-2">
              {activeView !== "dashboard" && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => setView("dashboard")}
                >
                  Dashboard
                </Button>
              )}
              <Button
                size="sm"
                className="gap-1.5"
                onClick={() => {
                  if (!isAgent) setView("agent");
                  else createConversation();
                }}
              >
                {isAgent ? (
                  <>
                    <Plus className="h-4 w-4" />
                    New session
                  </>
                ) : (
                  <>
                    <Bot className="h-4 w-4" />
                    Open Agent
                  </>
                )}
              </Button>
            </div>
          </header>
        )}
        <main
          className={cn(
            "flex-1 overflow-hidden",
            isAgent ? "" : "overflow-y-auto p-4 scroll-thin lg:p-6"
          )}
        >
          {renderView(activeView)}
        </main>
      </div>
    </div>
  );
}
