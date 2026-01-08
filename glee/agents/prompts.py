"""Reusable prompt templates for Glee agents."""


def review_prompt(target: str = ".", focus: list[str] | None = None) -> str:
    """Generate a code review prompt.

    Args:
        target: What to review. Can be a file path, directory, 'git:changes',
                'git:staged', or a natural description.
        focus: Optional focus areas (security, performance, etc.)
    """
    focus_str = ""
    if focus:
        focus_str = f"Focus on: {', '.join(focus)}. "

    # Interpret special targets
    if target == "git:changes":
        target_str = "the uncommitted changes in this git repository (use `git diff` to see them)"
    elif target == "git:staged":
        target_str = "the staged changes in this git repository (use `git diff --staged` to see them)"
    else:
        target_str = target

    return f"""Review: {target_str}

{focus_str}Provide structured feedback using severity tags:

## Opinion Levels (for recommendations)
- [MUST] Required changes - mandatory
- [SHOULD] Recommended changes - optional

## Issue Levels (for identified problems)
- [HIGH] Critical issues - mandatory to fix
- [MEDIUM] Moderate issues - optional
- [LOW] Minor issues - optional

For each item, specify:
- File and line number
- Description
- Suggested fix

Example format:
[MUST] Fix SQL injection in auth.py:42 - use parameterized queries
[HIGH] Memory leak in cache.py:156 - connection pool never releases
[SHOULD] Consider async/await in api.py:89 - improves I/O performance
[MEDIUM] Function too long in utils.py:200 - consider splitting
[LOW] Variable 'x' in helpers.py:15 - use descriptive name

End with APPROVED if no MUST/HIGH items, or NEEDS_CHANGES if any found."""


def code_prompt(task: str, files: list[str] | None = None) -> str:
    """Generate a coding task prompt.

    Args:
        task: Description of the coding task
        files: Optional list of files to focus on
    """
    context = ""
    if files:
        context = f"Focus on these files: {', '.join(files)}. "

    return f"""{context}{task}

Implement the requested changes. Use the available tools to read and modify files."""


def judge_prompt(code_context: str, review_item: str, coder_objection: str) -> str:
    """Generate a judge arbitration prompt.

    Args:
        code_context: The relevant code being disputed
        review_item: The reviewer's feedback (MUST or HIGH item)
        coder_objection: The coder's reasoning for disagreeing
    """
    return f"""You are an impartial judge arbitrating a dispute between a coder and a reviewer.

## Code Context
```
{code_context}
```

## Reviewer's Feedback (Disputed)
{review_item}

## Coder's Objection
{coder_objection}

## Your Task
Evaluate both perspectives objectively and make a decision:

1. **ENFORCE** - The reviewer is correct. The coder must implement the feedback.
2. **DISMISS** - The coder's objection is valid. The review item can be ignored.
3. **ESCALATE** - The situation is ambiguous and requires human judgment.

## Guidelines
- Focus on technical correctness, not preferences
- Consider: Does the review identify a real issue? Is the coder's objection factually accurate?
- ENFORCE if: The review catches a genuine bug, security issue, or violation of requirements
- DISMISS if: The review is based on a misunderstanding, or the suggestion would break functionality
- ESCALATE if: Both sides have valid points, or the decision requires domain knowledge you lack

## Response Format
Start your response with one of: ENFORCE, DISMISS, or ESCALATE

Then provide a brief explanation (2-3 sentences) justifying your decision.

Example:
ENFORCE
The reviewer correctly identified a SQL injection vulnerability. The coder's objection that "the input is trusted" is incorrect because user input should never be trusted without validation."""


def process_feedback_prompt(review_items: str) -> str:
    """Generate a prompt for processing review feedback.

    Args:
        review_items: The structured review feedback from reviewer
    """
    return f"""You received the following review feedback on your code:

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
Reviewers help improve code quality. Embrace their feedback."""
