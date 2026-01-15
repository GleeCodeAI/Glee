# PRD — Glee MCP Agent Runtime

## 1. Product Definition

**Glee MCP Agent Runtime** is a locally-running autonomous agent exposed to LLM tools (Claude Code, Codex, Cursor, etc.) through MCP.

It allows LLMs to **delegate complex, long-running, multi-step work to Glee** instead of executing it inside the model's own context.

> **Delegate work. Save context.**

## 2. The Problem

Coding agents (Claude Code, Codex, Cursor) have limited context windows. When you ask them to do complex work:

1. **Context bloat** — Long tasks fill up the context window
2. **Lost focus** — The model loses track of the original goal
3. **No persistence** — Session ends, context is gone
4. **Single-threaded** — Can't delegate work to run in parallel

## 3. The Solution

Delegate work to Glee. Glee runs in its **own context** using another AI instance.

```
Claude Code (your main agent)
    ↓ glee.job.submit("refactor the auth system")
Glee Agent Runtime (separate context)
    ↓ Uses Codex/Claude API internally
    ↓ Runs autonomously with ReAct loop
    ↓ Can use tools, read files, search code
    ↓ Returns result when done
Claude Code gets result (its context stayed clean)
```

## 4. Core Goals

| Goal | Description |
|------|-------------|
| **Decouple long work from model context** | Main agent stays focused, Glee does the heavy lifting |
| **Support long-running jobs** | Tasks that take minutes, not seconds |
| **Enable agentic execution** | ReAct loop: Reason → Act → Observe |
| **Support human-in-the-loop** | Glee can ask for input when stuck |

## 5. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                              │
│                    (user's main agent)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP Protocol
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Glee MCP Server                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  MCP Tools: glee.job.submit, glee.job.get, glee.job.wait  │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────┴─────────────────────────────────┐ │
│  │                   Glee Agent Runtime                        │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │ │
│  │  │ ReAct Loop  │  │   Memory    │  │   Tool Executor     │ │ │
│  │  │ (Reason →   │  │ (LanceDB +  │  │ (HTTP, Command,     │ │ │
│  │  │  Act →      │  │  DuckDB)    │  │  Python)            │ │ │
│  │  │  Observe)   │  │             │  │                     │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │ AI Provider (for reasoning)
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌────────────┐    ┌────────────┐    ┌────────────┐
     │ Codex API  │    │ Claude API │    │ CLI Fallback│
     │ (OAuth)    │    │ (API Key)  │    │ (codex cli) │
     └────────────┘    └────────────┘    └────────────┘
```

## 6. API Design

All MCP tools live under one namespace: `glee.job.*`

### Required Tools

| Tool | Description |
|------|-------------|
| `glee.job.submit` | Submit a task, returns job_id |
| `glee.job.get` | Get job status and progress |
| `glee.job.wait` | Block until job completes |
| `glee.job.result` | Get final result of completed job |
| `glee.job.needs_input` | Check if any job needs human input |
| `glee.job.provide_input` | Provide input to a waiting job |
| `glee.job.latest` | Get most recent job |

### Optional Tools

| Tool | Description |
|------|-------------|
| `glee.job.list` | List all jobs |
| `glee.job.cancel` | Cancel a running job |

### Example Usage

```python
# Claude Code submits a job
job_id = glee.job.submit(
    task="Refactor the authentication system to use JWT tokens",
    context=["src/auth/", "src/middleware/"]
)

# Check status
status = glee.job.get(job_id)
# → {"status": "running", "progress": "Analyzing auth module..."}

# Wait for completion
result = glee.job.wait(job_id)
# → {"status": "completed", "result": "...", "files_changed": [...]}

# Or check if human input is needed
if glee.job.needs_input():
    question = glee.job.get(job_id)["question"]
    # → "Should I also update the session management? (yes/no)"
    glee.job.provide_input(job_id, "yes")
```

## 7. ReAct Agent Loop

Glee uses the ReAct pattern internally:

```
while not done:
    # REASON: What should I do next?
    thought = llm.think(task, history, context)

    # DECIDE: What action to take?
    action = llm.decide(thought)

    # ACT: Execute the action
    if action.type == "tool":
        result = execute_tool(action.tool, action.params)
    elif action.type == "ask_human":
        result = wait_for_human_input(action.question)
    elif action.type == "finish":
        return action.result

    # OBSERVE: Record what happened
    history.append({thought, action, result})
```

### Available Actions

| Action | Description |
|--------|-------------|
| `read_file` | Read a file's contents |
| `write_file` | Write/edit a file |
| `search_code` | Search codebase with grep/glob |
| `run_command` | Execute shell command |
| `use_tool` | Call a registered tool |
| `ask_human` | Request human input |
| `finish` | Complete the task |

## 8. AI Provider Selection

Glee needs an AI to power its reasoning. Priority order:

| Priority | Provider | Auth Method |
|----------|----------|-------------|
| 1 | Codex API | OAuth (PKCE flow) |
| 2 | GitHub Copilot API | OAuth (device flow) |
| 3 | Claude API | API key |
| 4 | Gemini API | API key |
| 5 | CLI Fallback | codex/claude/gemini CLI |

### Auth Storage

```yaml
# ~/.glee/auth.yml
codex:
  method: oauth
  access_token: "..."
  refresh_token: "..."
  expires_at: 1736956800

claude:
  method: api_key
  api_key: "sk-ant-..."
```

### CLI Commands

```bash
glee oauth codex        # PKCE flow, opens browser
glee oauth copilot      # Device flow, shows code
glee auth claude <key>  # Set API key
glee auth status        # Show configured providers
```

## 9. Job States

```
┌─────────┐     ┌─────────┐     ┌───────────┐     ┌───────────┐
│ pending │ ──▶ │ running │ ──▶ │ completed │     │ cancelled │
└─────────┘     └────┬────┘     └───────────┘     └───────────┘
                     │                ▲
                     ▼                │
              ┌─────────────┐         │
              │ needs_input │ ────────┘
              └─────────────┘
```

| State | Description |
|-------|-------------|
| `pending` | Job submitted, waiting to start |
| `running` | Job is executing |
| `needs_input` | Job is waiting for human input |
| `completed` | Job finished successfully |
| `failed` | Job encountered an error |
| `cancelled` | Job was cancelled |

## 10. Existing Features (Preserved)

Glee already has these features which remain available:

### Memory System
- `glee.memory.add` — Add memory entry
- `glee.memory.search` — Semantic search
- `glee.memory.overview` — Project overview
- Session hooks for warmup/summarization

### Code Review
- `glee.review` — Run code review with configured reviewer
- Primary/secondary reviewer preferences
- Structured feedback with severity levels

### Status & Config
- `glee.status` — Show project status
- `glee.config.set/unset` — Configuration management

## 11. Implementation Phases

### Phase 1: Auth & Provider Setup
- [ ] OAuth for Codex (PKCE flow)
- [ ] OAuth for GitHub Copilot (device flow)
- [ ] API key storage for Claude/Gemini
- [ ] Provider selection logic
- [ ] CLI commands: `glee oauth`, `glee auth`

### Phase 2: Agent Runtime
- [ ] ReAct loop implementation
- [ ] Job state management
- [ ] Basic actions (read, write, search)
- [ ] Human-in-the-loop support

### Phase 3: MCP Integration
- [ ] `glee.job.submit` tool
- [ ] `glee.job.get/wait/result` tools
- [ ] `glee.job.needs_input/provide_input` tools
- [ ] Job persistence across restarts

### Phase 4: Tools Integration
- [ ] Tool manifest format (`.glee/tools/`)
- [ ] HTTP, Command, Python tool types
- [ ] Tool execution in agent loop

## 12. Success Metrics

| Metric | Target |
|--------|--------|
| Context savings | 50%+ reduction in main agent context usage |
| Job completion | 80%+ of jobs complete without human intervention |
| Time to result | Complex tasks complete in < 5 minutes |
| Human-in-loop | Questions are clear and actionable |

## 13. Full Feature Set

### MCP Tool Namespaces

| Namespace | Purpose | Status |
|-----------|---------|--------|
| `glee.job.*` | Delegate autonomous work | Planned |
| `glee.review` | Code review | Existing |
| `glee.rag.*` | Cross-project knowledge base | Planned |
| `glee.memory.*` | Project memory | Existing |
| `glee.config.*` | Configuration | Existing |

### Supporting Infrastructure

| Component | Purpose | Status |
|-----------|---------|--------|
| **agents** | Reusable workers (`.glee/agents/*.yml`) | Partial |
| **tools** | Extensible capabilities (`.glee/tools/`) | Planned |
| **workflows** | Orchestration of agents | Planned |

### Future Features

| Feature | Description |
|---------|-------------|
| GitHub integration | PR reviews, issue tracking |
| Team features | Multi-user collaboration |
| Web dashboard | Visualization, monitoring |

## 14. Non-Goals

- **Not an account manager** — Auth is just for powering the agent
- **Not a proxy** — Glee doesn't route requests to multiple providers
- **Not a cost optimizer** — Focus is on capability, not cost savings

---

*Glee: Delegate work, save context, get results.*
