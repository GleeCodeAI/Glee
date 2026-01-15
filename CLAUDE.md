# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Rules

- **MUST NOT** change `version` in `pyproject.toml` - the user manages version bumps manually
- **MUST** run `uv sync` after modifying dependencies in `pyproject.toml`
- **MUST** test CLI commands with `uv run glee <command>` during development
- **SHOULD** update docs (README.md, CLAUDE.md, docs/) when adding new features
- **MUST NOT** add MCP servers to global `~/.claude/settings.json`
- **MUST** use project-local `.mcp.json` when editing mcp server configuration for claude code
- **MUST** always fix ide warnings and errors

## Project Overview

**Glee MCP Agent Runtime** is a locally-running autonomous agent exposed to LLM tools through MCP.

> **Delegate work. Save context.**

It allows Claude Code, Codex, Cursor, etc. to **delegate complex, long-running work to Glee** instead of executing it in their own context. This saves context window and enables parallel work.

## Core Concept

```
Claude Code (limited context)
    ↓ glee_job.submit("refactor auth system")
Glee Agent Runtime (separate context)
    ↓ Uses Codex/Claude API internally
    ↓ Runs autonomously with ReAct loop
    ↓ Returns result when done
Claude Code gets result (context saved)
```

## Development

```bash
# Clone the repository
git clone https://github.com/GleeCodeAI/Glee
cd Glee

# Install dev dependencies
uv sync

# Run CLI during development
uv run glee --help
```

## Architecture

```
Claude Code (user's main agent)
    ↓ MCP Protocol
Glee MCP Server (glee/mcp_server.py)
    ↓
Glee Agent Runtime
    ├── ReAct Loop (Reason → Act → Observe)
    ├── Memory (LanceDB + DuckDB)
    └── Tool Executor
    ↓ AI Provider
Codex API / Claude API / CLI Fallback
```

**Key design decisions:**

- Glee is a full agent, not just a tool collection
- Delegates work to save context in main agent
- Uses ReAct pattern: Reason → Act → Observe
- Supports human-in-the-loop when stuck
- Falls back to CLI agents if no API configured

## Module Structure

- `glee/cli.py` - Typer CLI commands
- `glee/config.py` - Configuration management
- `glee/mcp_server.py` - MCP server exposing glee_job.* tools
- `glee/agent/` - Agent runtime (planned)
  - `loop.py` - ReAct loop implementation
  - `providers.py` - AI provider selection
  - `actions.py` - Available actions (read, write, search, etc.)
- `glee/auth/` - Authentication (planned)
  - `codex.py` - Codex OAuth (PKCE flow)
  - `copilot.py` - GitHub Copilot OAuth (device flow)
  - `storage.py` - Credential storage
- `glee/agents/` - CLI agent adapters (existing)
  - `base.py` - Base agent interface
  - `claude.py` - Claude Code CLI adapter
  - `codex.py` - Codex CLI adapter
  - `gemini.py` - Gemini CLI adapter
- `glee/memory/` - Persistent memory (LanceDB)
- `glee/db/` - Database utilities (SQLite)

## MCP Tools

### Job API (Primary - Planned)

| Tool | Description |
|------|-------------|
| `glee_job.submit` | Submit a task, returns job_id |
| `glee_job.get` | Get job status and progress |
| `glee_job.wait` | Block until job completes |
| `glee_job.result` | Get final result |
| `glee_job.needs_input` | Check if human input needed |
| `glee_job.provide_input` | Provide input to waiting job |
| `glee_job.latest` | Get most recent job |

### Existing Tools (Preserved)

| Tool | Description |
|------|-------------|
| `glee.status` | Show project status and config |
| `glee.review` | Run code review with reviewer |
| `glee.config.*` | Configuration (set, unset) |
| `glee.memory.*` | Memory tools (add, list, delete, search, overview, stats) |

## Auth Commands

```bash
# OAuth flows
glee oauth codex        # PKCE flow, opens browser
glee oauth copilot      # Device flow, shows code

# API keys
glee auth claude <key>  # Set Claude API key
glee auth gemini <key>  # Set Gemini API key
glee auth status        # Show configured providers
```

## Auth Storage

```yaml
# ~/.glee/auth.yml
codex:
  method: oauth
  access_token: "..."
  refresh_token: "..."
  expires_at: 1736956800

claude:
  method: api_key
  api_key: "sk-ant-..."
```

## Session Hooks

When `glee init claude` is run, it registers hooks in `.claude/settings.local.json`:

- **SessionStart**: Runs `glee warmup-session` to inject context
- **SessionEnd**: Runs `glee summarize-session --from=claude` to save to memory

## Files Created by `glee init`

```
project/
├── .glee/
│   ├── config.yml      # Glee project config
│   ├── auth.yml        # Project-specific auth (optional)
│   ├── memory.lance/   # Vector store
│   ├── memory.duckdb   # SQL store
│   ├── stream_logs/    # Agent stdout/stderr logs
│   ├── jobs/           # Job state persistence
│   └── tools/          # Custom tools (planned)
├── .mcp.json           # MCP server registration
└── .claude/
    └── settings.local.json  # Session hooks
```

## Implementation Status

### Done
- [x] Memory system (add, search, overview, bootstrap)
- [x] Code review with reviewers
- [x] Session hooks (warmup, summarize)
- [x] MCP integration

### In Progress
- [ ] OAuth for Codex (PKCE flow)
- [ ] OAuth for GitHub Copilot (device flow)
- [ ] API key storage

### Planned
- [ ] ReAct agent loop
- [ ] Job state management
- [ ] `glee_job.*` MCP tools
- [ ] Tool executor
