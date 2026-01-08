"""Storage implementations for review sessions"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..types import ReviewSession


class ReviewStorage(ABC):
    """Abstract base class for review session storage"""

    @abstractmethod
    def save(self, session: ReviewSession) -> None:
        """Save a review session"""
        pass

    @abstractmethod
    def load(self, review_id: str) -> Optional[ReviewSession]:
        """Load a review session by ID"""
        pass

    @abstractmethod
    def load_by_claude_session(self, claude_session_id: str) -> list[ReviewSession]:
        """Load all sessions for a Claude session"""
        pass

    @abstractmethod
    def list_sessions(self, project_path: str) -> list[ReviewSession]:
        """List all sessions for a project"""
        pass

    @abstractmethod
    def delete(self, review_id: str) -> None:
        """Delete a review session"""
        pass


class LocalStorage(ReviewStorage):
    """Local JSON file storage"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd() / ".glee"
        self.sessions_dir = self.base_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, review_id: str) -> Path:
        return self.sessions_dir / f"{review_id}.json"

    def save(self, session: ReviewSession) -> None:
        file_path = self._get_session_path(session.review_id)
        data = session.model_dump(mode="json")
        file_path.write_text(json.dumps(data, indent=2, default=str))

    def load(self, review_id: str) -> Optional[ReviewSession]:
        file_path = self._get_session_path(review_id)
        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text())
            return ReviewSession.model_validate(data)
        except Exception:
            return None

    def load_by_claude_session(self, claude_session_id: str) -> list[ReviewSession]:
        sessions = self._list_all()
        return [s for s in sessions if s.claude_session_id == claude_session_id]

    def list_sessions(self, project_path: str) -> list[ReviewSession]:
        sessions = self._list_all()
        return sorted(
            [s for s in sessions if s.project_path == project_path],
            key=lambda s: s.updated_at,
            reverse=True,
        )

    def _list_all(self) -> list[ReviewSession]:
        sessions = []
        for file_path in self.sessions_dir.glob("*.json"):
            session = self.load(file_path.stem)
            if session:
                sessions.append(session)
        return sessions

    def delete(self, review_id: str) -> None:
        file_path = self._get_session_path(review_id)
        if file_path.exists():
            file_path.unlink()


class MemoryStorage(ReviewStorage):
    """In-memory storage for testing"""

    def __init__(self):
        self._sessions: dict[str, ReviewSession] = {}

    def save(self, session: ReviewSession) -> None:
        self._sessions[session.review_id] = session.model_copy(deep=True)

    def load(self, review_id: str) -> Optional[ReviewSession]:
        session = self._sessions.get(review_id)
        return session.model_copy(deep=True) if session else None

    def load_by_claude_session(self, claude_session_id: str) -> list[ReviewSession]:
        return [
            s.model_copy(deep=True)
            for s in self._sessions.values()
            if s.claude_session_id == claude_session_id
        ]

    def list_sessions(self, project_path: str) -> list[ReviewSession]:
        return sorted(
            [
                s.model_copy(deep=True)
                for s in self._sessions.values()
                if s.project_path == project_path
            ],
            key=lambda s: s.updated_at,
            reverse=True,
        )

    def delete(self, review_id: str) -> None:
        self._sessions.pop(review_id, None)

    def clear(self) -> None:
        self._sessions.clear()
