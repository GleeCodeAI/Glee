# Glee

> The Conductor for Your AI Orchestra

An orchestration layer for AI coding agents with shared memory, context injection, and multi-agent collaboration.

## Quick Start

```bash
# Install
uv tool install glee --python 3.13
# or: pipx install glee

# Upgrade
uv tool upgrade glee --python 3.13

# Initialize project (registers MCP server for Claude Code)
glee init

# Connect agents
glee connect claude --role coder --domain backend,api
glee connect codex --role reviewer --focus security,performance

# View status
glee status

# Run review
glee review src/main.py
glee review git:changes          # Review uncommitted changes
glee review git:staged           # Review staged changes
```

## Features

- **MCP Integration**: `glee init` registers Glee as an MCP server - Claude Code gets `glee_*` tools automatically
- **Multiple Coders**: Different agents for different domains (backend, frontend, infra)
- **Multiple Reviewers**: Get diverse perspectives (security, performance, architecture)
- **Parallel Execution**: Reviews run concurrently for speed
- **Flexible Review Targets**: Review files, directories, git changes, or natural descriptions

## Claude Code Integration

After running `glee init`, restart Claude Code. You'll have these MCP tools:

- `glee_status` - Show project status and connected agents
- `glee_review` - Run multi-agent review on any target
- `glee_connect` - Connect an agent to the project
- `glee_disconnect` - Disconnect an agent

```
# In Claude Code, you can now say:
"Use glee_review to review the uncommitted changes"
"Connect codex as a security reviewer using glee"
```

## CLI Commands

```bash
glee init                         # Initialize project + register MCP server
glee status                       # Show global and project status
glee connect <cmd> --role <role>  # Connect an agent
glee disconnect <name>            # Disconnect an agent
glee agents                       # List available agents
glee review [target]              # Run multi-reviewer workflow
glee test-agent <cmd>             # Test an agent
glee mcp                          # Run MCP server (used by Claude Code)
```

## Review Targets

```bash
glee review src/api/              # Review a directory
glee review src/main.py           # Review a file
glee review git:changes           # Review uncommitted changes
glee review git:staged            # Review staged changes
glee review "the auth module"     # Natural description
```

## Configuration

```yaml
# .glee/config.yml
project:
  id: 550e8400-e29b-41d4-a716-446655440000
  name: my-app
  path: /Users/yumin/ventures/my-app

agents:
  - name: claude-a1b2c3
    command: claude
    role: coder
    domain: [backend, api]
    priority: 1

  - name: codex-d4e5f6
    command: codex
    role: reviewer
    focus: [security, performance]

dispatch:
  coder: first      # first | random | round-robin
  reviewer: all     # all | first | random
```

## How It Works

```
glee init
    ├── Creates .glee/config.yml
    └── Creates .claude/settings.local.json (MCP registration)

claude (start in project)
    └── Reads .claude/settings.local.json
        └── Spawns `glee mcp` as MCP server
            └── Claude now has glee_* tools
```

## Documentation

See [docs/PRD.md](https://github.com/GleeCodeAI/Glee/blob/main/docs/PRD.md) for full documentation.
