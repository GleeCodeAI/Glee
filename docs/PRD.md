# Glee - The Conductor for Your AI Orchestra

> Glee (n.): A glee club is a group of voices singing in harmony — multiple AI agents collaborating to create better code.

## Background

Coding agents are everywhere — Claude Code, Codex, Gemini CLI, Cursor, and more. They're powerful, but they all share the same problems:

1. **They work alone** — No peer review, no second opinion
2. **They have no memory** — Every session starts fresh, context is lost
3. **They're siloed** — Switching agents means starting over

## The Insight

The solution isn't another coding agent. It's an **orchestration layer** that coordinates multiple agents together.

## What is Glee?

Glee is the **orchestration hub** for AI coding agents.

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
   │ Coders  │              │  Reviewers  │             │  Judges  │
   ├─────────┤              ├─────────────┤             ├──────────┤
   │ Claude  │              │   Codex     │             │ Claude   │
   │ Gemini  │              │   Claude    │             │ (disputes)│
   │ Codex   │              │   Gemini    │             └──────────┘
   └─────────┘              └─────────────┘
```

**Key principles**:
- Glee connects to agents. Agents don't connect to Glee.
- **Multiple coders**: Different agents for different parts (backend, frontend, infra)
- **Multiple reviewers**: Get diverse perspectives, catch more issues

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
# Start Glee
glee start

# Connect coders with domain expertise
glee connect claude --role coder --domain backend,api,database
glee connect gemini --role coder --domain frontend,react,css
glee connect codex --role coder --domain infra,devops,ci-cd

# Connect reviewers with focus areas
glee connect codex --role reviewer --focus security,performance
glee connect claude --role reviewer --focus architecture,maintainability

# Or use a config file
glee start --config glee.yaml

# View connected agents
glee agents
# Output:
#   Coders (dispatch: first)
#     1. claude [backend, api, database]
#     2. gemini [frontend, react, css]
#     3. codex [infra, devops, ci-cd]
#   Reviewers (dispatch: all)
#     - codex [security, performance]
#     - claude [architecture, maintainability]
```

### Project Configuration

```yaml
# .glee/config.yml
project:
  id: 550e8400-e29b-41d4-a716-446655440000  # UUID, auto-generated
  name: my-app
  path: /Users/yumin/ventures/my-app        # Absolute project path

# Agents - name is auto-generated unique ID, command is the CLI to invoke
agents:
  - name: claude-a1b2c3    # unique ID (auto-generated)
    command: claude        # CLI command to invoke
    role: coder
    domain:
      - backend
      - api
      - database
    priority: 1

  - name: gemini-d4e5f6
    command: gemini
    role: coder
    domain:
      - frontend
      - react
      - css
    priority: 2

  - name: codex-g7h8i9
    command: codex
    role: coder
    domain:
      - infra
      - devops
      - ci-cd
    priority: 3

  # Reviewers - diverse perspectives catch more issues
  - name: codex-j0k1l2
    command: codex
    role: reviewer
    focus:
      - security
      - performance

  - name: claude-m3n4o5
    command: claude
    role: reviewer
    focus:
      - architecture
      - maintainability

# Dispatch strategy: how to select when multiple agents match
dispatch:
  coder: first        # first | random | round-robin (one task = one coder)
  reviewer: all       # all | first | random (multiple reviewers add value)

memory:
  embedding_model: BAAI/bge-small-en-v1.5  # fastembed model

workflow:
  review:
    max_iterations: 10
    require_approval: true
```

### Workflow Example: Multi-Reviewer

```bash
# In Claude Code
User: Build a rate limiter

# Claude Code writes the code...
# Glee triggers parallel reviews from multiple reviewers

Glee: Sending to reviewers...
  → Codex (security, performance)
  → Claude (architecture, maintainability)

Codex: Found 2 issues:
  1. Race condition in counter increment [security]
  2. Missing cache invalidation [performance]

Claude: Found 1 issue:
  1. Consider extracting RateLimiter interface [architecture]

Glee: 3 issues found from 2 reviewers. Fixing...

# Claude Code fixes the issues...

Glee: Re-reviewing...
Codex: LGTM ✓
Claude: LGTM ✓

Glee: All reviewers approved after 2 iterations.
```

### Workflow Example: Multi-Coder

```bash
User: Build a full-stack feature with user dashboard

Glee: Dispatching to specialized coders...
  → Claude (backend): Building API endpoints
  → Gemini (frontend): Building React components
  → Codex (infra): Setting up database migrations

# Each coder works on their domain in parallel
# Glee coordinates and merges the work

Claude: Backend API complete (3 endpoints)
Gemini: Frontend components complete (Dashboard, UserStats)
Codex: Migrations complete (2 tables)

Glee: All coders finished. Triggering cross-review...
  → Backend reviewed by Gemini (API contract check)
  → Frontend reviewed by Codex (security check)
  → Infra reviewed by Claude (architecture check)

Glee: All reviews passed. Feature complete.
```

---

## Architecture

### Design Principle

**Glee = Universal Agent Gateway**

Glee runs locally, supports MCP and A2A protocols as input, and uses subprocess to invoke CLI agents as output.

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Agents                           │
│  ┌────────────────┐              ┌────────────────┐             │
│  │ MCP Client     │              │ A2A Client     │             │
│  │ (e.g. Claude)  │              │ (e.g. Gemini)  │             │
│  └───────┬────────┘              └───────┬────────┘             │
│          │ MCP Protocol                  │ A2A Protocol         │
└──────────┼───────────────────────────────┼──────────────────────┘
           ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                            Glee                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Protocol Layer                        │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │    │
│  │  │ MCP Server  │  │ A2A Server  │  │  REST API       │  │    │
│  │  │ (input)     │  │ (input)     │  │  (input)        │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                    Core Layer                            │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │    │
│  │  │Orchestrator│  │  Memory    │  │  Workflow Engine   │ │    │
│  │  └────────────┘  └────────────┘  └────────────────────┘ │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                 Subprocess Manager (output)              │    │
│  │  Invokes CLI agents with full local file access          │    │
│  └──────────────────────────┬──────────────────────────────┘    │
└─────────────────────────────┼───────────────────────────────────┘
                              │ subprocess
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌────────────┐    ┌────────────┐    ┌────────────┐
     │ Claude Code│    │   Codex    │    │  Gemini    │
     │   (CLI)    │    │   (CLI)    │    │   (CLI)    │
     └────────────┘    └────────────┘    └────────────┘
            │                 │                 │
            └─────────────────┴─────────────────┘
                              │
                     Full access to local files
```

### Why This Architecture?

**Protocol Gateway**:
- MCP clients (Claude Code, etc.) → connect via MCP protocol
- A2A clients (future agents) → connect via A2A protocol
- Any HTTP client → connect via REST API

**Subprocess Output**:
- CLI agents don't support server protocols
- Glee invokes them via subprocess (`codex exec`, `claude`, `gemini`)
- Agents run locally with full file access (no Docker isolation)

**Value Proposition**:
- Agent A (supports MCP) → via Glee → can use Agent B (CLI only)
- Agent X (supports A2A) → via Glee → can use Agent Y (CLI only)
- **Glee bridges the protocol gap**

### Agent Registry

Glee maintains a registry of available agents:

```python
class AgentRegistry:
    agents = {
        "claude": {
            "command": "claude",
            "capabilities": ["code", "review", "explain"],
            "config": "~/.claude/"
        },
        "codex": {
            "command": "codex",
            "capabilities": ["code", "review"],
            "exec_mode": "codex exec --json --full-auto"
        },
        "gemini": {
            "command": "gemini",
            "capabilities": ["code", "review"]
        },
        "opencode": {
            "command": "opencode",
            "capabilities": ["code"]
        },
        "crush": {
            "command": "crush",
            "capabilities": ["code"]
        }
    }
```

### Memory Layer

The memory layer provides persistent, searchable storage:

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
│  ├── Resolution history                                  │
│  └── Quality metrics                                     │
│                                                          │
│  Session Memory                                          │
│  ├── Current workflow state                             │
│  ├── Agent interactions                                  │
│  └── Pending actions                                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Feature**: Project ID is stable. Renaming folders doesn't lose history.

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
│   ├── config.yml          # project.id, agents, dispatch, etc.
│   ├── memory.lance/       # LanceDB - vector search
│   ├── memory.duckdb       # DuckDB - SQL queries
│   └── sessions/           # Session cache
└── .claude/
    └── settings.local.json # MCP server registration (created by glee init)
```

### Project Registry

```yaml
# ~/.config/glee/projects.yml (ID and path only, infrequently written)
projects:
  - id: 550e8400-e29b-41d4-a716-446655440000
    name: my-app
    path: /Users/yumin/ventures/my-app

  - id: 7c9e6679-7425-40de-944b-e07fc1f90ae7
    name: another-app
    path: /Users/yumin/work/another-app
```

**Data Layer:**
| Data | Storage | Reason |
|------|---------|--------|
| project.id, path | `projects.yml` | Infrequently changed |
| last_seen, stats | DuckDB | Frequently updated |
| memory, decisions | LanceDB + DuckDB | Needs search |

```yaml
# <project>/.glee/config.yml
project:
  id: 550e8400-e29b-41d4-a716-446655440000
  name: my-app
  path: /Users/yumin/ventures/my-app

agents:
  # ... project-specific agent config
```

### Path Mismatch Detection (No Auto-Update)

When path mismatch is detected, **no auto-update** — prompt user to confirm:

```bash
# Path mismatch detected
$ glee status
Warning: Project path mismatch!
  Config path: /Users/yumin/old-path/my-app
  Current path: /Users/yumin/new-path/my-app

Run 'glee update' to update the path.
```

```bash
# User confirms path update
$ glee update
Updated project path:
  Old: /Users/yumin/old-path/my-app
  New: /Users/yumin/new-path/my-app
  ID: 550e8400-e29b-41d4-a716-446655440000 (unchanged)
```

### Auto Memory Injection (Hook)

**The problem**: Every agent session starts fresh. No memory of past decisions.

**The solution**: Use agent hooks to automatically inject context at session start.

```json
// .claude/settings.json (per-project)
{
  "hooks": {
    "session_start": {
      "command": "glee context",
      "timeout": 5000
    }
  }
}
```

```bash
# What glee context returns:
$ glee context

## Project: my-app (since 2024-01)

### Architecture Decisions
- REST API with FastAPI, not GraphQL (decided 2024-01-20)
- Frontend: React + TailwindCSS
- DuckDB for local persistence (decided 2024-01-15)

### Code Conventions
- Use Pydantic for all data models
- Async handlers for all API endpoints
- pytest for testing, minimum 80% coverage

### Recent Review Issues
- Race condition in rate limiter (fixed 2024-02-01)
- Missing input validation on /api/users (fixed 2024-02-05)

### Active Coders
- claude: backend, api
- gemini: frontend, react
```

**Result**: Every new session automatically knows the project context.

---

## Core Features

### 1. Multi-Coder Collaboration

**The killer feature**: Dispatch different parts of a task to specialized agents.

```
┌──────────────────────────────────────────────────────────┐
│  User Request: "Build a full-stack dashboard"            │
└─────────────────────────────┬────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────┐
│  Glee analyzes and dispatches to specialized coders      │
└─────────────────────────────┬────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Claude        │    │ Gemini        │    │ Codex         │
│ (backend)     │    │ (frontend)    │    │ (infra)       │
│ → API routes  │    │ → Components  │    │ → Migrations  │
│ → Business    │    │ → Styling     │    │ → Docker      │
│   logic       │    │ → State mgmt  │    │ → CI/CD       │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│  Glee merges, coordinates, triggers cross-review         │
└──────────────────────────────────────────────────────────┘
```

**Why this matters**:
- Different agents excel at different things
- Parallel execution = faster results
- Specialized focus = higher quality
- Cross-review catches integration issues

### 2. Multi-Reviewer Review Loop

Get multiple perspectives on every piece of code.

```
┌──────────────────────────────────────────────────────────┐
│  Code written by coder(s)                                │
└─────────────────────────────┬────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────┐
│  Glee sends to multiple reviewers in parallel            │
└─────────────────────────────┬────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Codex         │    │ Claude        │    │ Gemini        │
│ (security)    │    │ (architecture)│    │ (ux/a11y)     │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │ Aggregate Result│
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ all_approved  │   │  has_issues   │   │ needs_human   │
│   ✓ Done      │   │  → Fix & Loop │   │  → Ask User   │
└───────────────┘   └───────────────┘   └───────────────┘
```

**Why multiple reviewers**:
- Different agents catch different issues
- Security expert + Architecture expert + UX expert = comprehensive review
- Reduces blind spots of any single agent

### 3. Intelligent Review Protocol

Not just "review this code" — structured, professional review:

```json
{
  "checklist": {
    "security": ["input validation", "auth checks", "sql injection"],
    "performance": ["n+1 queries", "caching", "async operations"],
    "maintainability": ["naming", "complexity", "documentation"]
  },
  "severity_levels": ["critical", "warning", "suggestion"],
  "output_format": "structured_json"
}
```

### 4. Role-Based Agent Assignment

Different agents for different tasks:

```yaml
agents:
  # Coders use 'domain' - their area of expertise
  - name: claude
    role: coder
    domain:
      - backend
      - api
      - database

  - name: gemini
    role: coder
    domain:
      - frontend
      - react
      - accessibility

  # Reviewers use 'focus' - what they look for
  - name: codex
    role: reviewer
    focus:
      - security
      - performance

  - name: claude
    role: reviewer
    focus:
      - architecture
      - maintainability

  # Judge arbitrates disputes between coder and reviewer
  - name: claude
    role: judge
```

### 5. Workflow Engine

Define custom multi-agent workflows:

```yaml
workflows:
  full-review:
    steps:
      - agent: codex
        action: review
        focus: [security, performance]
      - agent: claude
        action: review
        focus: [architecture, maintainability]
      - gate: all_approved

  security-audit:
    steps:
      - agent: claude
        action: security-scan
      - agent: codex
        action: vulnerability-check
      - human: approve
```

---

## CLI Commands

```bash
# Core commands
glee init                     # Initialize project + register MCP server
glee status                   # Show global status + project status
glee mcp                      # Run MCP server (used by Claude Code)

# Agent management
glee connect <agent> --role coder --domain <areas>
                              # Connect a coder with domain expertise
glee connect <agent> --role reviewer --focus <areas>
                              # Connect a reviewer with focus areas
glee disconnect <agent>       # Disconnect an agent
glee agents                   # List connected agents by role

# Multi-reviewer workflow (flexible targets)
glee review [target]          # Review files, dirs, or git changes
glee review src/api/          # Review a directory
glee review git:changes       # Review uncommitted changes
glee review git:staged        # Review staged changes
glee review "auth module"     # Natural description

# Memory
glee memory show              # Show project memory
glee memory add <key> <value> # Add to memory
glee memory search <query>    # Search memory
glee context                  # Get project context (for hook injection)

# Config
glee init --new-id            # Generate new ID (if duplicate detected)
glee config                   # Show current config

# Project management
glee project list             # List all registered projects
glee project info             # Show current project info
glee project prune            # Remove stale entries (path not found)
glee update                   # Update project path (after moving project)
```

## MCP Integration

Glee exposes tools to Claude Code via Model Context Protocol (MCP).

### How It Works

```
glee init
    ├── Creates .glee/config.yml (project config)
    └── Creates .claude/settings.local.json (MCP registration)

claude (start in project)
    └── Reads .claude/settings.local.json
        └── Spawns `glee mcp` as MCP server
            └── Claude now has glee_* tools
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `glee_status` | Show project status and connected agents |
| `glee_review` | Run multi-agent review on any target |
| `glee_connect` | Connect an agent to the project |
| `glee_disconnect` | Disconnect an agent |

### Usage in Claude Code

After `glee init`, restart Claude Code. Then:

```
"Use glee_review to review git:changes"
"Connect codex as a security reviewer"
"Show me the glee status"
```

---

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python | Ecosystem, LangGraph support |
| Package Manager | uv | Fast, modern |
| Orchestration | LangGraph | State management, workflows |
| Types | Pydantic | Validation, serialization |
| Embedding | fastembed | Local generation, no API, lightweight & fast |
| Vector DB | LanceDB | Embedded, single file, vector search |
| SQL DB | DuckDB | Embedded, single file, SQL queries |
| CLI | Typer | User-friendly CLI |

---

## Storage (Embedded, No Server)

Embedded databases, no Docker or external server required:

```
.glee/
├── config.yml
├── memory.lance/       # LanceDB - vector storage + search
├── memory.duckdb       # DuckDB - SQL queries
└── sessions/
```

**Data Flow:**
```
User input / Agent output
    ↓
fastembed (local embedding generation)
    ↓
LanceDB (store vectors, semantic search)
    ↓
DuckDB (structured queries, statistics)
```

**Benefits:**
- Zero config, no Docker
- Fully local, no API
- Single file, easy backup
- Cross-platform (macOS, Linux, Windows)

---

## Project Structure

```
glee/
├── glee/
│   ├── __init__.py
│   ├── cli.py                # Typer CLI commands
│   ├── config.py             # Configuration management
│   ├── logging.py            # Logging setup
│   ├── mcp_server.py         # MCP server for Claude Code integration
│   ├── agents/
│   │   ├── __init__.py       # Agent registry
│   │   ├── base.py           # Agent interface
│   │   ├── claude.py         # Claude Code adapter
│   │   ├── codex.py          # Codex adapter
│   │   ├── gemini.py         # Gemini adapter
│   │   └── prompts.py        # Reusable prompt templates
│   └── memory/               # TODO: Memory layer
│       ├── store.py          # Memory abstraction
│       ├── lance.py          # LanceDB backend (vector)
│       ├── duck.py           # DuckDB backend (SQL)
│       └── embed.py          # fastembed wrapper
├── docs/
│   ├── VISION.md
│   └── PRD.md
├── tests/
└── pyproject.toml
```

---

## V1 Scope

**Goal**: A working multi-agent platform that supports multiple coders and reviewers.

### Must Have
- [x] `glee init` - Initialize project with MCP registration
- [x] `glee connect <agent> --role <role>` for Claude, Codex, Gemini
- [x] **Multiple coders** with domain focus (backend, frontend, infra)
- [x] **Multiple reviewers** with specialty (security, architecture, ux)
- [x] Parallel agent execution
- [x] `glee review` triggers multi-reviewer workflow with flexible targets
- [x] `glee status` shows global + project status
- [x] `.glee/config.yml` project config
- [x] **MCP integration** - `glee mcp` server exposes tools to Claude Code
- [ ] LanceDB + DuckDB + fastembed (embedded, no server)
- [ ] **Auto memory injection via hook** - `glee context` command for session_start hook

### Nice to Have
- [ ] Agent auto-selection based on task analysis
- [ ] Custom review checklists
- [ ] Conflict resolution for overlapping work

### Out of Scope (V2+)
- Advanced RAG (cross-project knowledge base)
- Team features (multi-user collaboration)
- GitHub integration
- Knowledge marketplace

---

## Success Metrics

1. **Time to first review**: < 5 minutes from install
2. **Review quality**: Catches issues that single agent misses
3. **Memory value**: Context persists across sessions, survives folder renames
4. **Agent agnostic**: Works with any CLI-based coding agent

---

## Open Questions

1. ~~**How does Glee communicate with agents?**~~ ✅ Resolved
   - **Input**: Glee exposes MCP Server + A2A Server + REST API
   - **Output**: Glee invokes CLI agents via subprocess

2. ~~**How does Glee intercept agent output?**~~ ✅ Resolved
   - Subprocess captures stdout/stderr directly
   - Use `--json` flags where available (e.g., `codex exec --json`)

3. ~~**Should Glee have a TUI/Dashboard?**~~ ✅ Resolved
   - **Web UI** (not TUI) — more accessible, broader audience
   - Show agent status, review progress, memory stats
   - Served via FastAPI at `/dashboard`

4. ~~**A2A implementation priority?**~~ ✅ Resolved
   - V1 supports both MCP and A2A
   - Both protocols are straightforward to implement

---

*Glee: The Conductor for Your AI Orchestra.*
