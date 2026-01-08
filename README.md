# Glee

> The Conductor for Your AI Orchestra

An orchestration layer for AI coding agents with shared memory, context injection, and multi-agent collaboration.

## Quick Start

```bash
# Install
uv sync

# Initialize project
uv run glee init

# Connect agents
uv run glee connect claude --role coder --domain backend,api
uv run glee connect codex --role reviewer --focus security,performance

# View status
uv run glee status

# Run review
uv run glee review src/main.py
```

## Features

- **Multiple Coders**: Different agents for different domains (backend, frontend, infra)
- **Multiple Reviewers**: Get diverse perspectives (security, performance, architecture)
- **Parallel Execution**: Reviews run concurrently for speed
- **Unique Agent IDs**: Each connected agent gets a unique name like `claude-a1b2c3`

## CLI Commands

```bash
glee init                    # Initialize .glee/config.yml
glee connect <cmd> --role <role>  # Connect an agent
glee disconnect <name>       # Disconnect an agent
glee status                  # Show project status
glee agents                  # List available agents
glee review [files...]       # Run multi-reviewer workflow
glee test-agent <cmd>        # Test an agent
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

## Documentation

See [docs/PRD.md](docs/PRD.md) for full documentation.
