"""LangGraph review workflow"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END, START

from ..types import ReviewSession, ReviewStatus, ReviewResult, ReviewIssue
from ..services.codex_cli import review_with_codex
from ..state.session import SessionManager


class ReviewState(TypedDict):
    """State for the review graph"""
    session: ReviewSession
    current_feedback: str | None
    should_continue: bool
    human_input: str | None
    error: str | None


def call_codex_review(state: ReviewState) -> dict:
    """Node: Call Codex for review"""
    session = state["session"]

    result = review_with_codex(
        files=session.files,
        working_dir=session.project_path,
    )

    if not result.success:
        return {
            "error": result.error or "Codex review failed",
            "should_continue": False,
        }

    output = result.output
    if output:
        if output.status == "approved":
            feedback = f"LGTM - {output.summary}"
        else:
            issue_lines = [
                f"[{issue.severity.value.upper()}] "
                f"{f'{issue.file}:{issue.line}: ' if issue.file else ''}"
                f"{issue.message}"
                for issue in output.issues
            ]
            parts = [output.summary, "", "Issues:", *issue_lines]
            if output.questions:
                parts.extend(["", "Questions:", *[f"- {q}" for q in output.questions]])
            feedback = "\n".join(parts)
    else:
        feedback = result.raw_output or "No output from Codex"

    return {
        "current_feedback": feedback,
        "should_continue": True,
    }


def process_review_result(state: ReviewState, session_manager: SessionManager) -> dict:
    """Node: Process review result"""
    session = state["session"]
    feedback = state.get("current_feedback")

    if not feedback:
        return {
            "error": "No feedback to process",
            "should_continue": False,
        }

    # Add iteration to history
    session_manager.add_iteration(session.review_id, feedback)

    # Check if approved
    feedback_lower = feedback.lower()
    is_approved = any(
        keyword in feedback_lower
        for keyword in ["lgtm", "approved", "no issues"]
    )

    # Get updated session
    updated_session = session_manager.get_session(session.review_id)
    if not updated_session:
        return {
            "error": "Session not found",
            "should_continue": False,
        }

    if is_approved:
        session_manager.update_status(session.review_id, ReviewStatus.APPROVED)
        return {
            "session": updated_session.model_copy(update={"status": ReviewStatus.APPROVED}),
            "should_continue": False,
        }

    # Check max iterations
    if session_manager.is_max_iterations_reached(updated_session):
        session_manager.update_status(session.review_id, ReviewStatus.MAX_ITERATIONS)
        return {
            "session": updated_session.model_copy(update={"status": ReviewStatus.MAX_ITERATIONS}),
            "should_continue": False,
        }

    # Has issues - continue
    session_manager.update_status(session.review_id, ReviewStatus.HAS_ISSUES)
    return {
        "session": updated_session.model_copy(update={"status": ReviewStatus.HAS_ISSUES}),
        "should_continue": True,
    }


def should_continue_review(state: ReviewState) -> Literal["continue", "end"]:
    """Conditional edge: should continue review loop?"""
    if state.get("error"):
        return "end"
    if not state.get("should_continue"):
        return "end"
    if state["session"].status == ReviewStatus.APPROVED:
        return "end"
    if state["session"].status == ReviewStatus.MAX_ITERATIONS:
        return "end"
    return "continue"


def create_review_graph(session_manager: SessionManager):
    """Create the review graph"""
    graph = StateGraph(ReviewState)

    # Add nodes
    graph.add_node("call_codex", call_codex_review)
    graph.add_node(
        "process_result",
        lambda state: process_review_result(state, session_manager),
    )

    # Add edges
    graph.add_edge(START, "call_codex")
    graph.add_edge("call_codex", "process_result")
    graph.add_conditional_edges(
        "process_result",
        should_continue_review,
        {
            "continue": "call_codex",
            "end": END,
        },
    )

    return graph.compile()


def run_single_review(
    session: ReviewSession,
    session_manager: SessionManager,
) -> ReviewResult:
    """Run a single review iteration (for MCP use)"""
    result = review_with_codex(
        files=session.files,
        working_dir=session.project_path,
    )

    if not result.success:
        return ReviewResult(
            status=ReviewStatus.ERROR,
            iteration=session.iteration + 1,
            issues=[],
            questions=[],
            summary=result.error or "Codex review failed",
            raw_output=result.raw_output,
        )

    output = result.output
    issues: list[ReviewIssue] = output.issues if output else []
    questions: list[str] = output.questions if output else []

    # Update session
    session_manager.add_iteration(
        session.review_id,
        output.summary if output else result.raw_output,
    )

    # Determine status
    status = ReviewStatus.HAS_ISSUES
    if output:
        if output.status == "approved":
            status = ReviewStatus.APPROVED
        elif output.status == "needs_clarification" or questions:
            status = ReviewStatus.NEEDS_HUMAN
            session_manager.set_pending_questions(session.review_id, questions)

    # Check max iterations
    updated_session = session_manager.get_session(session.review_id)
    if updated_session and session_manager.is_max_iterations_reached(updated_session):
        status = ReviewStatus.MAX_ITERATIONS

    session_manager.update_status(session.review_id, status)

    return ReviewResult(
        status=status,
        iteration=updated_session.iteration if updated_session else session.iteration + 1,
        issues=issues,
        questions=questions,
        summary=output.summary if output else "Review completed",
        raw_output=result.raw_output,
    )
