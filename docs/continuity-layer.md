# Glee Session Continuity & Warmup (Spec)

## Why This Exists

Vibe coding breaks flow when a new session starts. Users re-explain context, re-open the same files, and re-justify decisions. Glee should own the "session continuity" wedge: resume a project in under 30 seconds with the right context and next steps.

## Goals

- Make new sessions productive in <30s.
- Eliminate repeated context re-explanations.
- Keep it local-first, fast, and MCP-friendly.
- Require minimal manual input.

## Non-Goals

- Replace full code review workflows.
- Build a cloud service or external index.
- Maintain infinite context (focus on recency + relevance).

## Core Concepts

- **Project Brief**: A concise "what we are building" statement.
- **Decisions**: Durable choices and rationale (frameworks, architecture, constraints).
- **Preferences**: Conventions, style, and "do/don't" rules.
- **Open Loops**: Unfinished tasks, blockers, or TODOs.
- **Recent Changes**: What changed since last session (git-aware).

## Primary Flow (User)

1. Start a new session.
2. Run `glee_warmup` (or it runs automatically via Claude Code hook).
3. Get a short, structured summary + next 3 actions.
4. Ask for deeper context only if needed (`glee_context_pack`).

## MCP + CLI Surface

### 1) `glee_warmup` (new)

Fast, single-shot continuity summary.

**Inputs**

- `focus` (optional): short task or question to bias relevance.
- `max_actions` (optional, default 3)
- `since` (optional): "last_session" | "24h" | "7d"

**Output (structured text)**

- Current goal
- Recent decisions (top 3)
- Open loops (top 5)
- Recent changes (files + 1-line summary)
- Next actions (top 3)

### 2) `glee_context_pack` (new)

On-demand, deeper context pack. Returns curated snippets only (no full tree).

**Inputs**

- `focus` (required): task description
- `max_files` (optional, default 6)
- `max_chars` (optional, default 6000)

**Output**

- Project brief
- Relevant memory snippets
- File excerpts for top-N relevant files
- Notes on where to look next

### 3) `glee_spotcheck` (new name for fast review)

A quick confidence check. Top 3 high-risk issues only. Targeted for vibe coding.

**Inputs**

- `target` (optional): default `git:changes`
- `limit` (optional, default 3)

**Output**

- Top risks with severity and 1-line rationale
- Optional "ignore if intentional" notes

## Data Sources (MVP, local only)

- `.glee/memory.*` (existing memory store)
- `.glee/sessions/*.json` (existing task sessions)
- `git status` / `git diff --name-only`
- `README.md`, `CLAUDE.md`, `AGENTS.md`

## Data Model (Additive)

Use the existing memory store with richer categories + metadata.

**New categories**

- `brief` (1 entry)
- `decision`
- `preference`
- `open_loop`
- `recent_change`
- `session_summary`

**Metadata examples**

```json
{
  "source": "session",
  "session_id": "task-1a2b3c4d",
  "files": ["src/api/auth.py", "src/db/models.py"],
  "timestamp": "2025-01-10T12:34:56Z"
}
```

## Heuristics (Keep It Fast)

- Prefer recency: last session + git changes.
- Prefer relevance: memory search on `focus` if provided.
- Cap output size aggressively (hard limit).
- Avoid LLM summarization unless user asks.

## Suggested Hooks

- On session start: auto-run `glee_warmup`.
- On task completion: create a `session_summary` memory entry.
- On git commit: add `recent_change` memory entry (best-effort).

## Implementation Phases

**Phase 0 (MVP, no new deps)**

- Add `glee_warmup` + `glee_context_pack` MCP tools.
- Add a lightweight summary builder (memory + git).
- Add `glee_spotcheck` tool name (alias of review with stricter limits).

**Phase 1**

- Auto-session summaries into memory.
- Decision/preference capture helper (`glee_memory_add` templates).

**Phase 2**

- Relevance ranking using semantic search + git diff weighting.
- Background indexing and cache.

## Success Metrics

- Time-to-first-action <30s after session start.
- Fewer repeated explanations (qualitative).
- Higher retention for users doing >3 sessions/week.

## Open Questions

- Should `glee_warmup` run automatically for all MCP clients or only Claude Code?
- Do we want "resume" to be opinionated (suggest next steps), or purely factual?
- Where should open loops be captured (manual vs inferred)?

## What’s harder to copy (and where Glee wins):

- A persistent, agent‑agnostic memory store with stable project IDs (survives renames, works across Claude/Codex/Gemini).
- Automatic session summaries and open‑loop tracking written after tasks complete (not at session start).
- Diff‑aware context: “what changed since last session,” “what broke last time,” “what’s still unresolved.”
- A context pack that’s relevant to the current focus, not just a dump.
