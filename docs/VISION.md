# Glee Vision

> **The Essential MCP Toolkit for Developers**

## The Problem

MCP is a game-changer for AI coding tools. But the ecosystem is fragmented:

- **Server sprawl**: Memory tools in one server, search in another, GitHub in a third...
- **Configuration hell**: Each server needs separate setup
- **Quality lottery**: Some servers are maintained, others abandoned
- **Discovery friction**: Hard to find what exists and what works

Developers shouldn't manage a fleet of MCP servers. They should code.

## The Solution

One install. Everything works.

```bash
uv tool install glee-code --python 3.13
glee init claude
# That's it. You're done.
```

Glee bundles essential developer tools into a single, well-maintained MCP server.

## What Glee Is

**A toolkit, not a platform.**

```
Claude Code
    ↓ MCP Protocol
Glee MCP Server
    ├── Memory (persistent project context)
    ├── Review (second opinion from another AI)
    ├── Session hooks (auto context management)
    └── (more tools coming)
```

## Core Principles

### 1. Consolidation Over Fragmentation

One server that does many things well beats ten servers you have to juggle.

### 2. Works Out of the Box

`glee init claude` → restart → done. No config files to edit. No API keys to manage (for basic features).

### 3. Community-Driven

Missing something? Open an issue. We ship fast.

### 4. Quality Over Quantity

Every tool is maintained. Every tool works. We'd rather have 5 great tools than 50 broken ones.

### 5. Local First

Your code stays on your machine. No cloud. No accounts. Just tools.

## Current Tools

### Memory System
Persistent project memory that survives across sessions:
- Store insights, decisions, context
- Semantic search
- Automatic session summarization

### Code Review
Get a second opinion:
- Configurable AI reviewers (Codex, Claude, Gemini)
- Structured feedback with severity levels

### Session Hooks
Automatic context management:
- Inject relevant context at session start
- Summarize and save at session end

## Roadmap

### Near-term
- **Agent delegation** — Hand off complex tasks to a background agent
- **RAG tools** — Cross-project knowledge base
- **GitHub tools** — PR reviews, issue tracking

### Future
- **Plugin system** — Let the community build tools
- **More integrations** — Whatever developers need

## Why "Glee"?

Because using good tools should bring you joy.

And because we couldn't resist the acronym potential.

---

*Glee: The Essential MCP Toolkit for Developers*
