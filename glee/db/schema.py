"""Central schema definitions for all Glee databases.

SQLite (glee.db):
- agent_logs: Agent invocation history
- logs: General application logs

DuckDB (memory.duckdb):
- memories: Stored memories with embeddings
- stats: Key-value stats/metadata
"""

from typing import TypedDict


class TableSchema(TypedDict):
    """Schema definition for a database table."""

    table: str
    indexes: list[str]

# =============================================================================
# SQLite Schemas (glee.db)
# =============================================================================

AGENT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS agent_logs (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    prompt TEXT NOT NULL,
    output TEXT,
    raw TEXT,
    error TEXT,
    exit_code INTEGER,
    duration_ms INTEGER,
    success INTEGER
)
"""

AGENT_LOGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON agent_logs(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_logs(agent)",
]

LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
)
"""

LOGS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)",
]

# All SQLite schemas
SQLITE_SCHEMAS: dict[str, TableSchema] = {
    "agent_logs": {
        "table": AGENT_LOGS_TABLE,
        "indexes": AGENT_LOGS_INDEXES,
    },
    "logs": {
        "table": LOGS_TABLE,
        "indexes": LOGS_INDEXES,
    },
}

# =============================================================================
# DuckDB Schemas (memory.duckdb)
# =============================================================================

MEMORIES_TABLE = """
CREATE TABLE IF NOT EXISTS memories (
    id VARCHAR PRIMARY KEY,
    category VARCHAR NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

MEMORIES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)",
]

STATS_TABLE = """
CREATE TABLE IF NOT EXISTS stats (
    key VARCHAR PRIMARY KEY,
    value JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

STATS_INDEXES: list[str] = []

# All DuckDB schemas
DUCKDB_SCHEMAS: dict[str, TableSchema] = {
    "memories": {
        "table": MEMORIES_TABLE,
        "indexes": MEMORIES_INDEXES,
    },
    "stats": {
        "table": STATS_TABLE,
        "indexes": STATS_INDEXES,
    },
}
