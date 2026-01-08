"""Logging configuration for Glee with SQLite storage."""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger


class SQLiteLogHandler:
    """Custom log handler that stores logs in SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get SQLite connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
        return self._conn

    def _init_db(self) -> None:
        """Initialize the logs table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                function TEXT,
                line INTEGER,
                extra JSON
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)
        """)
        self.conn.commit()

    def write(self, message: Any) -> None:
        """Write a log record to SQLite."""
        import json

        record = message.record
        extra_json = json.dumps(record["extra"]) if record["extra"] else None

        self.conn.execute(
            """
            INSERT INTO logs (timestamp, level, message, module, function, line, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["time"].isoformat(),
                record["level"].name,
                record["message"],
                record["module"],
                record["function"],
                record["line"],
                extra_json,
            ],
        )
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


_log_handler: SQLiteLogHandler | None = None


def setup_logging(project_path: Path | None = None) -> "Logger":
    """Configure loguru logging with SQLite storage.

    Args:
        project_path: Project path for .glee directory. If None, only console logging.

    Returns:
        Configured logger instance.
    """
    global _log_handler

    logger.remove()

    # Console logging
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG",
    )

    # SQLite logging if project path provided
    if project_path:
        glee_dir = project_path / ".glee"
        glee_dir.mkdir(exist_ok=True)
        db_path = glee_dir / "logs.db"

        _log_handler = SQLiteLogHandler(db_path)
        logger.add(_log_handler.write, level="DEBUG")

    return logger


def query_logs(
    project_path: Path,
    level: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query logs from SQLite.

    Args:
        project_path: Project path containing .glee directory.
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR).
        since: Filter logs after this time.
        until: Filter logs before this time.
        search: Search in message text.
        limit: Max number of results.

    Returns:
        List of log records.
    """
    db_path = project_path / ".glee" / "logs.db"
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM logs WHERE 1=1"
    params: list[Any] = []

    if level:
        query += " AND level = ?"
        params.append(level.upper())

    if since:
        query += " AND timestamp >= ?"
        params.append(since.isoformat())

    if until:
        query += " AND timestamp <= ?"
        params.append(until.isoformat())

    if search:
        query += " AND message LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor = conn.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def get_log_stats(project_path: Path) -> dict[str, Any]:
    """Get log statistics.

    Args:
        project_path: Project path containing .glee directory.

    Returns:
        Dictionary with log stats.
    """
    db_path = project_path / ".glee" / "logs.db"
    if not db_path.exists():
        return {"total": 0, "by_level": {}}

    conn = sqlite3.connect(str(db_path))

    # Total count
    total = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]

    # Count by level
    cursor = conn.execute(
        "SELECT level, COUNT(*) as count FROM logs GROUP BY level"
    )
    by_level = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return {"total": total, "by_level": by_level}
