"""Type definitions for Glee"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    HAS_ISSUES = "has_issues"
    NEEDS_HUMAN = "needs_human"
    APPROVED = "approved"
    MAX_ITERATIONS = "max_iterations"
    ERROR = "error"


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"


class ReviewIssue(BaseModel):
    """A single issue found during review"""
    severity: IssueSeverity
    file: Optional[str] = None
    line: Optional[int] = None
    message: str
    suggested_fix: Optional[str] = None


class CodexOutput(BaseModel):
    """Structured output from Codex review"""
    status: str  # "approved", "has_issues", "needs_clarification"
    issues: list[ReviewIssue] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    summary: str


class ReviewIteration(BaseModel):
    """A single iteration in the review history"""
    iteration: int
    codex_feedback: str
    claude_changes: Optional[str] = None
    human_answers: Optional[dict[str, str]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ReviewSession(BaseModel):
    """Full review session"""
    review_id: str
    claude_session_id: str
    project_path: str
    files: list[str]
    iteration: int = 0
    max_iterations: int = 10
    history: list[ReviewIteration] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ReviewResult(BaseModel):
    """Result from a single review iteration"""
    status: ReviewStatus
    iteration: int
    issues: list[ReviewIssue] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    summary: str
    raw_output: Optional[str] = None


class MCPReviewResult(BaseModel):
    """MCP tool result"""
    status: ReviewStatus
    iteration: int
    max_iterations: int
    feedback: Optional[str] = None
    issues: Optional[list[ReviewIssue]] = None
    questions: Optional[list[str]] = None
    summary: str
    review_id: str
