# Session Continuity & Warmup

How Glee maintains context across coding sessions.

## Problem

Vibe coding breaks flow when a new session starts. Users re-explain context, re-open the same files, and re-justify decisions. Glee owns the "session continuity" wedge: resume a project in under 30 seconds with the right context.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SESSION LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Session Start                          Session End              │
│  ─────────────                          ───────────              │
│  SessionStart hook                      Stop hook                │
│         │                                    │                   │
│         ▼                                    ▼                   │
│  ┌──────────────┐                    ┌───────────────┐          │
│  │ glee warmup  │                    │ glee          │          │
│  │              │                    │ summarize-    │          │
│  │ Reads:       │                    │ session       │          │
│  │ - goal       │                    │               │          │
│  │ - constraints│                    │ Writes:       │          │
│  │ - decisions  │                    │ - summary     │          │
│  │ - open_loops │                    │ - git_base    │          │
│  │ - changes    │                    │ - changes     │          │
│  │ - sessions   │                    │               │          │
│  └──────┬───────┘                    └───────┬───────┘          │
│         │                                    │                   │
│         ▼                                    ▼                   │
│  ┌──────────────────────────────────────────────────────────────┐
│  │                  .glee/memory.*                               │
│  │  (LanceDB vectors + DuckDB structured)                       │
│  └──────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

## Memory Categories

Glee uses reserved memory categories for session continuity:

| Category | Clear on Write? | Max Items | Purpose |
|----------|-----------------|-----------|---------|
| `goal` | Yes | 1 | Current objective |
| `constraint` | Yes | 5 | Key constraints to remember |
| `decision` | No (append) | 5 | Decisions made |
| `open_loop` | Yes | 5 | Unfinished tasks |
| `recent_change` | Yes | 20 | File changes since last session |
| `session_summary` | No (append) | 1 | Session end summary |

### Clear vs Append

- **Clear first** (`goal`, `constraint`, `open_loop`, `recent_change`): These represent "current state" — old values are replaced.
- **Append** (`decision`, `session_summary`): These are historical — we want to accumulate them.

## Git-Aware Change Tracking

Glee tracks what changed between sessions using git:

```
Session N ends:
  1. Get current HEAD → store as git_base in session_summary metadata
  2. Calculate changes since previous git_base → store as recent_change

Session N+1 starts (warmup):
  1. Read git_base from latest session_summary metadata
  2. Run: git diff --name-status {git_base}..HEAD
  3. Show "Changes Since Last Session"
```

This means warmup shows *actual* code changes since the last session, not just uncommitted changes.

## Data Flow

### Capture (`capture_memory`)

Called by:
- `glee_memory_capture` MCP tool (explicit)
- `glee_task` after agent completes (automatic, from `<glee_memory_capture>` block)
- `glee summarize-session` CLI command

```python
capture_memory(project_path, {
    "goal": "Implement session continuity",
    "constraints": ["No cloud dependencies", "Must be fast"],
    "decisions": ["Use LanceDB for vectors"],
    "open_loops": ["Hook registration not implemented"],
    "recent_changes": ["M glee/warmup.py", "A glee/helpers.py"],
    "summary": "Added warmup and capture modules",
    "git_base": "abc123..."  # Current HEAD
})
```

### Warmup (`build_warmup_text`)

Called by:
- `glee warmup` CLI command
- `glee_warmup` MCP tool
- `UserPromptSubmit` hook (planned)

Output format:

```markdown
# Glee Warmup

## Last Session
- task-abc123 (completed, 2025-01-10 14:30): Implement warmup module

## Current Goal
Implement session continuity for vibe coding

## Key Constraints
- No cloud dependencies
- Must be fast (<30s warmup)

## Recent Decisions
- Use LanceDB for vectors
- Store git_base in metadata

## Changes Since Last Session
- M glee/warmup.py
- A glee/helpers.py
- M glee/mcp_server.py

## Open Loops
- Hook registration not implemented
- Need to add TTL for decisions

## Memory
### Architecture
- CLI built with Typer, MCP server with mcp.server
### Convention
- Use snake_case for Python, type hints required
```

## Hook Integration

### Claude Code

```json
// .claude/settings.json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "",
      "hooks": [{ "type": "command", "command": "glee warmup" }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{ "type": "command", "command": "glee summarize-session" }]
    }]
  }
}
```

### Other Agents

See [coding-agent-hooks.md](./coding-agent-hooks.md) for hook configuration for Cursor, Gemini CLI, Codex, etc.

## MCP Tools

| Tool | Purpose |
|------|---------|
| `glee_warmup` | Return warmup context (injected at session start) |
| `glee_summarize_session` | Capture session summary (called at session end) |
| `glee_memory_capture` | Explicitly capture structured memory |
| `glee_memory_add` | Add a memory entry to a category |
| `glee_memory_list` | List memories, optionally filtered by category |
| `glee_memory_delete` | Delete memory by ID or category |

## CLI Commands

```bash
# Output warmup context to stdout
glee warmup

# Capture session summary
glee summarize-session
glee summarize-session --summary "Finished auth module"

# Capture structured memory from JSON
glee memory capture --json '{"goal": "Build auth", "constraints": ["Use JWT"]}'
glee memory capture --file context.json
```

## Success Metrics

- Time-to-first-action <30s after session start
- Fewer repeated explanations (qualitative)
- Users can resume mid-task without re-explaining context
