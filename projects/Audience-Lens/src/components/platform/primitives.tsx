"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  CircleSlash,
  Database,
  FlaskConical,
  Lightbulb,
  Plug,
  Radio,
  Sparkles,
  UserCog,
  type LucideIcon,
} from "lucide-react";
import type { Provenance, ConnectionStatus } from "@/lib/types";

// ---------------------------------------------------------------------------
// Provenance badge — the core data-honesty primitive
// ---------------------------------------------------------------------------

const PROV_CONFIG: Record<
  Provenance,
  { label: string; icon: LucideIcon; className: string }
> = {
  LIVE_DATA: {
    label: "Live data",
    icon: Radio,
    className:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  },
  MODEL_PREDICTION: {
    label: "Model prediction",
    icon: Sparkles,
    className:
      "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  },
  ESTIMATED_SCENARIO: {
    label: "Estimated scenario",
    icon: FlaskConical,
    className:
      "border-orange-500/30 bg-orange-500/10 text-orange-700 dark:text-orange-400",
  },
  INFERENCE: {
    label: "Inference",
    icon: Lightbulb,
    className:
      "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-400",
  },
  USER_INPUT: {
    label: "User input",
    icon: UserCog,
    className:
      "border-slate-400/30 bg-slate-400/10 text-slate-600 dark:text-slate-300",
  },
  INSUFFICIENT_DATA: {
    label: "Insufficient data",
    icon: CircleSlash,
    className:
      "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400",
  },
};

export function ProvenanceBadge({
  provenance,
  className,
}: {
  provenance: Provenance;
  className?: string;
}) {
  const cfg = PROV_CONFIG[provenance];
  const Icon = cfg.icon;
  return (
    <span className={cn("prov-badge", cfg.className, className)}>
      <Icon className="h-3 w-3" aria-hidden />
      {cfg.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Connection pill
// ---------------------------------------------------------------------------

const CONN_STYLE: Record<
  ConnectionStatus,
  { dot: string; label: string; className: string }
> = {
  connected: {
    dot: "bg-emerald-500",
    label: "Connected",
    className: "text-emerald-700 dark:text-emerald-400",
  },
  disconnected: {
    dot: "bg-slate-400",
    label: "Not connected",
    className: "text-muted-foreground",
  },
  error: {
    dot: "bg-rose-500",
    label: "Error",
    className: "text-rose-700 dark:text-rose-400",
  },
  unknown: {
    dot: "bg-amber-500",
    label: "Unknown",
    className: "text-amber-700 dark:text-amber-400",
  },
};

export function ConnectionPill({
  status,
  label,
  className,
}: {
  status: ConnectionStatus;
  label?: string;
  className?: string;
}) {
  const cfg = CONN_STYLE[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs font-medium",
        cfg.className,
        className
      )}
    >
      <span className={cn("h-2 w-2 rounded-full", cfg.dot)} />
      {label ?? cfg.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Empty state — honest, never fake
// ---------------------------------------------------------------------------

export function EmptyState({
  icon: Icon = BarChart3,
  title,
  description,
  action,
  provenance = "INSUFFICIENT_DATA",
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  provenance?: Provenance;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/30 px-6 py-12 text-center",
        className
      )}
    >
      <div className="mb-3 rounded-full bg-muted p-3 text-muted-foreground">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">
        {description}
      </p>
      <div className="mt-4 flex items-center gap-2">
        <ProvenanceBadge provenance={provenance} />
        {action}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// KPI card
// ---------------------------------------------------------------------------

export function KpiCard({
  label,
  value,
  sub,
  provenance,
  icon: Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  provenance: Provenance;
  icon?: LucideIcon;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {label}
            </p>
            <p className="text-2xl font-semibold tabular-nums text-foreground">
              {value}
            </p>
            {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
          </div>
          {Icon && (
            <div className="rounded-md bg-primary/10 p-2 text-primary">
              <Icon className="h-4 w-4" />
            </div>
          )}
        </div>
        <div className="mt-3">
          <ProvenanceBadge provenance={provenance} />
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// View header — used by every module view
// ---------------------------------------------------------------------------

export function ViewHeader({
  title,
  description,
  icon: Icon,
  actions,
}: {
  title: string;
  description: string;
  icon?: LucideIcon;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
            <Icon className="h-5 w-5" />
          </div>
        )}
        <div>
          <h1 className="text-xl font-semibold text-foreground">{title}</h1>
          <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
            {description}
          </p>
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Module shell — wraps an analytical view with a provenance strip + body
// ---------------------------------------------------------------------------

export function ModuleShell({
  title,
  description,
  icon,
  actions,
  dependencies,
  children,
}: {
  title: string;
  description: string;
  icon?: LucideIcon;
  actions?: React.ReactNode;
  dependencies?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6">
      <ViewHeader
        title={title}
        description={description}
        icon={icon}
        actions={actions}
      />
      {dependencies && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-2.5 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Dependencies:</span>
          {dependencies}
        </div>
      )}
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Quota bar — YouTube API units
// ---------------------------------------------------------------------------

export function QuotaBar({
  used,
  total,
  label = "API quota",
}: {
  used: number;
  total: number;
  label?: string;
}) {
  const pct = total > 0 ? Math.min(100, (used / total) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums text-muted-foreground">
          {used.toLocaleString()} / {total.toLocaleString()} units
        </span>
      </div>
      <Progress value={pct} className="h-2" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Data disclaimer caption
// ---------------------------------------------------------------------------

export function SampleDisclaimer({
  children = "Percentages represent the collected sample, not the entire YouTube audience.",
}: {
  children?: React.ReactNode;
}) {
  return (
    <p className="flex items-center gap-1.5 text-[11px] italic text-muted-foreground">
      <AlertTriangle className="h-3 w-3" />
      {children}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Section title
// ---------------------------------------------------------------------------

export function SectionTitle({
  children,
  icon: Icon,
}: {
  children: React.ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
      {Icon && <Icon className="h-4 w-4" />}
      {children}
    </h2>
  );
}

export { Card, CardContent, CardHeader, CardTitle, Badge, Separator, Database, Plug, CheckCircle2 };
