# Glee

**The Essential MCP Toolkit for Developers**

Don't install 10 different servers. Glee is the battery-included MCP toolkit that gives Claude superpowers: persistent memory, AI code review, session hooks — and soon: Git forensics, DB inspection, and background task delegation.

Missing something? [Open an issue](https://github.com/GleeMCP/Glee/issues). We ship fast.

## Quick Start

```bash
# Install
uv tool install glee-code --python 3.13
# or: pipx install glee-code

# Initialize (registers MCP server with Claude Code)
glee init claude

# Restart Claude Code - done!
```

## Tools

> See [Full MCP Service List](docs/GleeMcpServiceList.md) for all 42 tools (11 implemented, 31 planned).

### Memory

Persistent project memory that survives across sessions.

| Tool                   | Description                        |
| ---------------------- | ---------------------------------- |
| `glee.memory.add`      | Store insights, decisions, context |
| `glee.memory.search`   | Semantic search across memory      |
| `glee.memory.overview` | Get project summary                |

### Code Review

Get a second opinion from another AI.

| Tool          | Description                               |
| ------------- | ----------------------------------------- |
| `glee.review` | Review code with configurable AI reviewer |

```bash
glee review src/api/          # Review a directory
glee review git:changes       # Review uncommitted changes
```

### Session Hooks

Automatic context management for Claude Code sessions.

- **Session start**: Injects relevant project context
- **Session end**: Summarizes and saves to memory

### Status & Config

| Tool                | Description          |
| ------------------- | -------------------- |
| `glee.status`       | Show project status  |
| `glee.config.set`   | Set configuration    |
| `glee.config.unset` | Remove configuration |

## CLI Commands

```bash
# Setup
glee init claude              # Initialize project for Claude Code
glee connect status           # Show connected providers

# Memory
glee memory overview          # Show project memory
glee memory search <query>    # Search memory

# Review
glee review <target>          # Run code review
glee config set reviewer.primary codex
```

## How It Works

```
glee init claude
    ├── Creates .glee/ directory
    ├── Creates .mcp.json (MCP server registration)
    └── Creates .claude/settings.local.json (session hooks)

claude (start session)
    └── Reads .mcp.json
        └── Spawns `glee mcp` as MCP server
            └── Claude now has glee.* tools
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

## Roadmap

We're building more tools. Here's what's coming:

- [ ] **Agent delegation** — Hand off complex tasks to a background agent
- [ ] **RAG tools** — Cross-project knowledge base
- [ ] **GitHub tools** — PR reviews, issue tracking
- [ ] **More integrations** — What do you need?

[Request a feature →](https://github.com/AgenticHacker/glee-code/issues)

## Development

```bash
git clone https://github.com/AgenticHacker/glee-code
cd glee-code
uv sync
uv run glee --help
```

## Why "Glee"?

Because using good tools should bring you joy. And because we couldn't resist the acronym potential.

---

_Glee: The Essential MCP Toolkit for Developers_
