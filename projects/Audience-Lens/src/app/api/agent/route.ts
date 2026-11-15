import { NextRequest, NextResponse } from "next/server";
import ZAI from "z-ai-web-dev-sdk";
import { SYSTEM_PROMPT } from "@/lib/agent-prompt";

// The agent loop runs server-side. It calls the Python backend directly on
// localhost:8000 (no Caddy/gateway needed for server-to-server). The LLM never
// touches the DB or external APIs directly — it only emits structured tool
// calls that this route validates and executes against the backend.

export const runtime = "nodejs";
export const maxDuration = 60;

const BACKEND = "http://localhost:8000";

interface InMessage {
  role: "user" | "assistant";
  content: string;
}

interface ToolRun {
  name: string;
  summary: string;
  args?: { texts?: string[]; meta?: Record<string, string> };
}

// ---------------------------------------------------------------------------
// LLM call
// ---------------------------------------------------------------------------

async function llm(messages: { role: "system" | "user" | "assistant"; content: string }[]): Promise<string> {
  const zai = await ZAI.create();
  const res = await zai.chat.completions.create({
    model: "glm-4.6",
    messages,
    stream: false,
    thinking: { type: "disabled" },
  });
  return res?.choices?.[0]?.message?.content ?? res?.content ?? "";
}

// ---------------------------------------------------------------------------
// Tool execution — each returns { feed } for the LLM and { summary } for the UI
// ---------------------------------------------------------------------------

async function postBackend(path: string, body: unknown): Promise<any> {
  const res = await fetch(`${BACKEND}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail || data?.error || `backend ${res.status}`);
  }
  return data;
}

const TOOLS: Record<string, (args: any) => Promise<{ feed: string; summary: string }>> = {
  analyze_sentiment: async (args) => {
    const texts: string[] = Array.isArray(args?.texts) ? args.texts.filter((t: unknown) => typeof t === "string" && t.trim()) : [];
    if (texts.length === 0) return { feed: "ERROR: no texts provided.", summary: "analyze_sentiment — no texts" };
    const r = await postBackend("/api/v1/nlp/analyze-batch", { texts, aspect_catalog: args.catalog || "general" });
    const samples = r.results.slice(0, 6).map((x: any) => `  - [${x.sentiment} ${x.score}] "${x.text.slice(0, 90)}"`).join("\n");
    const feed = `Sentiment analysis of ${r.count} comments.
Distribution: ${JSON.stringify(r.distribution_pct)}.
Avg score: ${r.avg_score}. Languages: ${JSON.stringify(r.language_distribution)}.
Top topics: ${r.topics.slice(0, 6).map((t: any) => `${t.topic}(${t.count})`).join(", ")}.
Sample classified comments:
${samples}`;
    const summary = `Analyzed ${r.count} comments → ${r.distribution_pct.positive}% positive, ${r.distribution_pct.negative}% negative, ${r.distribution_pct.mixed}% mixed; avg ${r.avg_score}`;
    return { feed, summary };
  },

  cluster_comments: async (args) => {
    const texts: string[] = Array.isArray(args?.texts) ? args.texts.filter((t: unknown) => typeof t === "string" && t.trim()) : [];
    if (texts.length < 3) return { feed: "ERROR: need at least 3 texts to cluster.", summary: "cluster_comments — too few texts" };
    const r = await postBackend("/api/v1/audience/cluster", { texts, method: args.method || "kmeans" });
    if (r.error) return { feed: `Clustering error: ${r.error}`, summary: "cluster_comments — error" };
    const segs = r.clusters.slice(0, 6).map((c: any) => `  - ${c.label}: ${c.size} comments (${c.share}%), avg score ${c.avg_sentiment_score}, terms: ${c.top_terms.slice(0, 4).join(", ")}`).join("\n");
    const feed = `Clustering via ${r.method}. ${r.n_clusters} clusters from ${r.n_comments} comments. Silhouette: ${r.silhouette}.
Segments:
${segs}`;
    const summary = `${r.n_clusters} segments from ${r.n_comments} comments (${r.method}); silhouette ${r.silhouette}`;
    return { feed, summary };
  },

  generate_findings: async (args) => {
    const texts: string[] = Array.isArray(args?.texts) ? args.texts.filter((t: unknown) => typeof t === "string" && t.trim()) : [];
    if (texts.length < 3) return { feed: "ERROR: need at least 3 texts to generate findings.", summary: "generate_findings — too few texts" };
    const r = await postBackend("/api/v1/findings/generate", { texts, aspect_catalog: args.catalog || "general", cluster_method: args.method || "kmeans" });
    const cards = r.findings.map((f: any) => `  [${f.id}] ${f.title} (${f.provenance}, conf ${f.confidence}): ${f.description.slice(0, 160)} Action: ${f.recommended_action.slice(0, 120)}`).join("\n");
    const feed = `Findings engine produced ${r.n_findings} cards from ${r.n_comments} comments. Sentiment: ${JSON.stringify(r.sentiment_distribution)}.
Cards:
${cards}`;
    const summary = `${r.n_findings} findings from ${r.n_comments} comments`;
    return { feed, summary };
  },

  youtube_research: async (args) => {
    if (!args?.query || typeof args.query !== "string") return { feed: "ERROR: query required.", summary: "youtube_research — no query" };
    const r = await postBackend("/api/v1/youtube/research", {
      query: args.query,
      country: args.country || "",
      max_videos: Number(args.max_videos) || 5,
      comments_per_video: Number(args.comments_per_video) || 40,
      aspect_catalog: args.catalog || "general",
    });
    if (r.n_comments > 0) {
      const feed = `YouTube research for "${r.query}". Collected ${r.n_videos} videos, ${r.n_comments} comments.
Sentiment: ${JSON.stringify(r.sentiment.distribution_pct)}. Avg: ${r.sentiment.avg_score}.
Top topics: ${r.sentiment.topics.slice(0, 6).map((t: any) => `${t.topic}(${t.count})`).join(", ")}.
Videos: ${r.videos.slice(0, 5).map((v: any) => `${v.title} (${v.comment_count} comments)`).join(" | ")}.`;
      const summary = `YouTube: ${r.n_videos} videos, ${r.n_comments} comments → ${r.sentiment.distribution_pct.positive}% positive / ${r.sentiment.distribution_pct.negative}% negative`;
      return { feed, summary };
    }
    return { feed: `YouTube research for "${r.query}": collected ${r.n_videos} videos but 0 comments (comments may be disabled). Try a different query or more videos.`, summary: `YouTube: ${r.n_videos} videos, 0 comments` };
  },

  generate_report: async (args) => {
    const texts: string[] = Array.isArray(args?.texts) ? args.texts.filter((t: unknown) => typeof t === "string" && t.trim()) : [];
    if (texts.length < 3) return { feed: "ERROR: need at least 3 texts to generate a report.", summary: "generate_report — too few texts" };
    const meta = (args.meta && typeof args.meta === "object" ? args.meta : {}) as Record<string, string>;
    const r = await postBackend("/api/v1/reports/generate", {
      texts,
      meta,
      aspect_catalog: args.catalog || "general",
      cluster_method: args.method || "kmeans",
    });
    if (r.error) return { feed: `Report error: ${r.error}`, summary: "generate_report — error" };
    const sectionList = r.sections.map((s: any) => `  - ${s.title} [${s.provenance}]`).join("\n");
    const feed = `Report generated: ${r.sections.length} sections from ${r.n_comments} comments.
Title: ${r.meta?.title || "Report"}.
Sections:
${sectionList}
The user can download this report as PDF or DOCX from the chat card below.`;
    const summary = `Report: ${r.sections.length} sections from ${r.n_comments} comments — download available`;
    return { feed, summary, args: { texts, meta } };
  },
};

// ---------------------------------------------------------------------------
// Tool-call parsing — robust to the LLM omitting the ```tool fence
// ---------------------------------------------------------------------------

const TOOL_RE = /```tool\s*([\s\S]*?)```/i;
const KNOWN_TOOLS = ["analyze_sentiment", "cluster_comments", "generate_findings", "youtube_research", "generate_report"];

/** Extract the first balanced JSON object from text (handles nested braces/strings). */
function extractFirstJsonObject(text: string): { raw: string; start: number } | null {
  const start = text.indexOf("{");
  if (start === -1) return null;
  let depth = 0, inStr = false, esc = false;
  for (let i = start; i < text.length; i++) {
    const ch = text[i];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === "\\") esc = true;
      else if (ch === '"') inStr = false;
    } else {
      if (ch === '"') inStr = true;
      else if (ch === "{") depth++;
      else if (ch === "}") {
        depth--;
        if (depth === 0) return { raw: text.slice(start, i + 1), start };
      }
    }
  }
  return null;
}

function parseToolCall(content: string): { name: string; args: any; raw: string } | null {
  // 1) Preferred: fenced ```tool block
  const fence = TOOL_RE.exec(content);
  if (fence) {
    try {
      const parsed = JSON.parse(fence[1]);
      if (parsed && typeof parsed.name === "string") {
        return { name: parsed.name, args: parsed.args || {}, raw: fence[0] };
      }
    } catch {
      /* fall through */
    }
  }
  // 2) Fallback: raw JSON object containing a known tool name (LLM omitted fence)
  if (KNOWN_TOOLS.some((t) => content.includes(t))) {
    const obj = extractFirstJsonObject(content);
    if (obj) {
      try {
        const parsed = JSON.parse(obj.raw);
        if (parsed && typeof parsed.name === "string" && KNOWN_TOOLS.includes(parsed.name)) {
          return { name: parsed.name, args: parsed.args || {}, raw: obj.raw };
        }
      } catch {
        /* ignore */
      }
    }
  }
  return null;
}

/** Strip both fenced and raw-JSON tool calls from text (used for final answers). */
function stripToolCalls(text: string): string {
  let out = text.replace(TOOL_RE, "");
  while (true) {
    const obj = extractFirstJsonObject(out);
    if (!obj) break;
    try {
      const parsed = JSON.parse(obj.raw);
      if (parsed && typeof parsed.name === "string" && KNOWN_TOOLS.includes(parsed.name)) {
        out = out.replace(obj.raw, "");
        continue;
      }
    } catch {
      /* ignore */
    }
    break;
  }
  return out.trim();
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => null);
    const incoming: InMessage[] = Array.isArray(body?.messages) ? body.messages : [];
    const safe = incoming
      .filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
      .slice(-20)
      .map((m) => ({ role: m.role, content: m.content }));

    if (safe.length === 0) {
      return NextResponse.json({ error: "No conversation history provided." }, { status: 400 });
    }

    const convo: { role: "system" | "user" | "assistant"; content: string }[] = [
      { role: "system", content: SYSTEM_PROMPT },
      ...safe,
    ];
    const tool_runs: ToolRun[] = [];
    const MAX_ITERS = 3;
    let toolCallCount = 0;
    let lastToolFeed = "";
    let lastToolName = "";
    let finalContent = "";

    for (let i = 0; i < MAX_ITERS; i++) {
      const content = await llm(convo);
      const call = parseToolCall(content);

      // No tool call → this is the final answer.
      if (!call) {
        finalContent = content;
        break;
      }

      // We allow at most ONE tool execution per user turn. If the LLM emits
      // another tool call after that, force a grounded summary instead.
      if (toolCallCount >= 1) {
        const preamble = content.replace(call.raw, "").trim();
        if (preamble) convo.push({ role: "assistant", content: preamble });
        finalContent = await llm([
          ...convo,
          {
            role: "system",
            content:
              "You already have tool results above. Write the final grounded answer for the user NOW. " +
              "DO NOT emit any tool block. Summarize the findings in 3-6 sentences, quoting the actual numbers " +
              "from the tool results (percentages, segment names, complaint/praise topics).",
          },
        ]);
        finalContent = stripToolCalls(finalContent);
        break;
      }

      // Execute the (first) tool call.
      const tool = TOOLS[call.name];
      const preamble = content.replace(call.raw, "").trim();
      if (preamble) convo.push({ role: "assistant", content: preamble });

      if (!tool) {
        convo.push({
          role: "system",
          content: `Tool "${call.name}" is not available. Available tools: ${Object.keys(TOOLS).join(", ")}. Answer the user directly without any tool call.`,
        });
        continue;
      }

      try {
        const result = await tool(call.args);
        tool_runs.push({ name: call.name, summary: result.summary, ...(result.args ? { args: result.args } : {}) });
        lastToolFeed = result.feed;
        lastToolName = call.name;
        convo.push({
          role: "system",
          content:
            `TOOL RESULT (${call.name}):\n${result.feed.slice(0, 3500)}\n\n` +
            "You have used your one tool call for this turn. Now write the final grounded answer for the user. " +
            "DO NOT emit another tool block. Summarize in 3-6 sentences with the actual numbers above.",
        });
        toolCallCount += 1;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "tool execution failed";
        tool_runs.push({ name: call.name, summary: `${call.name} — failed: ${msg.slice(0, 80)}` });
        convo.push({
          role: "system",
          content: `TOOL ERROR (${call.name}): ${msg}\nTell the user honestly that the tool failed and why. Do not call another tool.`,
        });
        toolCallCount += 1;
      }
      finalContent = "";
    }

    // Safety net: if we exited the loop without a final answer, force one and
    // strip any stray tool fence.
    if (!finalContent) {
      finalContent = await llm([
        ...convo,
        {
          role: "system",
          content:
            "Write the final grounded answer now using the tool results above. " +
            "DO NOT emit any tool block. Summarize with real numbers.",
        },
      ]);
      finalContent = stripToolCalls(finalContent);
    }

    // If the LLM still refused to summarize (emitted tool-only content),
    // synthesize a grounded answer directly from the tool result so the user
    // always gets real data — never an empty response.
    if (!finalContent && lastToolFeed) {
      finalContent =
        `Based on the ${lastToolName.replace(/_/g, " ")} I just ran on the backend, here is what the real data shows:\n\n` +
        lastToolFeed.slice(0, 2500);
    }

    if (!finalContent) {
      return NextResponse.json({ error: "The agent returned an empty response." }, { status: 502 });
    }

    // Embed the tool-run summary as a fenced block the client can render.
    let contentOut = finalContent;
    if (tool_runs.length > 0) {
      const toolsBlock = "```tools\n" + JSON.stringify(tool_runs) + "\n```";
      contentOut = finalContent.trimEnd() + "\n\n" + toolsBlock;
    }

    return NextResponse.json({ content: contentOut });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown agent error.";
    return NextResponse.json({ error: `Agent backend unavailable: ${message}` }, { status: 500 });
  }
}
