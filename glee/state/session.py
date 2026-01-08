"""Session manager for review sessions"""

import uuid
from datetime import datetime
from typing import Optional

from ..types import ReviewSession, ReviewStatus, ReviewIteration
from ..services.codex_cli import get_claude_session_id
from .storage import ReviewStorage


class SessionManager:
    """Manages review sessions"""

    def __init__(self, storage: ReviewStorage):
        self.storage = storage

    def create_session(
        self,
        files: list[str],
        project_path: str,
        max_iterations: int = 10,
        claude_session_id: Optional[str] = None,
    ) -> ReviewSession:
        """Create a new review session"""
        now = datetime.now()
        session = ReviewSession(
            review_id=str(uuid.uuid4()),
            claude_session_id=claude_session_id or get_claude_session_id(project_path) or "unknown",
            project_path=project_path,
            files=files,
            iteration=0,
            max_iterations=max_iterations,
            history=[],
            pending_questions=[],
            status=ReviewStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self.storage.save(session)
        return session

    def get_session(self, review_id: str) -> Optional[ReviewSession]:
        """Get a session by ID"""
        return self.storage.load(review_id)

    def update_status(self, review_id: str, status: ReviewStatus) -> Optional[ReviewSession]:
        """Update session status"""
        session = self.storage.load(review_id)
        if not session:
            return None

        session.status = status
        session.updated_at = datetime.now()
        self.storage.save(session)
        return session

    def add_iteration(
        self,
        review_id: str,
        codex_feedback: str,
        claude_changes: Optional[str] = None,
    ) -> Optional[ReviewSession]:
        """Add an iteration to the session history"""
        session = self.storage.load(review_id)
        if not session:
            return None

        session.iteration += 1
        session.history.append(ReviewIteration(
            iteration=session.iteration,
            codex_feedback=codex_feedback,
            claude_changes=claude_changes,
            timestamp=datetime.now(),
        ))
        session.updated_at = datetime.now()
        self.storage.save(session)
        return session

    def set_pending_questions(
        self,
        review_id: str,
        questions: list[str],
    ) -> Optional[ReviewSession]:
        """Set pending questions for human input"""
        session = self.storage.load(review_id)
        if not session:
            return None

        session.pending_questions = questions
        session.status = ReviewStatus.NEEDS_HUMAN
        session.updated_at = datetime.now()
        self.storage.save(session)
        return session

    def answer_questions(
        self,
        review_id: str,
        answers: dict[str, str],
    ) -> Optional[ReviewSession]:
        """Answer pending questions"""
        session = self.storage.load(review_id)
        if not session:
            return None

        # Add answers to last iteration
        if session.history:
            session.history[-1].human_answers = answers

        session.pending_questions = []
        session.status = ReviewStatus.IN_PROGRESS
        session.updated_at = datetime.now()
        self.storage.save(session)
        return session

    def is_max_iterations_reached(self, session: ReviewSession) -> bool:
        """Check if max iterations reached"""
        return session.iteration >= session.max_iterations

    def get_active_session(self, project_path: str) -> Optional[ReviewSession]:
        """Get the active session for a project"""
        sessions = self.storage.list_sessions(project_path)
        for session in sessions:
            if session.status in (ReviewStatus.IN_PROGRESS, ReviewStatus.NEEDS_HUMAN):
                return session
        return None

    def list_sessions(self, project_path: str) -> list[ReviewSession]:
        """List all sessions for a project"""
        return self.storage.list_sessions(project_path)

    def delete_session(self, review_id: str) -> None:
        """Delete a session"""
        self.storage.delete(review_id)
