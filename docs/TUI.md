# Glee Watch TUI - Product Requirements Document

## Overview

`glee watch` is a Terminal User Interface (TUI) that provides real-time observability and human-in-the-loop control for Glee's multi-agent orchestration. It transforms Glee from a black box into a transparent, controllable system.

Checkpoint policy and autonomy behavior are defined in [Autonomy](Autonomy.md).

## Problem Statement

When AI coding agents (Claude Code, Codex, OpenCode, Gemini) invoke Glee via MCP, the process blocks and users have no visibility into:
- What subagents are doing
- Progress of tasks and reviews
- Intermediate results or decisions
- Ability to intervene, approve, or correct course

Current workaround (`.glee/stream_logs/`) is passive and non-interactive.

## Goals

1. **Observability**: Real-time streaming of all Glee subagent activity
2. **Human-in-the-loop**: Allow humans to intervene at checkpoints (approve/reject/edit)
3. **Control**: Pause, resume, or kill running tasks
4. **Context awareness**: Show active memory, sessions, and agent state

## Non-Goals

- Replacing the agentic capabilities of Claude Code/Codex/Gemini
- Building a chat interface (the main agent handles that)
- Competing with existing agent TUIs

## User Stories

### US1: Monitor Subagent Progress
> As a developer, I want to see what Glee's subagents are doing in real-time, so I'm not staring at a blocked terminal wondering what's happening.

### US2: Approve at Checkpoints
> As a developer, I want to approve or reject subagent outputs at key checkpoints, so I can catch issues before they propagate.

### US3: Intervene Mid-Task
> As a developer, I want to pause or kill a runaway task, so I don't waste time/tokens on a wrong approach.

### US4: Inspect Context
> As a developer, I want to see what memory/context Glee is using for a task, so I can understand and debug agent behavior.

### US5: Multi-Task Awareness
> As a developer, I want to see all active Glee tasks across sessions, so I have a unified view of what's running.

## Architecture

### Current Flow (Black Box)
```
Claude Code → MCP call → Glee → subprocess → ??? → result
     ↑                                              │
     └──────────────── blocks ──────────────────────┘
```

### Proposed Flow (Observable)
```
Claude Code → MCP call → Glee → subprocess
                           │
                           ├──→ Event Bus (SQLite)
                           │         │
                           │         ↓
                           │    glee watch (TUI)
                           │         │
                           │         ↓
                           │    Human Input
                           │         │
                           ←─────────┘
                           │
                           → result (after human approval if needed)
```

### Components

1. **Event Bus**: SQLite-based event queue in `.glee/events.db`
2. **Event Emitter**: Glee core emits events during task/review execution
3. **TUI Process**: `glee watch` - separate process, subscribes to events
4. **Input Handler**: Human responses and control actions flow back through event bus
5. **Checkpoint System**: Defined pause points where human input is required/optional

## Event System Design

### Event Schema
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent TEXT,
    tool TEXT,
    status TEXT NOT NULL,   -- running, suspended, completed, failed, killed
    pid INTEGER,
    pgid INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,  -- 'task_start', 'progress', 'stream', 'checkpoint', 'output', 'error', 'complete'
    agent TEXT,                -- 'codex', 'claude', 'gemini', etc.
    tool TEXT,                 -- 'glee_review', 'glee_task', etc.
    payload JSON,              -- Event-specific data
    acknowledged BOOLEAN DEFAULT FALSE
);

CREATE TABLE human_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL UNIQUE REFERENCES events(id),
    task_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    response_type TEXT NOT NULL,  -- 'approve', 'reject', 'edit'
    payload JSON
);

CREATE TABLE task_controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,  -- 'pause', 'resume', 'kill'
    payload JSON
);

CREATE INDEX idx_events_session_id ON events(session_id);
CREATE INDEX idx_events_task_id ON events(task_id);
CREATE INDEX idx_task_controls_task_id ON task_controls(task_id);
```

### Event Types

| Event Type | Description | Payload |
|------------|-------------|---------|
| `task_start` | Task/review initiated | `{task_id, description, agent}` |
| `progress` | Progress update | `{task_id, message, percent?}` |
| `stream` | Streaming output pointer | `{task_id, log_path, offset, length, source: stdout|stderr}` |
| `checkpoint` | Requires/allows human input | `{task_id, prompt, options, severity}` |
| `output` | Intermediate result | `{task_id, content, type}` |
| `error` | Error occurred | `{task_id, error, recoverable}` |
| `complete` | Task finished | `{task_id, result, status}` |

### Checkpoint Types

Checkpoint types and severity policy are defined in [Autonomy](Autonomy.md). The TUI displays checkpoint state and collects human responses.

## TUI Design

### Layout
```
┌─────────────────────────────────────────────────────────────────────┐
│ GLEE WATCH                                    [P]ause [K]ill [Q]uit │
├─────────────────────────────────────────────────────────────────────┤
│ ACTIVE TASKS                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ● review:abc123  src/api.py           [codex]    ████████░░ 80% │ │
│ │ ○ task:def456    "implement auth"     [gemini]   running...     │ │
│ │ ✓ task:ghi789    "fix types"          [claude]   completed      │ │
│ └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│ LIVE STREAM (review:abc123 - codex)                      [f]ollow  │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Analyzing src/api.py...                                         │ │
│ │ Found 3 functions, 2 classes                                    │ │
│ │ Checking for security issues...                                 │ │
│ │ [!] Potential SQL injection at line 42                          │ │
│ │ [!] Missing input validation at line 67                         │ │
│ │ Generating fix suggestions...                                   │ │
│ │                                                                 │ │
│ │ ──────────────────────────────────────────────────────────────  │ │
│ │ CHECKPOINT: Apply suggested fixes?                              │ │
│ │ [a] Approve all  [r] Reject  [e] Edit  [v] View diff           │ │
│ └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│ MEMORY (session context)                              [m]ore [c]lear│
│ │ architecture: "FastAPI REST, SQLite storage"                     │
│ │ convention: "Use Pydantic for validation"                        │
│ └──────────────────────────────────────────────────────────────────│
└─────────────────────────────────────────────────────────────────────┘
```

### Key Bindings

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate task list |
| `Enter` | Select task to follow |
| `f` | Toggle follow mode (auto-scroll) |
| `a` | Approve (at checkpoint) |
| `r` | Reject (at checkpoint) |
| `e` | Edit (at checkpoint) |
| `v` | View details/diff |
| `p` | Pause selected task |
| `k` | Kill selected task |
| `m` | Expand memory panel |
| `q` | Quit |

### Panels

1. **Header**: Title, global controls, connection status
2. **Task List**: All active/recent tasks with status indicators
3. **Live Stream**: Real-time output from selected task
4. **Checkpoint Banner**: Appears when human input needed
5. **Memory Panel**: Current session context (collapsible)
6. **Status Bar**: Keybindings, notifications

## Implementation Phases

### Phase 1: Event Infrastructure
- [ ] Create `glee/events/` module
- [ ] Implement SQLite event bus (`events.db`)
- [ ] Add event emission to `glee_review` tool
- [ ] Add event emission to `glee_task` tool
- [ ] Basic event cleanup/rotation

### Phase 2: Basic TUI
- [ ] Set up Textual app structure
- [ ] Implement task list panel
- [ ] Implement live stream panel (read-only)
- [ ] Connect to event bus (polling or file watch)
- [ ] Add `glee watch` CLI command

### Phase 3: Human-in-the-Loop
- [ ] Implement checkpoint events in Glee core
- [ ] Add checkpoint UI in TUI
- [ ] Implement response handling (approve/reject)
- [ ] Add suspend-and-return checkpoint support (pending approval)
- [ ] Add edit capability at checkpoints

### Phase 4: Control Features
- [ ] Implement pause/resume
- [ ] Implement kill task
- [ ] Add memory panel
- [ ] Add task detail view
- [ ] Add diff viewer for review results

### Phase 5: Polish
- [ ] Notifications (sound, visual flash)
- [ ] Session history view
- [ ] Export/share task logs
- [ ] Configuration (colors, layout)
- [ ] Documentation and help screen

## Technical Considerations

### Library Choice: Textual
- Modern Python TUI framework
- Async-native (fits well with event streaming)
- Rich widget library
- Good documentation
- Active development

### Event Bus: SQLite
- Already using SQLite for sessions
- Simple, no external dependencies
- WAL mode for concurrent read/write
- Easy to query and debug

### Communication Pattern
```python
# Glee side (emitter)
async def emit_event(event_type: str, payload: dict):
    db.execute(
        "INSERT INTO events (session_id, task_id, event_type, payload) VALUES (?, ?, ?, ?)",
        [current_session_id, current_task_id, event_type, json.dumps(payload)]
    )

# TUI side (subscriber)
async def watch_events():
    last_id = 0
    while True:
        events = db.execute(
            "SELECT * FROM events WHERE id > ? ORDER BY id",
            [last_id]
        ).fetchall()
        for event in events:
            await handle_event(event)
            last_id = event.id
        await asyncio.sleep(0.1)  # Or use file system watcher
```

### Checkpoint Flow
```python
# Glee side
async def checkpoint(prompt: str, options: list, severity: str):
    event_id = emit_event("checkpoint", {
        "task_id": current_task_id,
        "prompt": prompt,
        "options": options,
        "severity": severity
    })
    # Autonomy policy decides whether to suspend; see docs/Autonomy.md.

# TUI side
async def handle_checkpoint(event):
    # Show checkpoint UI
    response = await show_checkpoint_dialog(event.payload)
    # Write response
    db.execute(
        "INSERT INTO human_responses (event_id, task_id, response_type, payload) VALUES (?, ?, ?, ?)",
        [event.id, event.task_id, response.type, json.dumps(response.payload)]
    )
```

### Control Plane (Pause/Resume/Kill)

- Task processes register pid/pgid in `tasks` when they start.
- `glee watch` writes control intents to `task_controls`.
- Glee polls `task_controls` and applies signals to the process group:
  - pause: SIGSTOP
  - resume: SIGCONT
  - kill: SIGTERM, then SIGKILL after timeout
- If a task has no pid/pgid (already finished or unavailable), Glee emits an `error` event.

### Event Storage and Retention

- `stream` events store pointers (log_path, offset, length) instead of raw chunks.
- Raw output stays in `.glee/stream_logs/` and is the source of truth.
- Events and responses are pruned after N days; task summaries can be retained longer.

### Multi-Session Behavior

- TUI shows all tasks in the current project by default (grouped by session_id).
- Filters: session_id, agent, status, task_id.
- The TUI tracks last_id per session to avoid mixing or missing events.

## CLI Interface

```bash
# Watch all sessions in current project
glee watch
```

That's it. One command. Watches everything in `.glee/` for the current project.

## Success Metrics

1. **Observability**: User can see real-time progress of any Glee operation
2. **Latency**: Events appear in TUI within 200ms of emission
3. **Intervention**: User can successfully pause/kill a runaway task
4. **Checkpoint**: Blocking checkpoints work reliably (no race conditions)
5. **Adoption**: Users prefer running `glee watch` alongside their main agent

## Future Vision: Glee Terminal

The ultimate capability is a **Glee Terminal** that controls terminal splitting itself - deciding when to spawn new panes, which agent output goes where, orchestrating the visual layout dynamically.

For now, the TUI mocks multi-screen within a single terminal using Textual's panel system. This gives us:
- Multiple panels (task list, live stream, memory) in one view
- Tab switching between active tasks
- Split views for comparing outputs

This is the stepping stone toward a full terminal orchestrator.

## Design Decisions

1. **Notifications**: Configurable per-event type
   - Terminal bell (works over SSH)
   - Desktop notification (macOS/Linux native)
   - Sound
   - HTTP webhook (Slack, Discord, custom)
   - Email

2. **Persistence**: TUI is just a view, data layer is independent
   - `.glee/stream_logs/` remains the source of truth for raw output
   - Events DB for structured queries
   - Cleanup: rotate logs older than N days

3. **Edit capability**: Simple text input for v1
   - User types feedback/instructions at checkpoint
   - Future: $EDITOR launch, inline diff editing

4. **Remote access**: Works over SSH natively
   - TUI is just terminal output
   - Human-in-the-loop from anywhere

## References

- [Textual Documentation](https://textual.textualize.io/)
- [Rich (Textual's rendering engine)](https://rich.readthedocs.io/)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [Glee Architecture](../CLAUDE.md)
