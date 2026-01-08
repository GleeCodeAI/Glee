# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Glee is the Conductor for Your AI Orchestra - an orchestration layer for AI coding agents (Claude, Codex, Gemini) with shared memory, context injection, and multi-agent collaboration.

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

# Connect agents
glee connect claude --role coder --domain backend,api
glee connect codex --role reviewer --focus security,performance

# View status (global + project)
glee status

# Run review (flexible targets)
glee review src/main.py           # File
glee review src/api/              # Directory
glee review git:changes           # Uncommitted changes
glee review git:staged            # Staged changes
glee review "the auth module"     # Natural description

# Test an agent
glee test-agent claude --prompt "Say hello"

# Run MCP server (used by Claude Code automatically)
glee mcp
```

## Architecture

```
User
    ↓ CLI or MCP
Glee (glee/cli.py, glee/mcp_server.py)
    ↓ orchestrates
Agent Registry (glee/agents/)
    ↓ subprocess
Claude/Codex/Gemini CLI
```

**Key design decisions:**

- Glee invokes CLI agents via subprocess
- Each agent has unique name (e.g., `claude-a1b2c3`) and command (e.g., `claude`)
- Multiple coders with domain specialization
- Multiple reviewers with focus areas
- Parallel review execution
- MCP server exposes Glee tools to Claude Code

## Module Structure

- `glee/cli.py` - Typer CLI commands
- `glee/config.py` - Configuration management
- `glee/mcp_server.py` - MCP server for Claude Code integration
- `glee/agents/` - Agent adapters (Claude, Codex, Gemini)
  - `base.py` - Base agent interface
  - `claude.py` - Claude Code CLI adapter
  - `codex.py` - Codex CLI adapter
  - `gemini.py` - Gemini CLI adapter
  - `prompts.py` - Reusable prompt templates

## MCP Tools

When `glee init` is run, it registers Glee as an MCP server in `.claude/settings.local.json`. Claude Code then has access to:

- `glee_status` - Show project status and connected agents
- `glee_review` - Run multi-agent review (accepts flexible target)
- `glee_connect` - Connect an agent to the project
- `glee_disconnect` - Disconnect an agent

## Config Structure

```yaml
# .glee/config.yml
project:
  id: uuid
  name: project-name
  path: /absolute/path

agents:
  - name: claude-a1b2c3    # unique ID
    command: claude        # CLI to invoke
    role: coder
    domain: [backend, api]
    priority: 1

dispatch:
  coder: first      # first | random | round-robin
  reviewer: all     # all | first | random
```

## Files Created by `glee init`

```
project/
├── .glee/
│   └── config.yml              # Glee project config
└── .claude/
    └── settings.local.json     # MCP server registration
```
