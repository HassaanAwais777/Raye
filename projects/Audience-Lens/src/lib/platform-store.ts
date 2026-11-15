"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  ChatConversation,
  ChatMessage,
  Connection,
  Provenance,
  ResearchPlan,
  ViewId,
} from "./types";

// ---------------------------------------------------------------------------
// Phase-1 note: chat history and plans are persisted to localStorage only as a
// UX stand-in. In Phase 2 these move to Neon PostgreSQL via the FastAPI backend.
// API keys are NEVER stored here — only connection *status*.
// ---------------------------------------------------------------------------

interface PlatformState {
  activeView: ViewId;
  setView: (v: ViewId) => void;

  conversations: ChatConversation[];
  currentConversationId: string | null;
  createConversation: () => string;
  setCurrentConversation: (id: string) => void;
  addMessage: (conversationId: string, msg: ChatMessage) => void;
  updateLastAssistant: (conversationId: string, content: string) => void;

  plans: ResearchPlan[];
  upsertPlan: (plan: ResearchPlan) => void;
  approvePlan: (id: string) => void;

  connections: Connection[];
  setConnection: (id: Connection["id"], patch: Partial<Connection>) => void;

  /** Whether the agent is currently calling the LLM. */
  agentBusy: boolean;
  setAgentBusy: (b: boolean) => void;
}

const uid = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);

const DEFAULT_CONNECTIONS: Connection[] = [
  {
    id: "youtube",
    label: "YouTube Data API v3",
    status: "disconnected",
    detail: "No API key configured. Live collection unavailable.",
    quotaUsed: 0,
    quotaTotal: 10000,
  },
  {
    id: "googleAds",
    label: "Google Ads API",
    status: "disconnected",
    detail: "Not authorized. Campaign performance unavailable; optimizer runs in ESTIMATED_SCENARIO mode.",
  },
  {
    id: "llm",
    label: "Research Agent LLM",
    status: "connected",
    detail: "Agent backend available.",
  },
  {
    id: "database",
    label: "Neon PostgreSQL",
    status: "disconnected",
    detail: "Backend persistence not yet provisioned. Chat history is session-local.",
  },
];

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "I'm your **YouTube Audience & Campaign Intelligence** research agent. Tell me about your business, product, or research objective — what you want to learn, which market, and which competitors — and I'll propose a structured research plan you can review and approve before any data is collected.\n\n*Everything I recommend is grounded in real, authorized data. I never fabricate metrics or substitute synthetic data.*",
  createdAt: new Date().toISOString(),
  meta: { kind: "guidance" },
};

const FIRST_CONVO: ChatConversation = {
  id: "seed",
  title: "New research session",
  messages: [WELCOME],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export const usePlatform = create<PlatformState>()(
  persist(
    (set, get) => ({
      activeView: "agent",
      setView: (v) => set({ activeView: v }),

      conversations: [FIRST_CONVO],
      currentConversationId: "seed",
      createConversation: () => {
        const id = uid();
        const convo: ChatConversation = {
          id,
          title: "New research session",
          messages: [
            {
              ...WELCOME,
              id: "welcome-" + id,
              createdAt: new Date().toISOString(),
            },
          ],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        set((s) => ({
          conversations: [convo, ...s.conversations],
          currentConversationId: id,
        }));
        return id;
      },
      setCurrentConversation: (id) => set({ currentConversationId: id }),
      addMessage: (conversationId, msg) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: [...c.messages, msg],
                  updatedAt: new Date().toISOString(),
                  title:
                    c.messages.length <= 1 && msg.role === "user"
                      ? msg.content.slice(0, 48)
                      : c.title,
                }
              : c
          ),
        })),
      updateLastAssistant: (conversationId, content) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: c.messages.map((m, i, arr) =>
                    i === arr.length - 1 && m.role === "assistant"
                      ? { ...m, content }
                      : m
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : c
          ),
        })),

      plans: [],
      upsertPlan: (plan) =>
        set((s) => {
          const exists = s.plans.some((p) => p.id === plan.id);
          return {
            plans: exists
              ? s.plans.map((p) => (p.id === plan.id ? plan : p))
              : [plan, ...s.plans],
          };
        }),
      approvePlan: (id) =>
        set((s) => ({
          plans: s.plans.map((p) =>
            p.id === id ? { ...p, status: "approved" as const } : p
          ),
        })),

      connections: DEFAULT_CONNECTIONS,
      setConnection: (id, patch) =>
        set((s) => ({
          connections: s.connections.map((c) =>
            c.id === id ? { ...c, ...patch } : c
          ),
        })),

      agentBusy: false,
      setAgentBusy: (b) => set({ agentBusy: b }),
    }),
    {
      name: "audiencelens-v1",
      // Only persist durable, non-secret state.
      partialize: (s) => ({
        conversations: s.conversations,
        currentConversationId: s.currentConversationId,
        plans: s.plans,
        connections: s.connections,
      }),
    }
  )
);

/** Convenience selector for the active conversation. */
export function useCurrentConversation(): ChatConversation | undefined {
  return usePlatform((s) =>
    s.conversations.find((c) => c.id === s.currentConversationId)
  );
}

export { uid };
export type { Provenance, ResearchPlan, ViewId };
