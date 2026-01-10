# Subagent Orchestration Design

## Problem

Different agents have different subagent systems:
- **Claude Code**: `.claude/agents/*.md` (Markdown)
- **Gemini CLI**: `.gemini/agents/*.toml` (TOML)
- **Codex**: no subagent support
- **Cursor, Windsurf, etc.**: varies

**No unified standard.** If you switch main agents, your subagent setup doesn't transfer.

## Solution

Glee becomes the **universal subagent orchestrator** for all AI coding agents.

1. **Own format**: `.glee/agents/*.yml` (YAML)
2. **Import tool**: Convert from Claude/Gemini formats
3. **Run anywhere**: Subagents work with any main agent

```
Main Agent (Claude, Codex, Gemini, Cursor, anything)
    ↓ MCP call: glee_spawn_subagents
Glee
    ├── Reads .glee/agents/*.yml
    ├── Spawns agents in parallel via subprocess
    ├── Logs to .glee/stream_logs/
    └── Returns aggregated results to main agent
```

## Subagent Definition Format

```yaml
# .glee/agents/security-scanner.yml
name: security-scanner
description: Scan code for security vulnerabilities

# Which CLI to use (codex, claude, gemini)
# If not specified, uses first available
agent: codex

# System prompt for the subagent
prompt: |
  You are a security expert. Analyze the given code for:
  - SQL injection
  - XSS vulnerabilities
  - Authentication issues
  - Secrets in code

# Runtime settings
timeout_mins: 5
max_output_kb: 50
```

### Full Schema

```yaml
name: string          # required, lowercase with hyphens
description: string   # required, one-line description
agent: string         # optional: codex | claude | gemini (default: first available)
prompt: string        # required, system prompt

# Source tracking (optional, only for imported agents)
# Native glee agents don't have this field
source:                 # optional
  from: string          # claude | gemini
  file: string          # original file path
  imported_at: string   # ISO timestamp

# Optional runtime settings
timeout_mins: number  # default: 5
max_output_kb: number # default: 100

# Optional input parameters (for templating)
inputs:
  - name: target_file
    type: string
    description: File to analyze
    required: true
  - name: severity
    type: string
    description: Minimum severity to report
    default: "medium"

# Optional: restrict available tools
tools:
  - read_file
  - grep
  - web_search
```

### Prompt Templating

```yaml
prompt: |
  Analyze ${target_file} for security issues.
  Report issues with severity >= ${severity}.
```

## Import from Other Formats

### CLI Commands

```bash
# Import from Claude Code (one-way: claude → glee)
glee agents import --from claude
# Reads .claude/agents/*.md → writes .glee/agents/*.yml

# Import from Gemini CLI (one-way: gemini → glee)
glee agents import --from gemini
# Reads .gemini/agents/*.toml → writes .glee/agents/*.yml

# Import specific file
glee agents import --file .claude/agents/reviewer.md

# Re-import: update from sources (overwrites local changes)
glee agents import --from claude --update

# Dry run: show what would be imported
glee agents import --from claude --dry

# List all agents with source info
glee agents list
# Output:
#   security-scanner    (from: claude, .claude/agents/security-scanner.md)
#   code-reviewer       (from: gemini, .gemini/agents/code-reviewer.toml)
#   my-custom-agent     (native glee)
```

**Note:** Import is one-way only (source → glee). Glee never writes back to `.claude/` or `.gemini/`.

### Format Conversion

**Claude Markdown → Glee YAML:**
```markdown
# Security Reviewer

You are a security expert...

## Tools
- read_file
- grep
```
↓
```yaml
name: security-reviewer
description: Security Reviewer
agent: claude
prompt: |
  You are a security expert...
tools:
  - read_file
  - grep
```

**Gemini TOML → Glee YAML:**
```toml
name = "security-scanner"
description = "Scan for vulnerabilities"

[prompts]
system_prompt = "You are a security expert..."

[run]
timeout_mins = 5
```
↓
```yaml
name: security-scanner
description: Scan for vulnerabilities
agent: gemini
prompt: |
  You are a security expert...
timeout_mins: 5
```

## Current Thinking

> **Note:** This is exploratory. The scope of subagents may expand as we learn more.

For now, subagents are for **small, scoped, parallelizable tasks**.

**Good for subagents (v1):**
- Read multiple files in parallel
- Web searches in parallel
- Run linters/formatters
- Fetch documentation from multiple sources
- Fix typos across files

**Not for subagents:**
- Code review (opinionated, use reviewer preferences)
- Architecture decisions (needs human input)
- Complex refactoring (needs context, iteration)

## MCP Tool Design

### `glee_task`

```python
glee_task(
    description="Find API endpoints",           # Short (3-5 words)
    prompt="Search for all REST endpoints...",  # Full task prompt
    background=False,                           # Run in background (optional)
    session_id=None                             # Resume existing session (optional)
)
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Short task description (3-5 words) |
| `prompt` | string | Yes | Full task prompt for the agent |
| `background` | boolean | No | Run in background, default: false |
| `session_id` | string | No | Resume existing session by ID |

**Returns:**
```json
{
    "session_id": "task-a1b2c3d4",
    "status": "completed",
    "output": "Found 5 endpoints:\n- GET /api/users\n- POST /api/auth...",
    "duration_ms": 3200
}
```

**Resume a session:**
```python
# First call
result = glee_task(
    description="Find endpoints",
    prompt="Search for all REST endpoints in src/"
)
# Returns: { "session_id": "task-a1b2c3d4", ... }

# Follow-up call
result = glee_task(
    session_id="task-a1b2c3d4",
    prompt="Now document each endpoint"
)
# Agent remembers previous context
```

### Agent Selection

If `agent_name` not specified, Glee auto-selects based on:

1. **Availability** - is the CLI installed?
2. **Task type heuristics** - simple keyword matching:

```python
AGENT_HEURISTICS = {
    "gemini": [
        "search web", "google", "find online", "latest", "news",
        "research", "look up", "what is", "documentation"
    ],
    "codex": [
        "analyze code", "review", "find bugs", "refactor",
        "security", "performance", "fix", "debug"
    ],
    "claude": [
        "summarize", "explain", "write", "draft", "quick",
        "simple", "help me understand"
    ]
}

def select_agent(prompt: str) -> str:
    prompt_lower = prompt.lower()
    for agent, keywords in AGENT_HEURISTICS.items():
        if any(kw in prompt_lower for kw in keywords):
            if is_available(agent):
                return agent
    return first_available()
```

3. **Fallback** - first available CLI

Configurable override in `.glee/config.yml`:
```yaml
subagents:
  default_agent: codex  # skip heuristics, always use this
```

## Session Management

CLI agents (codex, claude, gemini) are stateless - each subprocess is fresh. Glee stores conversation history and injects it on resume.

### Session Storage

```
.glee/sessions/
└── task-a1b2c3d4.json
```

```json
{
  "session_id": "task-a1b2c3d4",
  "agent_name": "codex",
  "created_at": "2025-01-09T15:00:00",
  "updated_at": "2025-01-09T15:05:00",
  "status": "completed",
  "messages": [
    {
      "role": "user",
      "content": "Search for all REST endpoints in src/"
    },
    {
      "role": "assistant",
      "content": "Found 5 endpoints:\n- GET /api/users..."
    }
  ]
}
```

### Resume Flow

When `session_id` is provided:

1. Load session from `.glee/sessions/{session_id}.json`
2. Build context from previous messages
3. Inject into new prompt:

```
<previous_conversation>
User: Search for all REST endpoints in src/
Assistant: Found 5 endpoints...
</previous_conversation>

User: Now document each one
```

4. Send full prompt to agent
5. Append new messages to session file

### Limits

- `max_history`: Max messages to include (default: 20)
- `max_context_tokens`: Truncate if context too large (future)
- Session expiry: Auto-delete after 7 days (configurable)

```yaml
# .glee/config.yml
sessions:
  max_history: 20
  expiry_days: 7
```

## CLI Command

```bash
# Test subagent spawning
glee subagent "Read src/main.py and summarize"
glee subagent "Search web for FastAPI middleware" --agent gemini

# Multiple tasks (from file)
glee subagents --file tasks.json
```

## Implementation

### Subprocess Execution

Each subagent runs via subprocess (same as reviewers):

```python
async def spawn_subagent(task: SubagentTask) -> SubagentResult:
    agent = registry.get(task.agent or "codex")

    result = agent.run(
        prompt=task.prompt,
        stream=True,
        on_output=lambda line: log_to_stream(line)
    )

    return SubagentResult(
        output=result.output,
        status="success" if not result.error else "error",
        duration_ms=result.duration_ms
    )
```

### Parallel Execution

```python
async def spawn_subagents(tasks: list[SubagentTask]) -> list[SubagentResult]:
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = [
            loop.run_in_executor(executor, spawn_subagent, task)
            for task in tasks
        ]
        results = await asyncio.gather(*futures)
    return results
```

### Logging

All subagent output goes to `.glee/stream_logs/`:

```
.glee/stream_logs/
├── stdout-20250109.log
├── stderr-20250109.log
└── subagents-20250109.log  # dedicated subagent log
```

Format:
```
[2025-01-09T14:30:00] [subagent:0] [codex] Starting: Read src/api/auth.py...
[2025-01-09T14:30:01] [subagent:0] [codex] Output: The auth flow uses...
[2025-01-09T14:30:01] [subagent:0] [codex] Completed in 3200ms
```

## Resource Limits

| Setting | Default | Description |
|---------|---------|-------------|
| `subagents.max_concurrent` | 10 | Max parallel subagents |
| `subagents.timeout_ms` | 60000 | Timeout per task (ms) |
| `subagents.max_output_kb` | 100 | Truncate output if exceeded |

```bash
# Configure via CLI
glee config set subagents.max_concurrent 20
glee config set subagents.timeout_ms 120000
```

## Error Handling

```json
{
    "task_index": 1,
    "agent": "gemini",
    "status": "error",
    "error": "CLI not installed",
    "output": null,
    "duration_ms": 0
}
```

Errors don't stop other tasks. Main agent decides what to do with partial results.

## Memory Integration

Subagent results can optionally be saved to memory:

```python
glee_spawn_subagents(
    tasks=[...],
    save_to_memory=True,  # default False
    memory_category="subagent-results"
)
```

Useful for caching expensive operations (web searches, large file reads).

## Security Considerations

- Subagents run with same permissions as main agent
- No sandboxing (same as current reviewer execution)
- Prompt injection risk: subagent prompts come from main agent, not user directly
- Rate limiting: respect underlying API rate limits

## Design Decisions

### Subagents don't access Glee memory directly

Subagents are simple - they receive a prompt and return output. They don't call Glee APIs.

**Glee is the manager.** When spawning a subagent, Glee:
1. Reads `AGENTS.md` from project root (if exists)
2. Fetches relevant memories
3. Injects all context into the subagent's prompt

```python
# Glee does this internally:
agents_md = read_file("AGENTS.md")  # Project instructions
memories = glee_memory_search(query=task_description)

full_prompt = f"""
<project_instructions>
{agents_md}
</project_instructions>

<project_context>
{memories}
</project_context>

{user_prompt}
"""
spawn_subagent(prompt=full_prompt)
```

This keeps subagents stateless and simple. They just receive a rich prompt and return output.

### No streaming (MCP limitation)

MCP can't stream stdout/stderr to clients. Same solution as reviewers:
- Output logged to `.glee/stream_logs/stdout-YYYYMMDD.log`
- User can `tail -f` to watch in real-time
- Final result returned when task completes

## Implementation Phases

### Phase 1: glee_task (v0.3)
- [x] Design docs (subagents.md, workflows.md, tools.md)
- [ ] `glee_task` MCP tool - spawn CLI agents (codex, claude, gemini)
- [ ] Session management (generate ID, store context)
- [ ] Context injection (AGENTS.md + memories)
- [ ] Basic logging to `.glee/stream_logs/`

### Phase 2: Tools (v0.4)
- [ ] `.glee/tools/*.yml` format
- [ ] `glee_tool` MCP tool (execute tools)
- [ ] `glee_tool_create` MCP tool (AI creates tools)
- [ ] Built-in tools: web_search, http_request

### Phase 3: Agents (v0.5)
- [ ] `.glee/agents/*.yml` format
- [ ] `glee_agent_create` MCP tool (AI creates agents)
- [ ] `glee agents import` from Claude/Gemini formats
- [ ] Agent selection heuristics

### Phase 4: Workflows (v0.6+)
- [ ] `.glee/workflows/*.yml` format
- [ ] `glee_workflow` MCP tool
- [ ] Nested workflows
- [ ] Parallel/DAG execution
