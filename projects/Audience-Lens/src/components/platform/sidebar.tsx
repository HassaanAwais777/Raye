"use client";

import * as React from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { usePlatform } from "@/lib/platform-store";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ConnectionPill } from "./primitives";
import type { ViewId } from "@/lib/types";
import {
  Bot,
  LayoutDashboard,
  ClipboardList,
  Youtube,
  History,
  Smile,
  Users,
  GitFork,
  Activity,
  Swords,
  Megaphone,
  Wallet,
  Lightbulb,
  FileText,
  Settings,
  Sun,
  Moon,
  Menu,
  Database,
  Plug,
  Youtube as YoutubeIcon,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  id: ViewId;
  label: string;
  icon: LucideIcon;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

function Dot({
  status,
}: {
  status: "connected" | "disconnected" | "error" | "unknown";
}) {
  return (
    <span
      className={cn(
        "h-1.5 w-1.5 rounded-full",
        status === "connected" && "bg-emerald-500",
        status === "disconnected" && "bg-slate-400",
        status === "error" && "bg-rose-500",
        status === "unknown" && "bg-amber-500"
      )}
    />
  );
}

const NAV: NavGroup[] = [
  {
    title: "Agent",
    items: [{ id: "agent", label: "Research Agent", icon: Bot }],
  },
  {
    title: "Research",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "research-planning", label: "Research Planning", icon: ClipboardList },
      { id: "live-youtube", label: "Live YouTube", icon: Youtube },
      { id: "history", label: "Research History", icon: History },
    ],
  },
  {
    title: "Audience",
    items: [
      { id: "sentiment", label: "Sentiment", icon: Smile },
      { id: "audience", label: "Audience Intelligence", icon: Users },
      { id: "clustering", label: "Clustering", icon: GitFork },
      { id: "anomaly", label: "Anomaly Detection", icon: Activity },
    ],
  },
  {
    title: "Market",
    items: [
      { id: "competitor", label: "Competitor", icon: Swords },
      { id: "campaign", label: "Campaign Intelligence", icon: Megaphone },
    ],
  },
  {
    title: "Plan",
    items: [
      { id: "optimizer", label: "Budget Optimizer", icon: Wallet },
      { id: "findings", label: "Findings", icon: Lightbulb },
      { id: "reports", label: "Reports", icon: FileText },
    ],
  },
  {
    title: "System",
    items: [{ id: "settings", label: "Settings & Integrations", icon: Settings }],
  },
];

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  if (!mounted)
    return (
      <Button variant="ghost" size="icon" className="h-8 w-8">
        <Sun className="h-4 w-4" />
      </Button>
    );
  const isDark = theme === "dark";
  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}

function ConnectionSummary() {
  const connections = usePlatform((s) => s.connections);
  const yt = connections.find((c) => c.id === "youtube");
  const ads = connections.find((c) => c.id === "googleAds");
  const db = connections.find((c) => c.id === "database");
  return (
    <div className="flex items-center gap-3 rounded-md border border-border bg-muted/30 px-2.5 py-1.5 text-[10px] text-muted-foreground">
      <span className="flex items-center gap-1" title={yt?.label}>
        <YoutubeIcon className="h-3 w-3" />
        <Dot status={yt?.status ?? "unknown"} />
      </span>
      <span className="flex items-center gap-1" title={ads?.label}>
        <Megaphone className="h-3 w-3" />
        <Dot status={ads?.status ?? "unknown"} />
      </span>
      <span className="flex items-center gap-1" title={db?.label}>
        <Database className="h-3 w-3" />
        <Dot status={db?.status ?? "unknown"} />
      </span>
    </div>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const activeView = usePlatform((s) => s.activeView);
  const setView = usePlatform((s) => s.setView);
  return (
    <nav className="flex flex-col gap-5 px-3 py-4">
      {NAV.map((group) => (
        <div key={group.title} className="space-y-1">
          <p className="px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            {group.title}
          </p>
          {group.items.map((item) => {
            const Icon = item.icon;
            const active = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setView(item.id);
                  onNavigate?.();
                }}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                aria-current={active ? "page" : undefined}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

function BrandHeader() {
  return (
    <div className="flex items-center gap-2.5 px-4 py-4">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Bot className="h-4.5 w-4.5" />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold text-foreground">AudienceLens</p>
        <p className="text-[10px] text-muted-foreground">
          YouTube Intelligence
        </p>
      </div>
    </div>
  );
}

function SidebarFooter() {
  return (
    <div className="flex items-center justify-between gap-2 border-t border-border px-3 py-3">
      <ConnectionSummary />
      <ThemeToggle />
    </div>
  );
}

export function AppSidebar() {
  const [open, setOpen] = React.useState(false);

  return (
    <>
      {/* Desktop */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-sidebar lg:flex">
        <BrandHeader />
        <ScrollArea className="flex-1 scroll-thin">
          <NavList />
        </ScrollArea>
        <SidebarFooter />
      </aside>

      {/* Mobile drawer */}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="fixed left-3 top-3 z-40 h-9 w-9 lg:hidden"
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-72 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="flex h-full flex-col">
            <BrandHeader />
            <ScrollArea className="flex-1 scroll-thin">
              <NavList onNavigate={() => setOpen(false)} />
            </ScrollArea>
            <SidebarFooter />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
