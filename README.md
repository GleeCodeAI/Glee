# Glee

> **Delegate work to save context.**

Glee is an **MCP Agent Runtime** — a locally-running autonomous agent that LLM tools (Claude Code, Codex, Cursor) can delegate work to.

## The Problem

Coding agents have limited context windows. Complex tasks bloat context, causing the model to lose focus. When the session ends, context is gone.

## The Solution

Delegate work to Glee. Glee runs in its **own context** using another AI instance.

```
Claude Code (your main agent)
    ↓ glee_job.submit("refactor the auth system")
Glee Agent Runtime (separate context)
    ↓ Uses Codex/Claude API internally
    ↓ Runs autonomously with ReAct loop
    ↓ Can use tools, read files, search code
    ↓ Returns result when done
Claude Code gets result (its context stayed clean)
```

> **Delegate work. Save context.**

## Quick Start

```bash
# Install
uv tool install glee --python 3.13
# or: pipx install glee

# Initialize project (registers MCP server)
glee init claude

# Authenticate with AI provider (for Glee's reasoning)
glee oauth codex          # OAuth to Codex API
# or
glee auth claude <key>    # Claude API key
```

After restart, Claude Code can delegate work:

```
"Submit a job to Glee to refactor the authentication system"
→ glee_job.submit(task="refactor the auth system", context=["src/auth/"])
→ Returns job_id, Glee works autonomously
→ glee_job.wait(job_id) to get result
```

## Features

### MCP Tool Namespaces

| Namespace | Purpose |
|-----------|---------|
| `glee.job.*` | Delegate autonomous work to Glee agent |
| `glee.review` | Code review from another AI perspective |
| `glee.rag.*` | Cross-project knowledge base (planned) |
| `glee.memory.*` | Project memory (existing) |

### Job API

| Tool | Description |
|------|-------------|
| `glee_job.submit` | Submit a task, returns job_id |
| `glee_job.get` | Get job status and progress |
| `glee_job.wait` | Block until job completes |
| `glee_job.result` | Get final result |
| `glee_job.needs_input` | Check if human input needed |
| `glee_job.provide_input` | Provide input to waiting job |

### Code Review

```bash
glee review src/api/          # Review a directory
glee review git:changes       # Review uncommitted changes
```

### Memory System

| Tool | Description |
|------|-------------|
| `glee.memory.add` | Add memory entry |
| `glee.memory.search` | Semantic search |
| `glee.memory.overview` | Project overview |

### Supporting Infrastructure

| Component | Description |
|-----------|-------------|
| **agents** | Reusable workers (`.glee/agents/*.yml`) |
| **tools** | Extensible capabilities (`.glee/tools/`) |
| **workflows** | Orchestration of agents |

## AI Provider Setup

Glee needs an AI to power its reasoning. Configure one:

```bash
# OAuth flows (uses your existing subscription)
glee oauth codex              # Codex API (PKCE flow)
glee oauth copilot            # GitHub Copilot API (device flow)

# API keys
glee auth claude <key>        # Claude API
glee auth gemini <key>        # Gemini API

# Check status
glee auth status
```

**Priority order:** Codex API → Copilot API → Claude API → Gemini API → CLI fallback

## CLI Commands

```bash
# Setup
glee init <agent>             # Initialize project
glee oauth codex              # OAuth to Codex
glee oauth copilot            # OAuth to Copilot
glee auth <provider> <key>    # Set API key
glee auth status              # Show configured providers

# Jobs
glee status                   # Show project status

# Review
glee review <target>          # Run code review
glee config set reviewer.primary codex

# Memory
glee memory overview          # Show project memory
glee memory search <query>    # Search memory
```

## How It Works

```
glee init claude
    ├── Creates .glee/ directory
    ├── Creates .mcp.json (MCP server registration)
    └── Creates .claude/settings.local.json (session hooks)

claude (start in project)
    └── Reads .mcp.json
        └── Spawns `glee mcp` as MCP server
            └── Claude now has glee_job.* tools
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP Protocol
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Glee MCP Server                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Glee Agent Runtime                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │   │
│  │  │ ReAct Loop  │  │   Memory    │  │ Tool Executor   │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────┘
                              │ AI Provider
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌────────────┐    ┌────────────┐    ┌────────────┐
     │ Codex API  │    │ Claude API │    │ CLI Fallback│
     └────────────┘    └────────────┘    └────────────┘
```

## Configuration

```yaml
# .glee/config.yml
project:
  id: 550e8400-e29b-41d4-a716-446655440000
  name: my-app

reviewers:
  primary: codex
  secondary: gemini
```

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

## Documentation

- [docs/PRD.md](docs/PRD.md) - Product requirements
- [docs/VISION.md](docs/VISION.md) - Project vision

## Development

```bash
git clone https://github.com/GleeCodeAI/Glee
cd Glee
uv sync
uv run glee --help
```

---

*Glee: Delegate work, save context, get results.*
