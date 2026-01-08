# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Glee is the Conductor for Your AI Orchestra - an orchestration layer for AI coding agents (Claude, Codex, Gemini) with shared memory, context injection, and multi-agent collaboration.

## Commands

```bash
# Install dependencies
uv sync

# Run CLI
uv run glee --help

# Initialize project
uv run glee init

# Connect agents
uv run glee connect claude --role coder --domain backend,api
uv run glee connect codex --role reviewer --focus security,performance

# View status
uv run glee status

# Run review
uv run glee review [files...]

# Test an agent
uv run glee test-agent claude --prompt "Say hello"
```

## Architecture

```
User
    ↓ CLI
Glee (glee/cli.py)
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

## Module Structure

- `glee/cli.py` - Typer CLI commands
- `glee/config.py` - Configuration management
- `glee/agents/` - Agent adapters (Claude, Codex, Gemini)
  - `base.py` - Base agent interface
  - `claude.py` - Claude Code CLI adapter
  - `codex.py` - Codex CLI adapter
  - `gemini.py` - Gemini CLI adapter

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
