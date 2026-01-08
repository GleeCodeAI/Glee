# Glee Vision

## The Problem

Coding agents are everywhere — Claude Code, Codex, Gemini CLI, Cursor, Windsurf, and more are shipping weekly. They're powerful. They're fast. But they all share the same fundamental problems:

1. **They work alone.** Each agent operates in isolation, with its own biases and blind spots. No peer review. No second opinion. No collaboration between agents with different strengths.

2. **They have no memory.** Every session starts fresh. They don't remember your project's conventions, past decisions, or lessons learned. You explain the same context over and over. Worse: some agents (Claude Code) use directory paths as project identifiers — rename a folder and all your history vanishes. Months of context, gone.

3. **They're interchangeable.** Today's best agent is tomorrow's second choice. But switching means losing all context and starting over.

## The Insight

The solution isn't to build another coding agent.

The solution is to build **an orchestration layer** that coordinates them all.

## What is Glee?

Glee is the **Universal Agent Gateway**.

Not a replacement. A multiplier.

```
Without Glee:
┌─────────────┐
│   Agent     │ → Works alone, no memory, no checks
└─────────────┘

With Glee:
┌─────────────────────────────────────────────────────────────┐
│                           Glee                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │
│  │MCP Server│  │A2A Server│  │ REST API │  │  Web UI    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────────┘   │
│       └─────────────┴─────────────┘                          │
│                     │                                        │
│       ┌─────────────┴─────────────┐                         │
│       │  Orchestrator + Memory    │                         │
│       └─────────────┬─────────────┘                         │
│                     │ subprocess                             │
└─────────────────────┼───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐     ┌───────────┐     ┌──────────┐
│ Coders  │     │ Reviewers │     │  Judges  │
├─────────┤     ├───────────┤     ├──────────┤
│ Claude  │     │  Codex    │     │ Claude   │
│ Gemini  │     │  Claude   │     │ (disputes)│
│ Codex   │     │  Gemini   │     └──────────┘
└─────────┘     └───────────┘
```

**Protocol In, Subprocess Out**:
- Claude Code connects via MCP protocol (`glee mcp` server)
- `glee init` registers MCP server in project's `.claude/settings.local.json`
- Glee invokes CLI agents via subprocess
- Every agent can talk to every other agent — through Glee

**Multiple Coders, Multiple Reviewers**:
- Coders have **domains** (backend, frontend, infra) — their area of expertise
- Reviewers have **focus** (security, architecture, ux) — what they look for
- Parallel execution for speed, cross-review for quality

## Four Pillars

### 1. Multi-Agent Collaboration

**The killer feature.** Why use one agent when you can use them all?

**Multiple Coders** (by domain):
- Claude: `domain: [backend, api, database]`
- Gemini: `domain: [frontend, react, css]`
- Codex: `domain: [infra, devops, ci-cd]`
- Dispatch: `first | random | round-robin` (one task = one coder)

**Multiple Reviewers** (by focus):
- Codex: `focus: [security, performance]`
- Claude: `focus: [architecture, maintainability]`
- Gemini: `focus: [accessibility, ux]`
- Dispatch: `all | first | random` (multiple reviewers add value)

```
User: "Build a full-stack dashboard"

Glee dispatches by domain:
  → Claude [backend]: API endpoints, business logic
  → Gemini [frontend]: React components, styling
  → Codex [infra]: Database migrations, CI/CD

Then reviews by focus:
  → Codex [security]: checks all code for vulnerabilities
  → Claude [architecture]: checks structure and patterns
  → Gemini [accessibility]: checks UI components
```

**Different agents excel at different things. Glee lets you use them all.**

### 2. Intelligent Review Protocol

Agents make mistakes. Code gets shipped with bugs, security holes, and anti-patterns.

Glee provides structured, professional code review:

- Curated review checklists by language and framework
- Security, performance, and maintainability standards
- Structured feedback that agents can act on
- Iteration loops until quality gates pass

**Not "does this code look okay?" — but systematic quality assurance.**

### 3. Agent Abstraction Layer

Today you use Claude Code. Tomorrow maybe Codex is better for your use case. Next month, a new player emerges.

Glee abstracts the underlying agent:

- Unified interface across all coding agents
- Mix and match: Claude writes, Codex reviews, Gemini audits
- Switch agents without losing context
- Best tool for each job

**Use any agent. Use all agents. Glee orchestrates.**

### 4. Persistent Memory

This is the biggest gap in today's coding agents.

Glee remembers everything:

- **Project memory**: Architecture decisions, conventions, tech stack choices
- **Review memory**: Past issues, common mistakes, what worked
- **Team memory**: Who owns what, style preferences, tribal knowledge
- **Learning**: Gets smarter about your codebase over time

**Storage (Embedded, No Server)**:

```
# Global config
~/.config/glee/
├── config.yml              # Global defaults
├── projects.yml            # Project registry (ID → path)
└── credentials.yml         # API keys

# Project config (gitignore .glee/)
<project>/.glee/
├── config.yml              # project.id, agents, dispatch
├── memory.lance/           # LanceDB - vector search
├── memory.duckdb           # DuckDB - SQL queries
└── sessions/               # Session cache
```

**Tech stack**:
```
fastembed (local embedding, no API)
    ↓
LanceDB (vector storage + semantic search)
    ↓
DuckDB (SQL queries)
```

**Project ID is stable**: Renaming/moving projects doesn't lose history. Glee prompts user to run `glee update` when path mismatch is detected.

**Auto-injection via hooks**: When you start a new session, Glee automatically injects relevant context.

```
Claude Code starts
    ↓ hook: session_start
glee context
    ↓ returns project context
Claude Code now knows:
  - Architecture decisions
  - Code conventions
  - Recent review issues
  - Active coders and their domains
  - Active reviewers and their focus
```

Every agent you use can tap into this shared memory — automatically.

**The more you use Glee, the better every agent becomes at understanding your project.**

## The Flywheel

```
More Agents → Better Coverage → Fewer Bugs → More Trust → More Usage
     ↓                                                        ↓
More Memory → Smarter Context → Better Reviews → Better Code ←┘
```

This is the moat:
- **Agent synergy**: Each agent's strength compensates for another's weakness
- **Memory compounds**: Every review, every decision makes Glee smarter
- **Network effects**: More agents supported = more combinations = more value

This knowledge and coordination can't be replicated by switching to a new tool.

## Design Principles

### 1. Orchestrator, Not Competitor

We don't replace coding agents. We coordinate them. When Claude Code ships a new feature, Glee users benefit immediately.

### 2. Agent Agnostic

No lock-in to any single agent. Glee works with Claude Code, Codex, Gemini CLI, Cursor, and whatever comes next.

### 3. Local First

Your code stays on your machine. Agents run locally with full capabilities. Memory can be local or synced.

### 4. Zero Config Start

`uvx glee` and you're running. Complexity is opt-in, not required.

### 5. Open Core

The orchestration layer is open source. Build on it, extend it, trust it.

## V1: The Starting Point

The first version focuses on multi-agent collaboration:

**"Multiple coders. Multiple reviewers. One orchestrator."**

- **MCP integration**: `glee init` registers Glee as MCP server, Claude Code gets `glee_*` tools
- **Multiple coders**: Assign Claude to backend, Gemini to frontend, Codex to infra
- **Multiple reviewers**: Security review + Architecture review + UX review in parallel
- **Flexible review targets**: Review files, directories, `git:changes`, or natural descriptions
- Works with Claude Code, Codex, Gemini CLI out of the box
- Installs in one command, zero config

This establishes the core pattern: your agents + Glee = better code, faster.

## The Future

### V2: Advanced Memory

- Vector database for semantic search
- Automatic context injection based on task
- Learn from every review and decision
- Cross-project knowledge sharing

### V3: Intelligent Dispatch

- Auto-detect task type and assign to best agent
- Load balancing across agents
- Conflict resolution for overlapping work
- Smart task decomposition

### V4: Team & Enterprise

- Shared memory across team
- GitHub/GitLab integration
- Audit logs and compliance
- SSO and access control

### V5: Knowledge Marketplace

- Share review checklists
- Import best practices
- Community-contributed agent configs
- Agent performance benchmarks

## Why "Glee"?

A glee club is a group of voices singing in harmony. No single voice dominates — each contributes its unique part to create something greater than any could alone.

That's what we're building: a harmonious collaboration between AI agents, each contributing their strengths, coordinated into beautiful code.

---

_Glee: The Conductor for Your AI Orchestra._
