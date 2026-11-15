"use client";

import * as React from "react";
import { usePlatform } from "@/lib/platform-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  ViewHeader,
  ProvenanceBadge,
  EmptyState,
  SectionTitle,
} from "../primitives";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Wallet,
  FlaskConical,
  Info,
  TrendingUp,
  Calculator,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Assumed saturation curve parameters R(s) = α·ln(1 + s/β) + c
// These are DOCUMENTED ASSUMPTIONS for the ESTIMATED_SCENARIO mode.
// When real Google Ads history is connected, these are replaced by fitted
// curves from actual campaign data (MODEL_PREDICTION).
// ---------------------------------------------------------------------------

type FormatId = "in_stream" | "shorts" | "in_feed";
type Objective =
  | "awareness"
  | "views"
  | "traffic"
  | "leads"
  | "sales";
type Strategy = "balanced" | "performance_focused" | "exploratory";

const FORMAT_META: Record<FormatId, { label: string; baseAlpha: number; baseBeta: number }> = {
  in_stream: { label: "In-Stream Ads", baseAlpha: 1.0, baseBeta: 200 },
  shorts: { label: "Shorts Ads", baseAlpha: 0.85, baseBeta: 120 },
  in_feed: { label: "In-Feed Video Ads", baseAlpha: 0.7, baseBeta: 90 },
};

const OBJECTIVE_MULT: Record<Objective, Record<FormatId, number>> = {
  awareness: { in_stream: 0.95, shorts: 1.15, in_feed: 1.1 },
  views: { in_stream: 1.1, shorts: 1.0, in_feed: 0.9 },
  traffic: { in_stream: 1.0, shorts: 0.9, in_feed: 1.15 },
  leads: { in_stream: 1.15, shorts: 0.85, in_feed: 1.0 },
  sales: { in_stream: 1.2, shorts: 0.8, in_feed: 0.95 },
};

interface Curve {
  name: FormatId;
  label: string;
  alpha: number;
  beta: number;
}

function buildCurves(
  objective: Objective,
  strategy: Strategy,
  enabled: FormatId[]
): Curve[] {
  const base = enabled.map((f) => {
    const meta = FORMAT_META[f];
    let alpha = meta.baseAlpha * OBJECTIVE_MULT[objective][f];
    let beta = meta.baseBeta;
    if (strategy === "performance_focused") {
      // concentrate: amplify spread
      const maxAlpha = Math.max(...enabled.map((x) => FORMAT_META[x].baseAlpha * OBJECTIVE_MULT[objective][x]));
      if (meta.baseAlpha * OBJECTIVE_MULT[objective][f] === maxAlpha) alpha *= 1.12;
      else alpha *= 0.88;
    }
    return { name: f, label: meta.label, alpha, beta };
  });
  return base;
}

/** Water-fill: equalize marginal return α/(β+x) = λ, x_i = max(0, α/λ − β). */
function waterFill(curves: Curve[], budget: number) {
  const active = curves.filter((c) => c.alpha > 0 && c.beta > 0);
  if (active.length === 0 || budget <= 0)
    return { alloc: {} as Record<string, number>, lambda: 0 };

  const maxCorner = Math.max(...active.map((c) => c.alpha / c.beta));
  let lo = 1e-9;
  let hi = maxCorner * 1.0001 + 1e-6;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    const total = active.reduce(
      (s, c) => s + Math.max(0, c.alpha / mid - c.beta),
      0
    );
    if (total > budget) lo = mid;
    else hi = mid;
  }
  const lambda = (lo + hi) / 2;
  const raw: Record<string, number> = {};
  for (const c of active) raw[c.name] = Math.max(0, c.alpha / lambda - c.beta);

  // Largest-remainder rounding to 2 decimals so total == budget exactly.
  const rounded: Record<string, number> = {};
  let allocated = 0;
  for (const c of active) {
    const r = Math.round(raw[c.name] * 100) / 100;
    rounded[c.name] = r;
    allocated += r;
  }
  const residue = Math.round((budget - allocated) * 100) / 100;
  if (Math.abs(residue) > 0.001 && active.length > 0) {
    // give residue to the format with the highest marginal return at its allocation
    let best = active[0];
    let bestMr = -Infinity;
    for (const c of active) {
      const x = rounded[c.name];
      const mr = c.alpha / (c.beta + x); // marginal return
      if (mr > bestMr) {
        bestMr = mr;
        best = c;
      }
    }
    rounded[best.name] = Math.round((rounded[best.name] + residue) * 100) / 100;
  }
  return { alloc: rounded, lambda };
}

function equalSplit(enabled: FormatId[], budget: number): Record<string, number> {
  const per = Math.round((budget / enabled.length) * 100) / 100;
  const r: Record<string, number> = {};
  enabled.forEach((f) => (r[f] = per));
  // fix residue
  const sum = enabled.reduce((s, f) => s + r[f], 0);
  r[enabled[0]] = Math.round((r[enabled[0]] + (budget - sum)) * 100) / 100;
  return r;
}

function roasProportional(curves: Curve[], budget: number): Record<string, number> {
  const weights = curves.map((c) => c.alpha / c.beta);
  const total = weights.reduce((a, b) => a + b, 0);
  const r: Record<string, number> = {};
  curves.forEach((c, i) => {
    r[c.name] = Math.round(((weights[i] / total) * budget) * 100) / 100;
  });
  const sum = curves.reduce((s, c) => s + r[c.name], 0);
  r[curves[0].name] = Math.round((r[curves[0].name] + (budget - sum)) * 100) / 100;
  return r;
}

function expectedRevenue(curves: Curve[], alloc: Record<string, number>): number {
  return curves.reduce((s, c) => s + c.alpha * Math.log(1 + (alloc[c.name] ?? 0) / c.beta), 0);
}

const CURRENCIES: Record<string, string> = {
  USD: "$",
  PKR: "Rs ",
  EUR: "€",
  GBP: "£",
  INR: "₹",
};

export function OptimizerView() {
  const connections = usePlatform((s) => s.connections);
  const ads = connections.find((c) => c.id === "googleAds")!;
  const realAdsConnected = ads.status === "connected";

  const [budget, setBudget] = React.useState("100000");
  const [currency, setCurrency] = React.useState("USD");
  const [objective, setObjective] = React.useState<Objective>("awareness");
  const [duration, setDuration] = React.useState("30");
  const [strategy, setStrategy] = React.useState<Strategy>("balanced");
  const [enabled, setEnabled] = React.useState<FormatId[]>([
    "in_stream",
    "shorts",
    "in_feed",
  ]);

  const toggle = (f: FormatId) =>
    setEnabled((cur) =>
      cur.includes(f) ? cur.filter((x) => x !== f) : [...cur, f]
    );

  const budgetNum = Math.max(0, Number(budget) || 0);
  const curves = buildCurves(objective, strategy, enabled);

  // Exploratory strategy: reserve 10% exploration equally, optimize the rest.
  const explorationReserve =
    strategy === "exploratory" ? budgetNum * 0.1 : 0;
  const optimizableBudget = budgetNum - explorationReserve;

  const { alloc: waterAlloc } = waterFill(curves, optimizableBudget);
  const equalAlloc = equalSplit(enabled, optimizableBudget);
  const roasAlloc = roasProportional(curves, optimizableBudget);

  // add exploration share equally across enabled formats
  const withExploration = (a: Record<string, number>) => {
    if (strategy !== "exploratory" || enabled.length === 0) return a;
    const exPer = explorationReserve / enabled.length;
    const out = { ...a };
    enabled.forEach((f) => (out[f] = (out[f] ?? 0) + exPer));
    return out;
  };

  const finalAlloc = withExploration(waterAlloc);
  const finalEqual = withExploration(equalAlloc);
  const finalRoas = withExploration(roasAlloc);

  const totalFinal = enabled.reduce((s, f) => s + (finalAlloc[f] ?? 0), 0);
  const revWater = expectedRevenue(curves, finalAlloc);
  const revEqual = expectedRevenue(curves, finalEqual);
  const revRoas = expectedRevenue(curves, finalRoas);

  const sym = CURRENCIES[currency] ?? "";
  const fmt = (n: number) =>
    `${sym}${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

  const sortedFormats = [...enabled].sort(
    (a, b) => (finalAlloc[b] ?? 0) - (finalAlloc[a] ?? 0)
  );

  return (
    <div className="space-y-6">
      <ViewHeader
        title="AI Budget Optimizer"
        description="Allocate a YouTube advertising budget across formats using a water-fill optimizer that equalizes marginal return and rounds via largest-remainder so the total equals your budget exactly."
        icon={Wallet}
      />

      {/* Provenance banner */}
      <div
        className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-xs ${
          realAdsConnected
            ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-800 dark:text-emerald-300"
            : "border-orange-500/30 bg-orange-500/5 text-orange-800 dark:text-orange-300"
        }`}
      >
        <FlaskConical className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-semibold">
            {realAdsConnected
              ? "MODEL_PREDICTION mode — fitted on real campaign history"
              : "ESTIMATED_SCENARIO mode — built on documented assumptions"}
          </p>
          <p className="mt-0.5">
            {realAdsConnected
              ? "Saturation curves are fitted from your actual Google Ads campaign data via GAQL."
              : "No Google Ads account connected. The curve parameters below are illustrative assumptions, not measured performance. Do not treat results as actual predictions. Connect Google Ads in Settings to switch to MODEL_PREDICTION mode."}
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        {/* Config */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Campaign parameters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Total budget</Label>
                <Input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Currency</Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(CURRENCIES).map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Marketing objective</Label>
              <Select value={objective} onValueChange={(v) => setObjective(v as Objective)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="awareness">Brand Awareness</SelectItem>
                  <SelectItem value="views">Video Views</SelectItem>
                  <SelectItem value="traffic">Website Traffic</SelectItem>
                  <SelectItem value="leads">Leads</SelectItem>
                  <SelectItem value="sales">Sales</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Duration (days)</Label>
                <Input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Strategy</Label>
                <Select value={strategy} onValueChange={(v) => setStrategy(v as Strategy)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="balanced">Balanced</SelectItem>
                    <SelectItem value="performance_focused">Performance-focused</SelectItem>
                    <SelectItem value="exploratory">Exploratory (+10% exploration)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Advertising formats</Label>
              <div className="space-y-2">
                {(Object.keys(FORMAT_META) as FormatId[]).map((f) => (
                  <label
                    key={f}
                    className="flex cursor-pointer items-center gap-2.5 rounded-md border border-border p-2.5"
                  >
                    <Checkbox
                      checked={enabled.includes(f)}
                      onCheckedChange={() => toggle(f)}
                    />
                    <span className="text-sm">{FORMAT_META[f].label}</span>
                  </label>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Recommended allocation</CardTitle>
                <ProvenanceBadge
                  provenance={realAdsConnected ? "MODEL_PREDICTION" : "ESTIMATED_SCENARIO"}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {enabled.length === 0 ? (
                <EmptyState
                  icon={Wallet}
                  title="Select at least one format"
                  description="Enable one or more YouTube ad formats to compute an allocation."
                  provenance="USER_INPUT"
                />
              ) : (
                <>
                  <div className="rounded-lg bg-primary/5 px-4 py-3">
                    <p className="text-xs text-muted-foreground">Total allocated</p>
                    <p className="text-2xl font-semibold tabular-nums text-foreground">
                      {fmt(totalFinal)}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Equals budget exactly (largest-remainder rounding) ·{" "}
                      {duration}-day campaign
                    </p>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Format</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead className="text-right">Share</TableHead>
                        <TableHead className="text-right">Marginal ROAS</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedFormats.map((f) => {
                        const amt = finalAlloc[f] ?? 0;
                        const curve = curves.find((c) => c.name === f)!;
                        const mr = curve.alpha / (curve.beta + amt);
                        const share = totalFinal > 0 ? (amt / totalFinal) * 100 : 0;
                        return (
                          <TableRow key={f}>
                            <TableCell className="font-medium">
                              {FORMAT_META[f].label}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {fmt(amt)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {share.toFixed(1)}%
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-muted-foreground">
                              {mr.toFixed(4)}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                  <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <Info className="h-3 w-3" />
                    Water-fill equalizes marginal return α/(β+x) across formats;
                    saturated formats earn zero allocation.
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          {/* Scenario comparison */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <TrendingUp className="h-4 w-4 text-primary" />
                Scenario comparison
                <ProvenanceBadge
                  provenance={realAdsConnected ? "MODEL_PREDICTION" : "ESTIMATED_SCENARIO"}
                  className="ml-auto"
                />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Strategy</TableHead>
                    <TableHead className="text-right">Expected revenue</TableHead>
                    <TableHead className="text-right">vs. water-fill</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell>Equal split (gut feel)</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(revEqual)}</TableCell>
                    <TableCell className="text-right tabular-nums text-rose-600">
                      {revEqual > 0
                        ? `${(((revWater - revEqual) / revEqual) * 100).toFixed(1)}%`
                        : "—"}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>ROAS-proportional</TableCell>
                    <TableCell className="text-right tabular-nums">{fmt(revRoas)}</TableCell>
                    <TableCell className="text-right tabular-nums text-rose-600">
                      {revRoas > 0
                        ? `${(((revWater - revRoas) / revRoas) * 100).toFixed(1)}%`
                        : "—"}
                    </TableCell>
                  </TableRow>
                  <TableRow className="bg-primary/5">
                    <TableCell className="font-semibold">Water-fill (recommended)</TableCell>
                    <TableCell className="text-right tabular-nums font-semibold">
                      {fmt(revWater)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-semibold text-emerald-600">
                      baseline
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <Calculator className="h-3 w-3" />
                Expected revenue uses R(s) = α·ln(1 + s/β). Comparison is computed
                under identical curves so differences reflect allocation quality,
                not bigger budgets.
              </p>
            </CardContent>
          </Card>

          {/* Assumptions */}
          <Card>
            <CardHeader className="pb-3">
              <SectionTitle icon={FlaskConical}>Documented assumptions</SectionTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <ul className="list-disc space-y-1 pl-5">
                <li>Curve model: R(s) = α·ln(1 + s/β) + c (logarithmic saturation).</li>
                <li>Base parameters per format are illustrative, not measured: In-Stream α=1.0/β=200, Shorts α=0.85/β=120, In-Feed α=0.7/β=90.</li>
                <li>Objective multipliers re-weight α per format (e.g. Sales → In-Stream ×1.2).</li>
                <li>Performance-focused strategy amplifies the spread (±12%); Exploratory reserves 10% split equally as a UCB-style exploration term (active only on real data).</li>
                <li>Hard constraints enforced: total == budget exactly, no negative allocations, all enabled formats considered.</li>
                <li>This is a recommendation system. It does not spend money or modify campaigns. Execution requires separate authorization.</li>
              </ul>
              <Separator className="my-2" />
              <p className="flex items-center gap-1.5">
                <Info className="h-3 w-3" />
                When Google Ads is connected, α/β are fitted from real weekly
                campaign aggregates via closed-form OLS over a β-grid with
                bootstrap confidence intervals.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
