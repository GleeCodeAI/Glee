# Glee

> The Stage Manager for Your AI Orchestra

An orchestration layer for AI coding agents with shared memory, code review, and subagent orchestration.

## Quick Start

```bash
# Install
uv tool install glee --python 3.13
# or: pipx install glee

# Initialize project (registers MCP server for Claude Code)
glee init

# Configure reviewers
glee config set reviewer.primary codex
glee config set reviewer.secondary gemini

# View status
glee status

# Run review
glee review src/main.py
glee review git:changes          # Review uncommitted changes
glee review git:staged           # Review staged changes
```

## Features

- **MCP Integration**: `glee init` registers Glee as an MCP server - Claude Code gets `glee_*` tools automatically
- **Structured Reviews**: Severity levels (MUST/SHOULD, HIGH/MEDIUM/LOW) for prioritized feedback
- **Reviewer Preferences**: Primary + optional secondary reviewer
- **Persistent Memory**: Project context persists across sessions
- **Stream Logging**: All agent output logged to `.glee/stream_logs/`

## Claude Code Integration

After running `glee init`, restart Claude Code. You'll have these MCP tools:

- `glee_status` - Show project status and reviewer config
- `glee_warmup` - Show session warmup context (goal, constraints, decisions, changes, open loops)
- `glee_summarize_session` - Store a session summary and recent changes in memory
- `glee_review` - Run code review with primary reviewer
- `glee_config_set` - Set config value (e.g., reviewer.primary)
- `glee_config_unset` - Unset config value (e.g., reviewer.secondary)
- `glee_memory_add` - Add a memory entry to a category
- `glee_memory_list` - List memories, optionally filtered by category
- `glee_memory_delete` - Delete memory by ID or category
- `glee_memory_capture` - Capture structured session memory (goal, constraints, decisions, open loops, changes)
- `glee_memory_search` - Semantic search across memories
- `glee_memory_overview` - Memory overview for context
- `glee_memory_stats` - Memory statistics
- `glee_memory_bootstrap` - Bootstrap memory from docs + structure

```
# In Claude Code, you can now say:
"Use glee_review to review the uncommitted changes"
"Set codex as my primary reviewer using glee"
```

## CLI Commands

```bash
glee init                         # Initialize project + register MCP server
glee status                       # Show project status

# Configuration
glee config get                   # Show all config
glee config set reviewer.primary codex
glee config set reviewer.secondary gemini
glee config unset reviewer.secondary

# Review
glee review src/api/              # Review a directory
glee review src/main.py           # Review a file
glee review git:changes           # Review uncommitted changes
glee review git:staged            # Review staged changes

# Agents
glee test-agent codex             # Test an agent
glee mcp                          # Run MCP server (used by Claude Code)
```

## Configuration

```yaml
# .glee/config.yml
project:
  id: 550e8400-e29b-41d4-a716-446655440000
  name: my-app

reviewers:
  primary: codex    # Default reviewer (required)
  secondary: gemini # For second opinions (optional)
```

## How It Works

```
glee init
    ├── Creates .glee/config.yml
    └── Creates .mcp.json (MCP server registration)

claude (start in project)
    └── Reads .mcp.json
        └── Spawns `glee mcp` as MCP server
            └── Claude now has glee_* tools
```

## Documentation

- [docs/VISION.md](docs/VISION.md) - Project vision and design principles
- [docs/PRD.md](docs/PRD.md) - Full product requirements
- [docs/subagents.md](docs/subagents.md) - Subagent orchestration design
- [docs/workflows.md](docs/workflows.md) - Agents & workflows design
- [docs/arbitration.md](docs/arbitration.md) - Review feedback system

## Development

```bash
# Clone the repository
git clone https://github.com/GleeCodeAI/Glee
cd Glee

# Install dev dependencies
uv sync

# Run CLI during development
uv run glee --help
```
