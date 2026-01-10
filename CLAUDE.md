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

Glee is the Stage Manager for Your AI Orchestra - an orchestration layer for AI coding agents (Claude, Codex, Gemini) with shared memory and code review.

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

## Usage

```bash
# Initialize project (creates .glee/ and registers MCP server)
glee init

# Configure reviewers
glee config set reviewer.primary codex
glee config set reviewer.secondary gemini

# View configuration
glee config get
glee status

# Run review (flexible targets)
glee review src/main.py           # File
glee review src/api/              # Directory
glee review git:changes           # Uncommitted changes
glee review git:staged            # Staged changes

# Test an agent
glee test-agent codex --prompt "Say hello"

# Run MCP server (used by Claude Code automatically)
glee mcp
```

## Architecture

```
User (via Claude Code)
    ↓ MCP protocol
Glee (glee/mcp_server.py)
    ↓ subprocess
Reviewer CLI (codex, claude, gemini)
```

**Key design decisions:**

- Main agent handles coding - no separate "coder" role
- Reviewers are preferences (primary + optional secondary)
- One reviewer at a time, user decides what feedback to apply
- Glee invokes CLI agents via subprocess
- MCP server exposes Glee tools to Claude Code
- Stream logs to `.glee/stream_logs/` for observability

## Module Structure

- `glee/cli.py` - Typer CLI commands
- `glee/config.py` - Configuration management
- `glee/dispatch.py` - Reviewer selection
- `glee/mcp_server.py` - MCP server for Claude Code integration
- `glee/agents/` - Agent adapters (Claude, Codex, Gemini)
  - `base.py` - Base agent interface
  - `claude.py` - Claude Code CLI adapter
  - `codex.py` - Codex CLI adapter
  - `gemini.py` - Gemini CLI adapter
  - `prompts.py` - Reusable prompt templates
- `glee/memory/` - Persistent memory (LanceDB)
- `glee/db/` - Database utilities (SQLite)

## MCP Tools

When `glee init` is run, it registers Glee as an MCP server in `.mcp.json`. Claude Code then has access to:

- `glee_status` - Show project status and reviewer config
- `glee_review` - Run code review with primary reviewer
- `glee_config_set` - Set config value (e.g., reviewer.primary)
- `glee_config_unset` - Unset config value (e.g., reviewer.secondary)
- `glee_memory_*` - Memory management tools
- `glee_task` - Spawn subagent for a task (V2)

## Config Structure

```yaml
# .glee/config.yml
project:
  id: uuid
  name: project-name

reviewers:
  primary: codex    # Default reviewer
  secondary: gemini # Optional, for second opinions
```

## Files Created by `glee init`

```
project/
├── .glee/
│   ├── config.yml      # Glee project config
│   ├── memory.lance/   # Vector store
│   ├── memory.duckdb   # SQL store
│   ├── stream_logs/    # Agent stdout/stderr logs
│   ├── agents/         # Subagent definitions (V2)
│   ├── workflows/      # Workflow definitions (V2)
│   └── sessions/       # Session cache (V2)
└── .mcp.json           # MCP server registration (for Claude Code)
```

## Subagent Orchestration (V2)

Glee separates two concepts:
- **Agents**: Reusable workers (`.glee/agents/*.yml`)
- **Workflows**: Orchestration of agents (`.glee/workflows/*.yml`)

See `docs/subagents.md` and `docs/workflows.md` for details.
