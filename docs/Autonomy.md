# Autonomy

## Overview

Autonomy is a spectrum that controls how Glee handles checkpoints and approvals. UI surfaces like `glee watch` are optional and do not change decision policy. The autonomy level determines whether a checkpoint suspends or auto-continues.

## Roles

```
Human      = Conductor (directs, decides) or delegates
Main Agent = Principal musician (does the work)
Subagents  = Session musicians (called in as needed)
Glee       = Stage manager (logistics, coordination, memory)
```

## Autonomy Levels

| Level        | Who Decides                                 | Best For                    |
| ------------ | ------------------------------------------- | --------------------------- |
| `hitl`       | Human approves every step                   | Control freaks, learning or debugging |
| `supervised` | AI suggests, human approves major decisions | Most engineers (default)    |
| `autonomous` | AI drives, human reviews at end             | Vibe coders, busy engineers |
| `yolo`       | AI drives, no human intervention            | Sleep mode, batch changes   |

## Checkpoint Severity

- Every checkpoint must declare a severity: `low`, `medium`, `high`, `critical`.
- Severity drives whether the checkpoint suspends or auto-continues.

## Checkpoint Types

- Blocking checkpoint: suspend and wait for human response before continuing.
- Non-blocking checkpoint: continue automatically, with the option to intervene.

Blocking vs non-blocking is determined by autonomy policy.

## Default Checkpoint Policy

| Level        | low | medium | high | critical |
| ------------ | --- | ------ | ---- | -------- |
| `hitl`       | suspend | suspend | suspend | suspend |
| `supervised` | auto | auto | suspend | suspend |
| `autonomous` | auto | auto | auto | suspend |
| `yolo`       | auto | auto | auto | auto |

## Policy Resolution Order

1. Autonomy level default
2. `checkpoint_policy` overrides (if configured)
3. `require_approval_for` overrides (force suspend)

Rules:
- `require_approval_for` always overrides autonomy (forces suspend)
- checkpoints without severity are invalid

## Execution Semantics (Suspend-and-Return)

If policy says auto-continue, Glee proceeds immediately.

If policy says suspend:
- Mark the task as `suspended`
- Return immediately to the caller:
  `{status: "pending_approval", task_id, checkpoint_id}`
- Resume when a response arrives (TUI or CLI)

Approvals can be recorded by:
- `glee watch` (TUI)
- a CLI command (e.g., `glee approve <task_id>`)

## Configuration Example

```yaml
autonomy:
  level: supervised # hitl | supervised | autonomous | yolo
  checkpoint_policy:
    low: auto
    medium: auto
    high: suspend
    critical: suspend
  require_approval_for:
    - commit
    - deploy
    - delete
```

## Guardrails (All Levels)

- Always show what AI is doing (transparency)
- Never auto-commit or deploy without explicit config
- Log all decisions for audit

## Observability

- Stream logs to `.glee/stream_logs/` for transparency
- `glee watch` provides live visibility when needed

## Related Docs

- `docs/TUI.md` for the TUI design and event bus
