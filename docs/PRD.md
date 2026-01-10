# Glee - Stage Manager for Your AI Orchestra

> Glee (n.): A glee club is a group of voices singing in harmony — multiple AI agents collaborating to create better code.

## Background

Coding agents are everywhere — Claude Code, Codex, Gemini CLI, Cursor, and more. They're powerful, but they all share the same problems:

1. **They work alone** — No peer review, no second opinion
2. **They have no memory** — Every session starts fresh, context is lost
3. **They're siloed** — Switching agents means starting over

## The Insight

The solution isn't another coding agent. It's an **orchestration layer** that coordinates code review and maintains memory.

## What is Glee?

Glee is the **stage manager** for AI coding agents.

```
                    ┌─────────────────────────────────┐
                    │             Glee                │
                    │  ┌─────────┐ ┌───────────────┐ │
                    │  │ Memory  │ │ Orchestration │ │
                    │  └─────────┘ └───────────────┘ │
                    └──────────────┬──────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
   ┌─────────┐              ┌─────────────┐             ┌──────────┐
   │  Main   │              │  Reviewers  │             │  Memory  │
   │  Agent  │              ├─────────────┤             │  Store   │
   ├─────────┤              │ Primary:    │             ├──────────┤
   │ Claude  │              │   Codex     │             │ LanceDB  │
   │ (user's │              │ Secondary:  │             │ DuckDB   │
   │  agent) │              │   Gemini    │             └──────────┘
   └─────────┘              └─────────────┘
```

**Key principles**:
- Main agent handles coding - no separate "coder" role
- Reviewers are preferences (primary + optional secondary)
- User decides what feedback to apply (HITL)
- Maximum 2 reviewers per review cycle

## User Experience

### Installation

```bash
# Global install
uv tool install glee
# or
pipx install glee
# or
brew install glee
```

### Basic Usage

```bash
# Initialize project
glee init

# Set reviewer preferences
glee config set reviewer.primary codex
glee config set reviewer.secondary gemini

# View configuration
glee config get
glee status

# Run review
glee review src/api/          # Review a directory
glee review git:changes       # Review uncommitted changes
glee review git:staged        # Review staged changes
```

### Project Configuration

```yaml
# .glee/config.yml
project:
  id: 550e8400-e29b-41d4-a716-446655440000  # UUID, auto-generated
  name: my-app

reviewers:
  primary: codex    # Default reviewer (required)
  secondary: gemini # For second opinions (optional)
```

### Review Flow

```
User: "Review my code"
         ↓
Glee invokes primary reviewer
         ↓
Reviewer returns structured feedback
         ↓
User decides:
  a) Apply - implement the feedback
  b) Discard - ignore the feedback
  c) Second opinion - get another review
```

---

## Architecture

### Design Principle

**Glee = Stage Manager**

Glee runs locally, connects via MCP protocol, and invokes CLI agents via subprocess.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                               │
│                    (user's main agent)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP Protocol
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                            Glee                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    MCP Server                            │    │
│  │  Tools: glee_status, glee_review, glee_connect, etc.    │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                    Core Layer                            │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │    │
│  │  │  Dispatch  │  │  Memory    │  │  Stream Logging    │ │    │
│  │  └────────────┘  └────────────┘  └────────────────────┘ │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │ subprocess                         │
└─────────────────────────────┼───────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
     ┌────────────┐                      ┌────────────┐
     │   Codex    │                      │   Gemini   │
     │  (primary) │                      │ (secondary)│
     └────────────┘                      └────────────┘
```

### Memory Layer

```
┌─────────────────────────────────────────────────────────┐
│                    Memory Layer                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Project Memory                                          │
│  ├── Architecture decisions & rationale                 │
│  ├── Code conventions & style guide                     │
│  ├── Tech stack & dependencies                          │
│  └── Historical context                                  │
│                                                          │
│  Review Memory                                           │
│  ├── Past review feedback                               │
│  ├── Common issues & patterns                           │
│  └── Resolution history                                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Config Directory Structure

```
# Global config (XDG standard)
~/.config/glee/
├── config.yml              # Global defaults
├── projects.yml            # Project registry
└── credentials.yml         # API keys

# Project config
<project>/
├── .glee/                  # gitignore this directory
│   ├── config.yml          # project.id, reviewers
│   ├── memory.lance/       # LanceDB - vector search
│   ├── memory.duckdb       # DuckDB - SQL queries
│   ├── stream_logs/        # Agent stdout/stderr
│   └── sessions/           # Session cache
└── .mcp.json               # MCP server registration
```

---

## Core Features

### 1. Structured Code Review

Get professional code review with severity levels:

```
[MUST] Fix SQL injection vulnerability in query builder
[HIGH] Memory leak in connection pool
[SHOULD] Consider using async/await for I/O operations
[MEDIUM] Function exceeds 50 lines, consider splitting
[LOW] Variable 'x' could have more descriptive name
```

### 2. Reviewer Preferences

Configure which agent reviews your code:

```yaml
reviewers:
  primary: codex    # Used by default
  secondary: gemini # For second opinions
```

### 3. Persistent Memory

Glee remembers your project:

- Architecture decisions
- Code conventions
- Past review feedback
- Common patterns

### 4. Stream Logging

All agent output logged to `.glee/stream_logs/`:

```bash
# Watch in real-time
tail -f .glee/stream_logs/stdout-*.log
```

### 5. Subagent Orchestration (V2)

Glee becomes the universal subagent orchestrator:

**Two concepts:**
- **Agents**: Reusable workers defined in `.glee/agents/*.yml`
- **Workflows**: Orchestration of agents (human or AI defined)

```yaml
# .glee/agents/security-scanner.yml
name: security-scanner
description: Scan code for security vulnerabilities
agent: codex
prompt: |
  You are a security expert. Analyze the given code for:
  - SQL injection
  - XSS vulnerabilities
  - Authentication issues
```

**Import from other formats:**
```bash
glee agents import --from claude  # .claude/agents/*.md → .glee/agents/*.yml
glee agents import --from gemini  # .gemini/agents/*.toml → .glee/agents/*.yml
```

See [docs/workflows.md](workflows.md) and [docs/subagents.md](subagents.md) for details.

---

## CLI Commands

```bash
# Core commands
glee init                     # Initialize project + register MCP server
glee status                   # Show global status + project status
glee mcp                      # Run MCP server (used by Claude Code)

# Configuration
glee config get                          # Show all config
glee config get reviewer.primary         # Show specific key
glee config set reviewer.primary codex   # Set primary reviewer
glee config set reviewer.secondary gemini # Set secondary reviewer
glee config unset reviewer.secondary     # Clear secondary reviewer

# Review (flexible targets)
glee review [target]          # Review files, dirs, or git changes
glee review src/api/          # Review a directory
glee review git:changes       # Review uncommitted changes
glee review git:staged        # Review staged changes

# Memory
glee memory show              # Show project memory
glee memory add <key> <value> # Add to memory
glee memory search <query>    # Search memory

# Logs
glee logs show                # Show recent logs
glee logs agents              # Show agent run history
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `glee_status` | Show project status and reviewer config |
| `glee_review` | Run review with primary reviewer |
| `glee_config_set` | Set a config value (e.g., reviewer.primary) |
| `glee_config_unset` | Unset a config value (e.g., reviewer.secondary) |
| `glee_memory_*` | Memory management tools |

---

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python | Ecosystem, tooling |
| Package Manager | uv | Fast, modern |
| Types | Pydantic | Validation, serialization |
| Embedding | fastembed | Local generation, no API |
| Vector DB | LanceDB | Embedded, vector search |
| SQL DB | DuckDB | Embedded, SQL queries |
| CLI | Typer | User-friendly CLI |

---

## Project Structure

```
glee/
├── glee/
│   ├── __init__.py
│   ├── cli.py                # Typer CLI commands
│   ├── config.py             # Configuration management
│   ├── dispatch.py           # Reviewer selection
│   ├── logging.py            # Logging setup
│   ├── mcp_server.py         # MCP server for Claude Code
│   ├── agents/
│   │   ├── __init__.py       # Agent registry
│   │   ├── base.py           # Agent interface
│   │   ├── claude.py         # Claude Code adapter
│   │   ├── codex.py          # Codex adapter
│   │   ├── gemini.py         # Gemini adapter
│   │   └── prompts.py        # Reusable prompt templates
│   ├── memory/
│   │   ├── store.py          # Memory abstraction
│   │   └── embed.py          # Embedding wrapper
│   └── db/
│       └── sqlite.py         # SQLite utilities
├── docs/
│   ├── VISION.md
│   ├── PRD.md
│   ├── agentic.md
│   ├── arbitration.md
│   ├── subagents.md
│   ├── workflows.md
│   └── stream_log.md
├── tests/
└── pyproject.toml
```

---

## V1 Scope

**Goal**: A working review platform with memory.

### Done
- [x] `glee init` - Initialize project with MCP registration
- [x] `glee config set/get/unset` - Configuration management
- [x] `glee review` - Run code review with primary reviewer
- [x] `glee status` - Show global + project status
- [x] `.glee/config.yml` - Simplified project config
- [x] MCP integration - `glee mcp` server exposes tools
- [x] LanceDB + DuckDB + fastembed (embedded, no server)
- [x] Stream logging to `.glee/stream_logs/`

### TODO
- [ ] `--second-opinion` flag for review
- [ ] Auto memory injection via hook
- [ ] Side-by-side feedback comparison

### V2: Subagent Orchestration
- [ ] `glee_task` MCP tool
- [ ] `.glee/agents/*.yml` format
- [ ] `glee agents import` from Claude/Gemini
- [ ] Session management for stateful conversations
- [ ] `.glee/workflows/*.yml` format (V2.1)

### Out of Scope (V3+)
- Advanced RAG (cross-project knowledge base)
- Team features (multi-user collaboration)
- GitHub integration
- Web dashboard

---

## Success Metrics

1. **Time to first review**: < 5 minutes from install
2. **Review quality**: Catches issues that single agent misses
3. **Memory value**: Context persists across sessions
4. **User control**: Human always decides what to apply

---

*Glee: Stage Manager for Your AI Orchestra.*
