# PRD — Glee

## 1. Product Definition

**Glee** is the essential MCP toolkit for developers.

> **The tools you actually need. One install.**

## 2. The Problem

MCP is powerful, but the ecosystem is fragmented:

1. **Server sprawl** — Need one MCP server for memory, another for search, another for GitHub...
2. **Configuration overhead** — Each server needs separate setup and configuration
3. **Inconsistent quality** — Some servers are maintained, others abandoned
4. **Discovery friction** — Hard to find what tools exist and which ones work

## 3. The Solution

One install. Everything works.

Glee bundles the essential developer tools into a single MCP server that works out of the box with Claude Code.

```
Claude Code
    ↓ MCP Protocol
Glee MCP Server
    ├── Memory tools
    ├── Code review
    ├── Session hooks
    └── (more coming)
```

## 4. Core Principles

| Principle | Description |
|-----------|-------------|
| **Consolidation** | One server instead of many |
| **Works out of the box** | `glee init claude` and you're done |
| **Community-driven** | Missing something? We ship fast |
| **Quality over quantity** | Every tool is well-maintained |

## 5. Current Tools

### Memory System
- `glee.memory.add` — Store insights, decisions, context
- `glee.memory.search` — Semantic search across memory
- `glee.memory.overview` — Get project summary

### Code Review
- `glee.review` — Get a second opinion from another AI

### Session Hooks
- Automatic context injection at session start
- Automatic summarization at session end

### Configuration
- `glee.status` — Project status
- `glee.config.set/unset` — Configuration management

## 6. Roadmap

### Near-term
- [ ] Agent delegation — Hand off complex tasks to background agent
- [ ] RAG tools — Cross-project knowledge base
- [ ] GitHub tools — PR reviews, issue tracking

### Future
- [ ] More integrations based on community requests
- [ ] Plugin system for custom tools

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Setup time | < 1 minute |
| Tools that "just work" | 100% |
| Community response time | < 24 hours for feature requests |

## 8. Non-Goals

- **Not a framework** — Glee is tools, not infrastructure
- **Not a platform** — No accounts, no cloud, runs locally
- **Not a marketplace** — Curated tools, not an app store

---

*Glee: The Essential MCP Toolkit for Developers*
