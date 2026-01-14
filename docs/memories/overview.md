# Overview Memory

The overview memory is a comprehensive project summary stored in Glee's memory system. It provides Claude with context about the project's architecture, conventions, dependencies, and technical decisions.

## How It Works

Overview memory is stored in the `overview` category as a single, comprehensive entry. This design allows for atomic refresh - when the project evolves, the entire overview can be replaced without affecting other memories.

## Usage

### MCP Tool: `glee_memory_overview`

**Read existing overview:**
```
glee_memory_overview()
```

**Generate/update overview:**
```
glee_memory_overview(generate=true)
```

When `generate=true`:
1. Clears existing overview memory
2. Gathers project documentation (README.md, CLAUDE.md, etc.)
3. Gathers package configuration (pyproject.toml, package.json, etc.)
4. Generates directory tree structure
5. Returns all content with instructions for Claude to analyze and store

Claude then calls `glee_memory_add(category="overview", content="...")` to save the comprehensive summary.

### CLI Command: `glee memory overview`

**Read existing overview:**
```bash
$ glee memory overview
Last updated: 3 days ago

# Project Overview
Glee is an orchestration layer for AI coding agents...
```

**Generate/update overview:**
```bash
$ glee memory overview --generate
# or
$ glee memory overview -g

# Specify agent:
$ glee memory overview --generate --agent codex
$ glee memory overview -g -a gemini
```

The `--generate` flag:
1. Auto-detects an available AI agent (claude, codex, gemini) or uses the one specified with `--agent`
2. Gathers project documentation and structure
3. Sends to the AI for analysis
4. Saves the generated overview to memory

If no overview exists:
```bash
$ glee memory overview
No overview memory found.
Run: glee memory overview --generate
```

## Staleness

Overview memory can become outdated as the project evolves. Glee tracks this with:

- **Staleness threshold**: 7 days (configurable via `BOOTSTRAP_STALE_DAYS` in `warmup.py`)
- **Automatic warning**: When overview is stale, warnings appear in:
  - Session warmup context (for Claude)
  - CLI output (for humans)
  - MCP tool response (for Claude)

### Warning Messages

**For Claude (in warmup/MCP):**
```
Warning: Overview memory is 14 days old. Run `glee_memory_overview(generate=true)` to update it.
```

**For humans (CLI):**
```
Stale - run: glee memory overview --generate
```

## Session Warmup

At session start, the overview memory is injected into Claude's context under "## Project Context". This gives Claude immediate understanding of the project without needing to explore the codebase.

Example warmup output:
```markdown
# Glee Warmup

## Last Session
- session_abc (completed, 2024-01-14 10:30): Implemented auth feature

## Project Context
# Project Overview
Glee is an orchestration layer for AI coding agents...

## Architecture
- CLI built with Typer
- MCP server for Claude Code integration
...

## Current Goal
Build the user authentication system

## Key Constraints
- Must use OAuth2
```

## Best Practices

1. **Generate overview early**: Run `glee memory overview --generate` when starting a new project with Glee

2. **Refresh regularly**: Update the overview when:
   - Major architectural changes occur
   - New key dependencies are added
   - The staleness warning appears

3. **Keep it comprehensive but concise**: The overview should cover:
   - Architecture and module organization
   - Coding conventions and patterns
   - Key dependencies and their purposes
   - Notable technical decisions

4. **Don't duplicate**: Use other memory categories for specific items:
   - `constraint` - for rules that must be followed
   - `decision` - for individual technical decisions
   - `goal` - for current project goals

## Storage

- **Category**: `overview`
- **Location**: `.glee/memory.lance/` (LanceDB) and `.glee/memory.duckdb` (DuckDB)
- **Entries**: Single comprehensive entry (not scattered across multiple entries)
