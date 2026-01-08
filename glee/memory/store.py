"""Memory store combining LanceDB (vector) and DuckDB (SQL)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import lancedb
from fastembed import TextEmbedding
from pydantic import BaseModel


class MemoryEntry(BaseModel):
    """A memory entry."""

    id: str
    category: str  # architecture, convention, review, decision
    content: str
    metadata: dict[str, Any] = {}
    created_at: datetime = datetime.now()


class Memory:
    """Memory store for project context."""

    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path)
        self.glee_dir = self.project_path / ".glee"
        self.lance_path = self.glee_dir / "memory.lance"
        self.duck_path = self.glee_dir / "memory.duckdb"

        # Initialize embedding model (lazy)
        self._embedder: TextEmbedding | None = None

        # Initialize databases
        self._lance_db: lancedb.DBConnection | None = None
        self._duck_conn: duckdb.DuckDBPyConnection | None = None

    @property
    def embedder(self) -> TextEmbedding:
        """Lazy load embedding model."""
        if self._embedder is None:
            self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        return self._embedder

    @property
    def lance(self) -> lancedb.DBConnection:
        """Get LanceDB connection."""
        if self._lance_db is None:
            self._lance_db = lancedb.connect(str(self.lance_path))
        return self._lance_db

    @property
    def duck(self) -> duckdb.DuckDBPyConnection:
        """Get DuckDB connection."""
        if self._duck_conn is None:
            self._duck_conn = duckdb.connect(str(self.duck_path))
            self._init_duck_schema()
        return self._duck_conn

    def _init_duck_schema(self) -> None:
        """Initialize DuckDB schema."""
        self.duck.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id VARCHAR PRIMARY KEY,
                category VARCHAR NOT NULL,
                content TEXT NOT NULL,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.duck.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                key VARCHAR PRIMARY KEY,
                value JSON,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        embeddings = list(self.embedder.embed([text]))
        return embeddings[0].tolist()

    def add(
        self,
        category: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a memory entry.

        Args:
            category: Type of memory (architecture, convention, review, decision)
            content: The content to remember
            metadata: Optional metadata

        Returns:
            The memory ID
        """
        import uuid

        memory_id = str(uuid.uuid4())[:8]
        now = datetime.now()

        # Store in DuckDB (structured)
        self.duck.execute(
            """
            INSERT INTO memories (id, category, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [memory_id, category, content, json.dumps(metadata or {}), now],
        )

        # Store in LanceDB (vector)
        vector = self._embed(content)
        table_name = "memories"

        data = [{
            "id": memory_id,
            "category": category,
            "content": content,
            "vector": vector,
        }]

        try:
            table = self.lance.open_table(table_name)
            table.add(data)  # type: ignore[reportUnknownMemberType]
        except Exception:
            # Table doesn't exist, create it
            self.lance.create_table(table_name, data)  # type: ignore[reportUnknownMemberType]

        return memory_id

    def search(
        self,
        query: str,
        category: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity.

        Args:
            query: Search query
            category: Optional category filter
            limit: Max results

        Returns:
            List of matching memories
        """
        try:
            table = self.lance.open_table("memories")
        except Exception:
            return []

        vector = self._embed(query)
        results = table.search(vector).limit(limit)  # type: ignore[reportUnknownMemberType]

        if category:
            results = results.where(f"category = '{category}'")

        return list(results.to_list())  # type: ignore[reportUnknownMemberType]

    def get_by_category(self, category: str) -> list[dict[str, Any]]:
        """Get all memories in a category."""
        result = self.duck.execute(
            "SELECT * FROM memories WHERE category = ? ORDER BY created_at DESC",
            [category],
        ).fetchall()

        columns = ["id", "category", "content", "metadata", "created_at"]
        return [dict(zip(columns, row)) for row in result]

    def get_context(self) -> str:
        """Get formatted context for hook injection."""
        lines: list[str] = []

        # Architecture decisions
        arch = self.get_by_category("architecture")
        if arch:
            lines.append("### Architecture Decisions")
            for m in arch[:5]:
                lines.append(f"- {m['content']}")
            lines.append("")

        # Code conventions
        conv = self.get_by_category("convention")
        if conv:
            lines.append("### Code Conventions")
            for m in conv[:5]:
                lines.append(f"- {m['content']}")
            lines.append("")

        # Recent decisions
        decisions = self.get_by_category("decision")
        if decisions:
            lines.append("### Recent Decisions")
            for m in decisions[:5]:
                lines.append(f"- {m['content']}")
            lines.append("")

        # Recent review issues
        reviews = self.get_by_category("review")
        if reviews:
            lines.append("### Recent Review Issues")
            for m in reviews[:5]:
                lines.append(f"- {m['content']}")
            lines.append("")

        return "\n".join(lines)

    def close(self) -> None:
        """Close database connections."""
        if self._duck_conn:
            self._duck_conn.close()
            self._duck_conn = None
        self._lance_db = None
