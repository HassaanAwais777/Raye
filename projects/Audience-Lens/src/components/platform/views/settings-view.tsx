"use client";

import * as React from "react";
import { usePlatform } from "@/lib/platform-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ConnectionPill, ProvenanceBadge, ViewHeader } from "../primitives";
import { api, BackendError } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import type { Connection } from "@/lib/types";
import {
  Youtube,
  Megaphone,
  Database,
  Bot,
  KeyRound,
  ShieldCheck,
  ExternalLink,
  FlaskConical,
  CheckCircle2,
} from "lucide-react";

function IntegrationCard({
  conn,
  icon: Icon,
  children,
}: {
  conn: Connection;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <div className="rounded-md bg-primary/10 p-1.5 text-primary">
              <Icon className="h-4 w-4" />
            </div>
            {conn.label}
          </CardTitle>
          <ConnectionPill status={conn.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">{conn.detail}</p>
        {conn.quotaTotal !== undefined && (
          <p className="text-[11px] text-muted-foreground">
            Quota: {(conn.quotaUsed ?? 0).toLocaleString()} /{" "}
            {conn.quotaTotal.toLocaleString()} units/day
          </p>
        )}
        {children}
      </CardContent>
    </Card>
  );
}

export function SettingsView() {
  const connections = usePlatform((s) => s.connections);
  const setConnection = usePlatform((s) => s.setConnection);
  const { toast } = useToast();

  const yt = connections.find((c) => c.id === "youtube")!;
  const ads = connections.find((c) => c.id === "googleAds")!;
  const llm = connections.find((c) => c.id === "llm")!;
  const db = connections.find((c) => c.id === "database")!;

  const [ytKey, setYtKey] = React.useState("");
  const [adsCfg, setAdsCfg] = React.useState({
    developerToken: "",
    customerId: "",
    refreshToken: "",
  });
  const [neonUrl, setNeonUrl] = React.useState("");

  const saveYouTube = async () => {
    if (!ytKey.trim()) {
      toast({ title: "Enter an API key first", variant: "destructive" });
      return;
    }
    try {
      const s = await api.youtubeConfigure(ytKey.trim());
      setConnection("youtube", {
        status: s.connected ? "connected" : "disconnected",
        detail: s.detail,
        quotaUsed: s.quota.used,
        quotaTotal: s.quota.total,
      });
      setYtKey("");
      toast({
        title: s.connected ? "YouTube connected" : "Key not accepted",
        description: s.detail,
      });
    } catch (e) {
      toast({
        title: "Connection failed",
        description: e instanceof BackendError ? e.message : "Backend unreachable.",
        variant: "destructive",
      });
    }
  };

  const saveAds = () => {
    if (!adsCfg.developerToken.trim() || !adsCfg.customerId.trim()) {
      toast({ title: "Developer token and customer ID are required", variant: "destructive" });
      return;
    }
    setConnection("googleAds", {
      status: "connected",
      detail:
        "Google Ads credentials recorded for this session. GAQL campaign metrics activate once the Python backend is provisioned. Until then the optimizer runs in ESTIMATED_SCENARIO mode.",
    });
    setAdsCfg({ developerToken: "", customerId: "", refreshToken: "" });
    toast({ title: "Google Ads configuration saved", description: "Real campaign metrics activate with the backend." });
  };

  const saveNeon = () => {
    if (!neonUrl.trim().startsWith("postgres")) {
      toast({ title: "Enter a valid postgresql:// connection string", variant: "destructive" });
      return;
    }
    setConnection("database", {
      status: "connected",
      detail:
        "Neon DATABASE_URL recorded for this session. Migrations and persistence activate when the Python backend (SQLAlchemy + Alembic) is provisioned. DIRECT_URL should also be set for migrations.",
    });
    setNeonUrl("");
    toast({ title: "Neon configuration saved", description: "Persistence activates with the backend." });
  };

  return (
    <div className="space-y-6">
      <ViewHeader
        title="Settings & Integrations"
        description="Configure the authorized data sources the platform uses. Keys are never committed to Git or persisted in the browser — they are passed to the backend service as environment variables."
        icon={ShieldCheck}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        {/* YouTube */}
        <IntegrationCard conn={yt} icon={Youtube}>
          <div className="space-y-2">
            <Label htmlFor="yt-key" className="flex items-center gap-1.5 text-xs">
              <KeyRound className="h-3.5 w-3.5" />
              YouTube Data API v3 key
            </Label>
            <Input
              id="yt-key"
              type="password"
              placeholder="AIza…"
              value={ytKey}
              onChange={(e) => setYtKey(e.target.value)}
            />
            <div className="flex items-center justify-between">
              <a
                href="https://developers.google.com/youtube/v3/getting-started"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[11px] text-primary hover:underline"
              >
                Get a key <ExternalLink className="h-3 w-3" />
              </a>
              <Button size="sm" onClick={saveYouTube}>
                Save configuration
              </Button>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Used for <code className="rounded bg-muted px-1">search.list</code>,{" "}
              <code className="rounded bg-muted px-1">videos.list</code>,{" "}
              <code className="rounded bg-muted px-1">commentThreads.list</code>,{" "}
              <code className="rounded bg-muted px-1">playlistItems.list</code>. No scraping.
            </p>
          </div>
        </IntegrationCard>

        {/* Google Ads */}
        <IntegrationCard conn={ads} icon={Megaphone}>
          <div className="space-y-2">
            <Label className="text-xs">Developer token</Label>
            <Input
              type="password"
              placeholder="dev-token"
              value={adsCfg.developerToken}
              onChange={(e) =>
                setAdsCfg((s) => ({ ...s, developerToken: e.target.value }))
              }
            />
            <Label className="text-xs">Customer ID (XXX-XXX-XXXX)</Label>
            <Input
              placeholder="123-456-7890"
              value={adsCfg.customerId}
              onChange={(e) =>
                setAdsCfg((s) => ({ ...s, customerId: e.target.value }))
              }
            />
            <Label className="text-xs">OAuth2 refresh token</Label>
            <Input
              type="password"
              placeholder="refresh token"
              value={adsCfg.refreshToken}
              onChange={(e) =>
                setAdsCfg((s) => ({ ...s, refreshToken: e.target.value }))
              }
            />
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <FlaskConical className="h-3 w-3" />
                Without this, optimizer = ESTIMATED_SCENARIO
              </span>
              <Button size="sm" onClick={saveAds}>
                Save configuration
              </Button>
            </div>
          </div>
        </IntegrationCard>

        {/* Neon */}
        <IntegrationCard conn={db} icon={Database}>
          <div className="space-y-2">
            <Label className="text-xs">Neon DATABASE_URL (pooled runtime)</Label>
            <Input
              type="password"
              placeholder="postgresql://…@ep-…neon.tech/audiencelens?sslmode=require"
              value={neonUrl}
              onChange={(e) => setNeonUrl(e.target.value)}
            />
            <p className="text-[11px] text-muted-foreground">
              Set <code className="rounded bg-muted px-1">DIRECT_URL</code> on the
              backend for Alembic migrations. SQLite, MongoDB, and local Postgres
              are not permitted.
            </p>
            <Button size="sm" onClick={saveNeon}>
              Save configuration
            </Button>
          </div>
        </IntegrationCard>

        {/* LLM */}
        <IntegrationCard conn={llm} icon={Bot}>
          <div className="flex items-center gap-2 rounded-md bg-emerald-500/10 p-3 text-xs text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="h-4 w-4" />
            The Research Agent LLM is available via the platform backend.
          </div>
          <p className="text-[11px] text-muted-foreground">
            The agent plans, explains, and grounds answers in collected data. It
            never executes arbitrary SQL or unrestricted API requests.
          </p>
        </IntegrationCard>
      </div>

      <Separator />

      {/* Data policy reference */}
      <Card className="border-primary/20">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Platform data policy</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">
            Every insight surfaced in the platform carries one of these
            provenance labels:
          </p>
          <div className="flex flex-wrap gap-2">
            <ProvenanceBadge provenance="LIVE_DATA" />
            <ProvenanceBadge provenance="MODEL_PREDICTION" />
            <ProvenanceBadge provenance="ESTIMATED_SCENARIO" />
            <ProvenanceBadge provenance="INFERENCE" />
            <ProvenanceBadge provenance="USER_INPUT" />
            <ProvenanceBadge provenance="INSUFFICIENT_DATA" />
          </div>
          <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
            <li>No synthetic data, demo seeding, or fabricated metrics are shown as live.</li>
            <li>Organic YouTube statistics are never blended with paid Google Ads metrics.</li>
            <li>No age/gender/identity claims from comments — segments are analytical clusters.</li>
            <li>API quota is tracked and respected; collection is periodic, not real-time.</li>
            <li>Percentages represent the collected sample, not the entire YouTube audience.</li>
          </ul>
          <div className="flex flex-wrap gap-2 pt-1">
            <Badge variant="outline">Neon PostgreSQL only</Badge>
            <Badge variant="outline">YouTube Data API v3</Badge>
            <Badge variant="outline">Google Ads API</Badge>
            <Badge variant="outline">Modular monolith</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
