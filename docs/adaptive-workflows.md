# Adaptive Workflows

## Core Thesis

**Memory is the foundation. Everything else is built on top.**

Everyone is building agents. Few are building memory. Workflows without memory are just scripts. Workflows *with* memory are learning systems.

## Two Modes: Choose Your Style

Glee supports **both** imperative and adaptive workflows. They coexist.

| Mode | File | When to Use |
|------|------|-------------|
| Imperative | [workflows.md](workflows.md) | Predictable, auditable, deterministic |
| Adaptive | (this doc) | Learning, improvisation, goal-driven |

**Why both?**

- Compliance/audit → need to prove exact steps were followed
- CI/CD pipelines → predictable, debuggable
- Onboarding → new users want to see what happens
- Creative tasks → AI can improvise based on context
- Complex debugging → situation-dependent approach
- Long-term optimization → memory compounds over time

```yaml
# Imperative: I tell you exactly what to do
type: imperative
steps:
  - agent: lint
  - agent: test
  - agent: review

# Adaptive: I tell you what I want, you figure it out
type: adaptive
goal: "Ensure code quality"
memory:
  consult: true
```

Users pick the right tool for the job. Some workflows are imperative, some are adaptive, some are hybrid.

```
┌─────────────────────────────────────────────────┐
│              Adaptive Workflows                 │
│    (intent-based, guardrails, learning)         │
├─────────────────────────────────────────────────┤
│                  Memory Layer                   │
│                                                 │
│   LanceDB (vector)      DuckDB (structured)     │
│        ↓                       ↓                │
│   "Find similar          "What patterns        │
│    past situations"       emerge over time?"   │
└─────────────────────────────────────────────────┘
```

This is why Glee exists.

## The Memory Architecture

### Two Stores, Two Purposes

| Store | Type | Purpose | Example Query |
|-------|------|---------|---------------|
| LanceDB | Vector | Semantic similarity | "Find past reviews of auth code" |
| DuckDB | SQL | Structured analytics | "What % of security fixes regressed?" |

Together they enable:

1. **Pattern recognition** — "I've seen this before"
2. **Outcome tracking** — "That approach failed last time"
3. **Preference learning** — "This user rejects verbose feedback"
4. **Codebase knowledge** — "This module is fragile, be careful"

### Memory Types

```yaml
# Semantic memories (LanceDB)
- type: experience
  content: "Auth refactor broke session handling"
  embedding: [0.23, -0.45, ...]

- type: decision
  content: "User prefers minimal comments"
  embedding: [0.12, 0.67, ...]

- type: pattern
  content: "Files in src/api/ often have missing error handling"
  embedding: [-0.34, 0.22, ...]

# Structured memories (DuckDB)
- workflow_runs: outcome, duration, agents_used, files_touched
- feedback_events: accepted, rejected, reason
- error_patterns: file, error_type, root_cause, fix_applied
```

### Memory-Driven Execution

Every workflow execution follows this pattern:

```
1. RECALL
   ├── Semantic search: "What's relevant to this task?"
   ├── SQL query: "What patterns exist for this file/module?"
   └── Result: Context for the orchestrator

2. EXECUTE
   ├── Orchestrator uses recalled context
   ├── Makes decisions based on past outcomes
   └── Adapts approach based on learned preferences

3. REMEMBER
   ├── Store outcome (success/failure/partial)
   ├── Store decisions made and why
   ├── Store feedback received
   └── Update pattern statistics
```

## The Problem with Traditional Workflows

Traditional workflows are rigid and deterministic:

| Traditional Workflows | What Glee Needs |
|----------------------|-----------------|
| Rigid steps | Adaptive behavior |
| Deterministic | Context-aware |
| Manual updates | Self-evolving |
| Code/YAML defined | Goal-driven |
| Imperative | **Declarative** |
| Stateless | **Memory-backed** |

When business logic is dynamic, you constantly update workflow definitions. This doesn't scale.

## Design Principle: Declarative, Not Imperative

**Imperative** (what we want to avoid):
```yaml
steps:
  - run: lint
  - run: test
  - run: review
```

**Declarative** (what we want):
```yaml
goal: "Ensure code quality before merge"
constraints:
  - must pass tests
  - must have review approval
hints:
  - prefer fast feedback loops
memory:
  consult: true  # <-- This is what makes it adaptive
```

The AI decides *how* to achieve the goal, informed by what it remembers.

## Three Layers (All Memory-Backed)

### Layer 1: Intent

Define goals and success criteria, not steps.

```yaml
# .glee/workflows/code-quality.yml
name: code-quality
type: intent

goal: "Ensure production-ready code"

success_criteria:
  - no critical security vulnerabilities
  - test coverage >= 80%
  - no type errors
  - approved by reviewer

constraints:
  - do not modify production data
  - do not push to main directly

# Memory integration
memory:
  before_run:
    - query: "past failures for files like {target}"
    - query: "known issues in {module}"
  after_run:
    - store: outcome
    - store: which checks failed and why
```

The orchestrating agent interprets the goal, consults memory, and decides which agents to invoke.

### Layer 2: Guardrails

Define boundaries and checkpoints, not execution paths.

```yaml
# .glee/workflows/deploy.yml
name: deploy
type: guardrails

checkpoints:
  - name: pre-deploy
    requires: human_approval
    message: "Ready to deploy to {environment}?"

  - name: post-deploy
    requires: health_check
    rollback_on_failure: true

boundaries:
  allowed_actions:
    - read any file
    - modify files in src/
    - run tests
    - deploy to staging

  forbidden_actions:
    - delete production data
    - modify .env files
    - push to main without PR

# Memory integration
memory:
  before_run:
    - query: "past deploy failures to {environment}"
    - query: "rollback history"
  after_run:
    - store: deploy outcome
    - store: any incidents triggered
```

The AI operates freely within boundaries, but learns from past deploys.

### Layer 3: Learning

Explicit feedback loops that compound over time.

```yaml
# .glee/workflows/review.yml
name: review
type: learning

goal: "Provide high-quality code review"

# What to remember
on_completion:
  remember:
    - what feedback was accepted
    - what feedback was rejected
    - what issues were missed (found later)

on_failure:
  remember:
    - what went wrong
    - root cause if identified

# How to adapt
adaptation:
  consult:
    - past failures in similar files
    - reviewer preferences (accepted/rejected patterns)
    - common issues in this codebase

  adjust:
    - if feedback often rejected → be more concise
    - if issues often missed → check related patterns
    - if certain agents fail often → try alternatives
```

This is where the magic happens. Over time:
- Review quality improves
- False positives decrease
- The system learns the codebase

## Hybrid: Combining All Three Layers

Real workflows combine intent, guardrails, and learning:

```yaml
# .glee/workflows/feature-development.yml
name: feature-development
type: hybrid

# Layer 1: Intent
goal: "Implement feature according to spec"
success_criteria:
  - feature works as specified
  - tests pass
  - code reviewed

# Layer 2: Guardrails
checkpoints:
  - name: design-review
    requires: human_approval
    when: before_implementation

  - name: merge-approval
    requires: human_approval
    when: before_merge

boundaries:
  forbidden_actions:
    - modify unrelated files
    - change public API without approval

# Layer 3: Learning
memory:
  before_run:
    - query: "similar features implemented before"
    - query: "common pitfalls in {module}"
    - query: "user preferences for code style"

  after_run:
    - store: implementation approach taken
    - store: review feedback received
    - store: any rework required

  learn:
    - which design patterns worked
    - which tests caught real bugs
    - what reviewer feedback was given
```

## The Feedback Loop

This is what makes Glee different:

```
     ┌──────────────────────────────────────┐
     │                                      │
     ▼                                      │
  WORKFLOW                                  │
  EXECUTION ──────► OUTCOME ──────► MEMORY ─┘
     │                                 │
     │                                 │
     └─── recalls ◄────────────────────┘
```

Every run makes the next run better. This compounds.

### Example: Code Review Evolution

**Week 1:**
```
Memory: (empty)
Behavior: Generic review, many false positives
Feedback: User rejects 60% of suggestions
```

**Week 4:**
```
Memory:
  - "User prefers functional style"
  - "Security issues in auth/ are critical"
  - "Don't flag missing docs in internal utils"

Behavior: Targeted review, fewer false positives
Feedback: User rejects 20% of suggestions
```

**Week 12:**
```
Memory:
  - Codebase patterns fully mapped
  - User preferences well understood
  - Known trouble spots identified

Behavior: Review feels like a senior teammate
Feedback: User rejects <5% of suggestions
```

## Memory Queries in Practice

### Semantic Queries (LanceDB)

```python
# Before reviewing auth code
glee_memory_search(
    query="past reviews of authentication code",
    limit=5
)
# Returns: similar past experiences, what worked/failed

# Before implementing a feature
glee_memory_search(
    query="how was caching implemented in this codebase",
    limit=3
)
# Returns: past implementation patterns
```

### Analytical Queries (DuckDB)

```sql
-- What's the acceptance rate for security feedback?
SELECT
    feedback_type,
    COUNT(*) as total,
    SUM(CASE WHEN accepted THEN 1 ELSE 0 END) as accepted,
    ROUND(100.0 * SUM(CASE WHEN accepted THEN 1 ELSE 0 END) / COUNT(*), 1) as rate
FROM feedback_events
WHERE category = 'security'
GROUP BY feedback_type;

-- Which files have the most rework?
SELECT
    file_path,
    COUNT(*) as times_modified,
    AVG(rework_cycles) as avg_rework
FROM workflow_runs
WHERE outcome = 'required_rework'
GROUP BY file_path
ORDER BY times_modified DESC
LIMIT 10;
```

## Implementation

### Execution Model

```
User Request
    ↓
Workflow Definition (declarative)
    ↓
Memory Recall (semantic + structured)
    ↓
Orchestrator Agent (interprets intent + context)
    ↓
Agent Invocations (dynamic, informed by memory)
    ↓
Result
    ↓
Memory Store (outcome, decisions, feedback)
```

### Memory Integration Points

| Phase | Memory Operation | Store |
|-------|------------------|-------|
| Before run | Semantic search for similar situations | LanceDB |
| Before run | Query patterns and statistics | DuckDB |
| During run | Log decisions and reasoning | Stream logs |
| After run | Store outcome | DuckDB |
| After run | Store experience embedding | LanceDB |
| On feedback | Update acceptance/rejection | DuckDB |

### Observability

```
.glee/stream_logs/
└── workflow-feature-development-20250111.log
    ├── memory_recalled: [...]
    ├── goal: "Implement feature according to spec"
    ├── orchestrator_reasoning: "Based on past similar features..."
    ├── agent_invocations: [...]
    ├── checkpoint_approvals: [...]
    ├── outcome: success | failure | partial
    └── memories_stored: [...]
```

## Key Insight

**Workflows are not scripts. They are learning systems.**

The difference:

| Scripts | Learning Systems |
|---------|------------------|
| Same behavior every time | Improves over time |
| Manual updates required | Self-adapting |
| No memory of past runs | Compounds experience |
| Generic | Personalized to codebase + user |

Glee's value is the memory layer. Workflows are just the interface to it.

## Open Questions

1. How do we measure if a goal is "achieved"? (success criteria evaluation)
2. How do we prevent memory from becoming stale or misleading?
3. How do we handle conflicting memories?
4. What's the right retention policy for memories?
5. How do we explain "why" the system made a decision? (memory attribution)

## Related Docs

- [memory.md](memory.md) — Memory system architecture
- [workflows.md](workflows.md) — Traditional workflow format (imperative)
- [subagents.md](subagents.md) — Agent definitions
