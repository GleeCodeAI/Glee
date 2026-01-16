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

**Glee** is the essential MCP toolkit for developers.

> **The tools you actually need. One install.**

Don't install 10 different servers. Glee is the battery-included MCP toolkit that gives Claude superpowers: persistent memory, AI code review, session hooks — and soon: Git forensics, DB inspection, and background task delegation.

## Development

```bash
git clone https://github.com/AgenticHacker/glee-code
cd glee-code
uv sync
uv run glee --help
```

## Architecture

```
Claude Code
    ↓ MCP Protocol
Glee MCP Server (glee/mcp_server.py)
    ├── glee.memory.*  — Project memory (LanceDB)
    ├── glee.review    — Code review
    ├── glee.config.*  — Configuration
    └── glee.status    — Project status
```

## Module Structure

- `glee/cli.py` - Typer CLI commands
- `glee/config.py` - Configuration management
- `glee/mcp_server.py` - MCP server exposing tools
- `glee/memory/` - Persistent memory (LanceDB)
- `glee/agents/` - CLI agent adapters for code review
  - `base.py` - Base agent interface
  - `claude.py` - Claude Code CLI adapter
  - `codex.py` - Codex CLI adapter
  - `gemini.py` - Gemini CLI adapter

## MCP Tools

| Tool | Description |
|------|-------------|
| `glee.status` | Show project status and config |
| `glee.review` | Run code review with AI reviewer |
| `glee.config.set` | Set configuration |
| `glee.config.unset` | Remove configuration |
| `glee.memory.add` | Add memory entry |
| `glee.memory.search` | Semantic search |
| `glee.memory.overview` | Project overview |
| `glee.memory.list` | List memories |
| `glee.memory.delete` | Delete memory |
| `glee.memory.stats` | Memory statistics |

## Session Hooks

When `glee init claude` is run, it registers hooks in `.claude/settings.local.json`:

- **SessionStart**: Runs `glee warmup-session` to inject context
- **SessionEnd**: Runs `glee summarize-session --from=claude` to save to memory

## Files Created by `glee init`

```
project/
├── .glee/
│   ├── config.yml      # Glee project config
│   ├── memory.lance/   # Vector store
│   └── memory.duckdb   # SQL store
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
- [x] CLI structure

### Roadmap
- [ ] Agent delegation (background tasks)
- [ ] RAG tools (cross-project knowledge)
- [ ] GitHub tools (PR reviews, issues)
