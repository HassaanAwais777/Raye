// ============================================================================
// AudienceLens — shared platform types
// YouTube Audience & Campaign Intelligence Platform
// ============================================================================

/** Mandatory data-provenance labels. Every insight, metric, or dataset row
 *  that surfaces in the UI must carry one of these so the user always knows
 *  what kind of data they are looking at. */
export type Provenance =
  | "LIVE_DATA" // collected from an authorized live API (YouTube Data API v3 / Google Ads API)
  | "MODEL_PREDICTION" // output of a trained ML / NLP model
  | "ESTIMATED_SCENARIO" // planner estimate built on documented assumptions, not measured
  | "INFERENCE" // derived analytical inference (e.g. cluster label, anomaly flag)
  | "USER_INPUT" // value the user supplied
  | "INSUFFICIENT_DATA"; // not enough real data to make a claim

/** The single-page app is driven by a view switcher (Zustand activeView).
 *  These map 1:1 to the platform's modules. */
export type ViewId =
  | "agent"
  | "dashboard"
  | "research-planning"
  | "live-youtube"
  | "sentiment"
  | "audience"
  | "clustering"
  | "anomaly"
  | "competitor"
  | "campaign"
  | "optimizer"
  | "findings"
  | "history"
  | "reports"
  | "settings";

// ---------------------------------------------------------------------------
// Module 1 — AI Research Agent
// ---------------------------------------------------------------------------

export type ChatRole = "system" | "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string; // ISO
  /** Optional structured artifact the assistant attached (e.g. a research plan). */
  artifact?: ResearchPlan;
  /** Flag messages that are auto-generated system guidance. */
  meta?: { kind?: "guidance" | "plan-proposed" | "plan-approved" };
}

export interface ChatConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

// ---------------------------------------------------------------------------
// Research plan (produced by the agent, edited by the user, approved before run)
// ---------------------------------------------------------------------------

export interface ResearchPlan {
  id: string;
  objective: string;
  businessContext: string;
  country: string;
  industry: string;
  niche: string;
  competitors: string[];
  keywords: string[];
  channels: string[]; // YouTube channel URLs / IDs / handles
  dateRange: { start: string; end: string };
  modules: ViewId[]; // which analytical modules to run
  sampleSizeTarget: number;
  languageScope: string[];
  notes: string;
  status: "draft" | "proposed" | "approved" | "running" | "completed";
  provenance: Provenance; // always USER_INPUT until results land
}

// ---------------------------------------------------------------------------
// Connections (Settings) — tracked client-side; real validation happens backend
// ---------------------------------------------------------------------------

export type ConnectionStatus = "connected" | "disconnected" | "error" | "unknown";

export interface Connection {
  id: "youtube" | "googleAds" | "llm" | "database";
  label: string;
  status: ConnectionStatus;
  detail: string;
  /** Quota usage where applicable (YouTube Data API units). */
  quotaUsed?: number;
  quotaTotal?: number;
}

// ---------------------------------------------------------------------------
// Generic insight row (used by Findings, Anomaly, Audience, etc.)
// ---------------------------------------------------------------------------

export interface InsightRow {
  id: string;
  title: string;
  description: string;
  provenance: Provenance;
  /** Supporting evidence references (video ids, comment ids, metric values). */
  evidence: { label: string; value: string }[];
  recommendedAction?: string;
  confidence?: number; // 0..1 when applicable
  collectedPeriod?: string;
  methodology?: string;
}
