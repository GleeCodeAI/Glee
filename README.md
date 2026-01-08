# Glee

> Multi-Agent Code Collaboration Platform

Multiple AIs working together like a Glee Club, making coding joyful.

## Quick Start

```bash
# Install with uv
uv sync

# Test help
uv run python -m glee --help
```

## Configure Claude Code

Add to `.claude/settings.local.json` (per-project) or `~/.claude/settings.json` (global):

```json
{
  "mcpServers": {
    "glee": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/clean-code-agent", "python", "-m", "glee"]
    }
  },
  "customSlashCommands": {
    "glee-review": {
      "description": "Start a code review using Codex",
      "prompt": "Call mcp__glee__start_review to get a code review from Codex. Based on the feedback, fix any issues and call the tool again until status is 'approved' or 'max_iterations'."
    }
  },
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "If code was modified (Edit/Write tools were used), ask the user: 'Do you want me to run a Codex review?' If they say yes, call mcp__glee__start_review."
          }
        ]
      }
    ]
  }
}
```

## Docker (Recommended for Windows/Server)

```bash
# Start with Docker Compose
docker compose up -d
```

Configure Claude Code to connect via SSE:

```json
{
  "mcpServers": {
    "glee": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

## Usage

### Manual trigger
```
/glee-review
```

### Auto prompt
After each response with code changes, Claude will ask if you want a Codex review.

## MCP Tools

- `start_review` - Start a code review session using Codex
- `continue_review` - Continue review after human input
- `get_review_status` - Check review status

## Documentation

See [docs/PRD.md](docs/PRD.md) for full documentation.
