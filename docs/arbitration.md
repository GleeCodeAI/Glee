# Arbitration System Design

## Overview

Glee's arbitration system handles disagreements between coder and reviewer agents. It introduces a **judge** role and **severity levels** to ensure code quality while giving users control over dispute resolution.

## Roles

| Role | Purpose | Example Agents |
|------|---------|----------------|
| Coder | Writes and modifies code | Claude Code |
| Reviewer | Reviews code, identifies issues | Codex, Gemini |
| Judge | Arbitrates disputes between coder and reviewer | Claude (fresh instance) |

The judge only intervenes when there is a dispute. It does not participate in the standard review flow.

## Review Severity Levels

### Opinion Levels

| Level | Meaning | Mandatory? | Coder Can Discard? |
|-------|---------|------------|-------------------|
| MUST | Required change | Yes | No |
| SHOULD | Recommended change | No | Yes |

### Issue Priority Levels

| Level | Meaning | Mandatory? | Coder Can Discard? |
|-------|---------|------------|-------------------|
| HIGH | Critical issue | Yes | No |
| MEDIUM | Moderate issue | No | Yes |
| LOW | Minor issue | No | Yes |

## Review Output Format

Reviewers must structure their feedback using severity tags:

```
[MUST] Fix SQL injection vulnerability in query builder
[MUST] Add authentication check before accessing user data
[HIGH] Memory leak in connection pool - objects never released
[SHOULD] Consider using async/await for I/O operations
[MEDIUM] Function exceeds 50 lines, consider splitting
[LOW] Variable 'x' could have more descriptive name
```

## Coder Prompt Guidelines

When invoking the coder to process review feedback, use a prompt that discourages ego and encourages collaboration:

```
You received the following review feedback on your code:

{review_items}

Instructions:
- Default stance: the reviewer is probably right. Accept and implement all valid feedback.
- Do NOT disagree unless there is a clear, objective technical reason.

Valid reasons to disagree:
- Factual error in the review (reviewer misread the code)
- Suggestion would break existing functionality
- Suggestion conflicts with explicit project requirements
- Reviewer misunderstood the context or intent

Invalid reasons to disagree:
- Personal preference or style
- "I think my way is better"
- Minor differences that don't affect correctness
- Ego or defensiveness

If you disagree with a MUST or HIGH item:
- You MUST provide specific technical justification
- Cite concrete evidence (code references, requirements, tests)
- Be objective, not defensive

Remember: You are a collaborative agent, not a defender of your code.
Reviewers help improve code quality. Embrace their feedback.
```

## Workflow

### Standard Flow (No Dispute)

```
Coder writes code
       ↓
Reviewer analyzes code
       ↓
Reviewer returns structured feedback
       ↓
Coder processes feedback:
  - MUST/HIGH items → implement changes
  - SHOULD/MEDIUM/LOW items → implement or discard
       ↓
Done
```

### Dispute Flow

A dispute occurs when the coder disagrees with a **mandatory** item (MUST or HIGH).

**With judge configured:**
```
Coder disagrees with MUST or HIGH item
              ↓
     ┌────────────────────────┐
     │   How to resolve?      │
     │                        │
     │   1. Use AI judge      │
     │   2. I'll decide       │
     │   3. Discard opinion   │
     └────────────────────────┘
              ↓
        User selects
              ↓
     Execute chosen path
```

**Without judge configured:**
```
Coder disagrees with MUST or HIGH item
              ↓
     ┌────────────────────────┐
     │   How to resolve?      │
     │                        │
     │   1. I'll decide       │
     │   2. Discard opinion   │
     │                        │
     │   (yellow) Tip: You    │
     │   can assign a judge   │
     │   with: glee connect   │
     │   <agent> --role judge │
     └────────────────────────┘
              ↓
        User selects
              ↓
     Execute chosen path
```

### Judge Arbitration

When the user selects "Use AI judge":

1. Judge receives:
   - Original code
   - Reviewer's feedback (the disputed item)
   - Coder's objection and reasoning

2. Judge evaluates:
   - Is the review valid and applicable?
   - Is the coder's objection reasonable?
   - What is the best path forward?

3. Judge decides:
   - **ENFORCE** - Coder must implement the review
   - **DISMISS** - Review is invalid, coder continues
   - **ESCALATE** - Ambiguous case, needs human decision

## Configuration

```yaml
# .glee/config.yml

agents:
  - name: claude-coder
    command: claude
    role: coder

  - name: codex-reviewer
    command: codex
    role: reviewer

  - name: claude-judge
    command: claude
    role: judge

review:
  # Opinions: reviewer's recommendations on code changes
  opinions:
    mandatory: [MUST]
    optional: [SHOULD]

  # Issues: identified problems in the code
  issues:
    mandatory: [HIGH]
    optional: [MEDIUM, LOW]

  on_dispute:
    prompt_user: true    # show selection to user
    default: judge       # default option: judge | human | discard

  judge:
    escalate_to: human   # fallback when judge is uncertain
```

## Data Flow

```
┌─────────┐    code     ┌──────────┐   structured   ┌─────────┐
│  Coder  │ ──────────► │ Reviewer │ ──────────────►│  Coder  │
└─────────┘             └──────────┘    review      └─────────┘
                                                         │
                                            [disagrees with MUST/HIGH]
                                                         ▼
                                                  ┌─────────────┐
                                                  │ User Prompt │
                                                  └─────────────┘
                                                    │    │    │
                                         ┌──────────┘    │    └──────────┐
                                         ▼               ▼               ▼
                                    ┌─────────┐    ┌─────────┐    ┌─────────┐
                                    │  Judge  │    │  Human  │    │ Discard │
                                    └─────────┘    └─────────┘    └─────────┘
                                         │               │
                                         ▼               ▼
                                    ┌─────────────────────────┐
                                    │ ENFORCE | DISMISS | ... │
                                    └─────────────────────────┘
```

## CLI Commands

```bash
# Review with arbitration enabled
glee review src/ --arbitrate

# Configure dispute handling
glee config set review.on_dispute.default judge

# View dispute history
glee disputes --recent 10
```

## Implementation Phases

### Phase 1: Review Format
- Define structured review output format
- Parse severity levels from reviewer output
- Categorize items as mandatory vs optional

### Phase 2: Dispute Detection
- Detect when coder disagrees with mandatory items
- Capture coder's objection and reasoning
- Trigger dispute resolution flow

### Phase 3: User Prompt
- Present resolution options to user
- Handle user selection
- Execute chosen path

### Phase 4: Judge Agent
- Implement judge agent interface
- Define judge prompt template
- Handle ENFORCE/DISMISS/ESCALATE decisions

### Phase 5: Tracking (Optional)
- Integrate logging/tracking for reviews and disputes
- Build dispute history
- Add analytics for continuous improvement
