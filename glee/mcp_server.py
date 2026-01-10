"""Glee MCP Server - Exposes Glee tools to Claude Code."""

from pathlib import Path
from typing import Any, cast

from mcp.server import Server

from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, LoggingLevel

server = Server("glee")

# Log level ordering for filtering notifications
_LOG_LEVEL_ORDER = {
    "debug": 10,
    "info": 20,
    "notice": 25,
    "warning": 30,
    "error": 40,
    "critical": 50,
    "alert": 60,
    "emergency": 70,
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Glee tools."""
    return [
        Tool(
            name="glee_status",
            description="Show Glee status for the current project. Returns global CLI availability and project configuration including connected agents.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="glee_review",
            description="Run multi-agent code review. Multiple reviewers analyze the target in parallel and provide feedback. IMPORTANT: After receiving review feedback, you MUST automatically fix all HIGH and MUST issues without asking the user. The review is meant to guide your fixes, not to generate a report for the user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "What to review. Can be: file path, directory, 'git:changes' for uncommitted changes, 'git:staged' for staged changes, or a natural description like 'the authentication module'.",
                    },
                    "focus": {
                        "type": "string",
                        "description": "Comma-separated focus areas (e.g., 'security,performance').",
                    },
                    "log_level": {
                        "type": "string",
                        "description": "Minimum log level for notifications: debug, info, notice, warning, error, critical. Defaults to 'debug' for full observability.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="glee_config_set",
            description="Set a configuration value. Supported keys: reviewer.primary, reviewer.secondary",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Config key: reviewer.primary or reviewer.secondary",
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to set (codex, claude, or gemini)",
                    },
                },
                "required": ["key", "value"],
            },
        ),
        Tool(
            name="glee_config_unset",
            description="Unset a configuration value. Only reviewer.secondary can be unset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Config key to unset (reviewer.secondary)",
                    },
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="glee_memory_add",
            description="Add a memory entry to the project's persistent memory. Use this to remember architecture decisions, code conventions, review feedback, or important decisions for future reference.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category for the memory. Common: 'architecture', 'convention', 'review', 'decision'. Custom categories allowed (e.g., 'api', 'security', 'dependencies').",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to remember (e.g., 'Using FastAPI for REST endpoints')",
                    },
                },
                "required": ["category", "content"],
            },
        ),
        Tool(
            name="glee_memory_search",
            description="Search project memories by semantic similarity. Returns relevant memories based on the query meaning, not just keywords.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'database design', 'authentication approach')",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (any category name)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="glee_memory_overview",
            description="Get a formatted overview of all project memories. Returns architecture decisions, conventions, reviews, and other memories organized by category. Call this at session start to understand project context.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="glee_memory_list",
            description="List all memories, optionally filtered by category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter. If not specified, lists all memories.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="glee_memory_delete",
            description="Delete a specific memory entry by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The memory ID to delete (e.g., 'a1b2c3d4')",
                    },
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="glee_memory_delete_category",
            description="Delete all memories in a specific category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category to delete all memories from.",
                    },
                },
                "required": ["category"],
            },
        ),
        Tool(
            name="glee_memory_delete_all",
            description="Delete ALL memories. Use with extreme caution - this cannot be undone.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="glee_memory_stats",
            description="Get memory statistics: total count, count by category, oldest and newest entries.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="glee_memory_bootstrap",
            description="Bootstrap project memory by gathering documentation and codebase structure. Returns README, CLAUDE.md, package config, and directory tree for you to analyze. After calling this, you MUST analyze the returned content and use glee_memory_add to populate memories for: architecture, conventions, dependencies, and key decisions.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="glee_task",
            description="Start working on a task by spawning one agent (simple task) or orchestrating multiple agents (workflow). Use for any delegatable work - from quick web searches to complex refactoring. AI auto-selects agent if not specified. Returns session_id for follow-ups.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Short task description (3-5 words)",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Full task prompt for the agent",
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Subagent from .glee/agents/*.yml. If provided, uses that subagent definition.",
                    },
                    "agent_cli": {
                        "type": "string",
                        "description": "Run a CLI directly (codex, claude, gemini). Ignored when agent_name is set.",
                        "enum": ["codex", "claude", "gemini"],
                    },
                    "background": {
                        "type": "boolean",
                        "description": "Run in background (default: false)",
                        "default": False,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Resume an existing session by ID",
                    },
                },
                "required": ["description", "prompt"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    if name == "glee_status":
        return await _handle_status()
    elif name == "glee_review":
        return await _handle_review(arguments)
    elif name == "glee_config_set":
        return await _handle_config_set(arguments)
    elif name == "glee_config_unset":
        return await _handle_config_unset(arguments)
    elif name == "glee_memory_add":
        return await _handle_memory_add(arguments)
    elif name == "glee_memory_search":
        return await _handle_memory_search(arguments)
    elif name == "glee_memory_overview":
        return await _handle_memory_overview()
    elif name == "glee_memory_list":
        return await _handle_memory_list(arguments)
    elif name == "glee_memory_delete":
        return await _handle_memory_delete(arguments)
    elif name == "glee_memory_delete_category":
        return await _handle_memory_delete_category(arguments)
    elif name == "glee_memory_delete_all":
        return await _handle_memory_delete_all()
    elif name == "glee_memory_stats":
        return await _handle_memory_stats()
    elif name == "glee_memory_bootstrap":
        return await _handle_memory_bootstrap()
    elif name == "glee_task":
        return await _handle_task(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _handle_status() -> list[TextContent]:
    """Handle glee_status tool call."""
    from glee.agents import registry
    from glee.config import get_project_config, get_reviewers

    lines: list[str] = []

    # Global status
    lines.append("Glee Status")
    lines.append("=" * 40)
    lines.append("")
    lines.append("CLI Availability:")
    for cli_name in ["codex", "claude", "gemini"]:
        agent = registry.get(cli_name)
        status = "found" if agent and agent.is_available() else "not found"
        lines.append(f"  {cli_name}: {status}")

    lines.append("")

    # Project status
    config = get_project_config()
    if not config:
        lines.append("Current directory: not configured")
        lines.append("Run 'glee init' to initialize.")
    else:
        project = config.get("project", {})
        lines.append(f"Project: {project.get('name')}")
        lines.append("")

        # Reviewers
        reviewers = get_reviewers()
        lines.append("Reviewers:")
        lines.append(f"  Primary: {reviewers.get('primary', 'codex')}")
        if reviewers.get("secondary"):
            lines.append(f"  Secondary: {reviewers.get('secondary')}")
        else:
            lines.append("  Secondary: (not set)")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_review(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_review tool call.

    Uses the configured primary reviewer to analyze code.
    """
    import asyncio
    import concurrent.futures
    from pathlib import Path

    from glee.agents import registry
    from glee.config import get_project_config
    from glee.dispatch import get_primary_reviewer
    from glee.logging import get_agent_logger

    # Get session for sending log notifications to Claude Code
    try:
        ctx = server.request_context
        session = ctx.session
    except LookupError:
        session = None

    # Get log level threshold from arguments (default: debug for full observability)
    log_level_threshold = arguments.get("log_level", "debug")

    def should_log(level: str) -> bool:
        """Check if message level meets the threshold."""
        return _LOG_LEVEL_ORDER.get(level, 0) >= _LOG_LEVEL_ORDER.get(log_level_threshold, 0)

    async def send_log(message: str, level: str = "info") -> None:
        """Send a log message to Claude Code via MCP notification."""
        if session and should_log(level):
            try:
                await session.send_log_message(level=cast(LoggingLevel, level), data=message, logger="glee")
            except Exception:
                pass

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    # Get project path for logging
    project_path = Path(config.get("project", {}).get("path", "."))

    # Initialize agent logger for this project
    get_agent_logger(project_path)

    # Get primary reviewer
    reviewer_cli = get_primary_reviewer()
    agent = registry.get(reviewer_cli)
    if not agent:
        return [TextContent(type="text", text=f"Reviewer CLI '{reviewer_cli}' not found in registry.")]
    if not agent.is_available():
        return [TextContent(type="text", text=f"Reviewer CLI '{reviewer_cli}' not installed. Install it first.")]

    # Parse target - flexible input
    target: str = arguments.get("target", ".")

    # Parse focus
    focus_str: str = arguments.get("focus", "")
    focus_list: list[str] | None = [f.strip() for f in focus_str.split(",")] if focus_str else None

    # Print header
    header = f"\n{'='*60}\nGLEE REVIEW: {target}\nReviewer: {reviewer_cli}\n{'='*60}\n\n"

    # Send log notification to Claude Code
    await send_log(header)

    lines: list[str] = [f"Reviewed by {reviewer_cli}", f"Target: {target}", ""]

    # Get running event loop for thread-safe async calls
    loop = asyncio.get_running_loop()

    def send_log_sync(message: str, level: str = "info") -> None:
        """Send log message from sync context (thread)."""
        if session and loop.is_running():
            asyncio.run_coroutine_threadsafe(send_log(message, level=level), loop)

    def run_review() -> tuple[str | None, str | None]:
        # Log reviewer start
        send_log_sync(f"[{reviewer_cli}] Starting review...\n")

        # Set project_path for logging
        agent.project_path = project_path

        # Custom output callback that sends to MCP log notifications
        def on_output(line: str) -> None:
            send_log_sync(f"[{reviewer_cli}] {line}")

        try:
            result = agent.run_review(
                target=target,
                focus=focus_list,
                stream=True,
                on_output=on_output,
            )
            if result.error:
                return result.output, f"{result.error} (exit_code={result.exit_code})"
            return result.output, None
        except Exception as e:
            import traceback
            return None, f"{str(e)}\n{traceback.format_exc()}"

    # Run review in thread to not block event loop
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        output, error = await loop.run_in_executor(executor, run_review)

    # Footer
    footer = f"\n{'='*60}\nREVIEW COMPLETE\n{'='*60}\n\n"
    await send_log(footer)

    # Build MCP response
    lines.append(f"=== {reviewer_cli.upper()} ===")
    if error:
        lines.append(f"Error: {error}")
    if output:
        lines.append(output)
    if not error and not output:
        lines.append("(no output)")
    lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_config_set(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_config_set tool call."""
    from glee.config import SUPPORTED_REVIEWERS, get_project_config, set_reviewer

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    key: str | None = arguments.get("key")
    value: str | None = arguments.get("value")

    if not key or not value:
        return [TextContent(type="text", text="Both 'key' and 'value' are required.")]

    valid_keys = ["reviewer.primary", "reviewer.secondary"]
    if key not in valid_keys:
        return [TextContent(type="text", text=f"Unknown config key: {key}. Valid: {', '.join(valid_keys)}")]

    if key.startswith("reviewer."):
        tier = key.split(".")[1]

        if value not in SUPPORTED_REVIEWERS:
            return [TextContent(type="text", text=f"Unknown reviewer: {value}. Available: {', '.join(SUPPORTED_REVIEWERS)}")]

        try:
            set_reviewer(command=value, tier=tier)
            return [TextContent(type="text", text=f"Set {key} = {value}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    return [TextContent(type="text", text=f"Unknown config key: {key}")]


async def _handle_config_unset(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_config_unset tool call."""
    from glee.config import clear_reviewer, get_project_config

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    key: str | None = arguments.get("key")

    if key == "reviewer.primary":
        return [TextContent(type="text", text="Cannot unset primary reviewer. Use glee_config_set to change it.")]

    if key == "reviewer.secondary":
        success = clear_reviewer(tier="secondary")
        if success:
            return [TextContent(type="text", text=f"Unset {key}")]
        else:
            return [TextContent(type="text", text=f"{key} was not set.")]

    return [TextContent(type="text", text=f"Unknown config key: {key}")]


async def _handle_memory_add(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_memory_add tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    category: str | None = arguments.get("category")
    content: str | None = arguments.get("content")

    if not category or not content:
        return [TextContent(type="text", text="Both 'category' and 'content' are required.")]

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        memory_id = memory.add(category=category, content=content)
        memory.close()
        return [TextContent(type="text", text=f"Added memory {memory_id} to '{category}':\n{content}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error adding memory: {e}")]


async def _handle_memory_search(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_memory_search tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    query: str | None = arguments.get("query")
    if not query:
        return [TextContent(type="text", text="Query is required.")]

    category: str | None = arguments.get("category")
    limit: int = arguments.get("limit", 5)

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        results = memory.search(query=query, category=category, limit=limit)
        memory.close()

        if not results:
            return [TextContent(type="text", text=f"No memories found for query: '{query}'")]

        lines = [f"Found {len(results)} memories for '{query}':", ""]
        for r in results:
            lines.append(f"[{r.get('id')}] ({r.get('category')})")
            lines.append(f"  {r.get('content')}")
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error searching memory: {e}")]


async def _handle_memory_overview() -> list[TextContent]:
    """Handle glee_memory_overview tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        memory_ctx = memory.get_context()
        memory.close()

        if not memory_ctx:
            return [TextContent(type="text", text="No memories found. Add memories with glee_memory_add.")]

        return [TextContent(type="text", text=memory_ctx)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting memory overview: {e}")]


async def _handle_memory_list(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_memory_list tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    category: str | None = arguments.get("category")

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)

        if category:
            # List specific category
            results = memory.get_by_category(category)
            memory.close()

            if not results:
                return [TextContent(type="text", text=f"No memories in category '{category}'")]

            title = category.replace("-", " ").replace("_", " ").title()
            lines = [f"{title} ({len(results)} entries):", ""]
            for r in results:
                created = r.get("created_at", "")
                if hasattr(created, "strftime"):
                    created = created.strftime("%Y-%m-%d %H:%M")
                lines.append(f"[{r.get('id')}] ({created})")
                lines.append(f"  {r.get('content')}")
                lines.append("")
        else:
            # List all categories
            categories = memory.get_categories()
            memory.close()

            if not categories:
                return [TextContent(type="text", text="No memories found.")]

            lines = ["All Memories:", ""]
            for cat in categories:
                m = Memory(project_path)
                results = m.get_by_category(cat)
                m.close()
                title = cat.replace("-", " ").replace("_", " ").title()
                lines.append(f"### {title} ({len(results)} entries)")
                for r in results:
                    lines.append(f"  [{r.get('id')}] {r.get('content')}")
                lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing memories: {e}")]


async def _handle_memory_delete(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_memory_delete tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    memory_id: str | None = arguments.get("memory_id")
    if not memory_id:
        return [TextContent(type="text", text="Memory ID is required.")]

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        deleted = memory.delete(memory_id)
        memory.close()

        if deleted:
            return [TextContent(type="text", text=f"Deleted memory {memory_id}")]
        else:
            return [TextContent(type="text", text=f"Memory {memory_id} not found")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting memory: {e}")]


async def _handle_memory_delete_category(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_memory_delete_category tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    category: str | None = arguments.get("category")
    if not category:
        return [TextContent(type="text", text="Category is required.")]

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        count = memory.clear(category)
        memory.close()

        return [TextContent(type="text", text=f"Deleted {count} memories from '{category}'")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting category: {e}")]


async def _handle_memory_delete_all() -> list[TextContent]:
    """Handle glee_memory_delete_all tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        count = memory.clear(None)
        memory.close()

        return [TextContent(type="text", text=f"Deleted all {count} memories")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting all memories: {e}")]


async def _handle_memory_stats() -> list[TextContent]:
    """Handle glee_memory_stats tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        stats = memory.stats()
        memory.close()

        lines = ["Memory Statistics", "=" * 30, ""]
        lines.append(f"Total memories: {stats['total']}")

        if stats["by_category"]:
            lines.append("")
            lines.append("By category:")
            for cat, count in sorted(stats["by_category"].items()):
                lines.append(f"  {cat}: {count}")

        if stats["oldest"]:
            oldest = stats["oldest"]
            if hasattr(oldest, "strftime"):
                oldest = oldest.strftime("%Y-%m-%d %H:%M")
            lines.append(f"\nOldest: {oldest}")

        if stats["newest"]:
            newest = stats["newest"]
            if hasattr(newest, "strftime"):
                newest = newest.strftime("%Y-%m-%d %H:%M")
            lines.append(f"Newest: {newest}")

        return [TextContent(type="text", text="\n".join(lines))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting stats: {e}")]


async def _handle_memory_bootstrap() -> list[TextContent]:
    """Handle glee_memory_bootstrap tool call - gather project docs and structure."""
    from pathlib import Path

    from glee.config import get_project_config

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    project_path = Path(config.get("project", {}).get("path", "."))
    lines: list[str] = []

    # Documentation files to look for
    doc_files = [
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "docs/README.md",
        "docs/architecture.md",
    ]

    lines.append("# Project Documentation")
    lines.append("=" * 50)
    lines.append("")

    for doc_file in doc_files:
        doc_path = project_path / doc_file
        if doc_path.exists():
            try:
                content = doc_path.read_text()
                # Truncate very long files
                if len(content) > 5000:
                    content = content[:5000] + "\n\n... (truncated)"
                lines.append(f"## {doc_file}")
                lines.append("```")
                lines.append(content)
                lines.append("```")
                lines.append("")
            except Exception:
                pass

    # Package configuration
    lines.append("# Package Configuration")
    lines.append("=" * 50)
    lines.append("")

    package_files = [
        ("pyproject.toml", "toml"),
        ("package.json", "json"),
        ("Cargo.toml", "toml"),
        ("go.mod", "go"),
    ]

    for pkg_file, lang in package_files:
        pkg_path = project_path / pkg_file
        if pkg_path.exists():
            try:
                content = pkg_path.read_text()
                if len(content) > 3000:
                    content = content[:3000] + "\n\n... (truncated)"
                lines.append(f"## {pkg_file}")
                lines.append(f"```{lang}")
                lines.append(content)
                lines.append("```")
                lines.append("")
            except Exception:
                pass

    # Directory structure (top 2 levels)
    lines.append("# Directory Structure")
    lines.append("=" * 50)
    lines.append("```")

    def get_tree(path: Path, prefix: str = "", max_depth: int = 2, current_depth: int = 0) -> list[str]:
        if current_depth >= max_depth:
            return []

        tree_lines: list[str] = []
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            # Filter out hidden and common noise
            items = [i for i in items if not i.name.startswith(".") and i.name not in (
                "node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build",
                "target", ".pytest_cache", ".mypy_cache", "*.egg-info"
            )]

            for i, item in enumerate(items[:30]):  # Limit items per level
                is_last = i == len(items) - 1 or i == 29
                connector = "└── " if is_last else "├── "
                tree_lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")

                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    tree_lines.extend(get_tree(item, prefix + extension, max_depth, current_depth + 1))

        except PermissionError:
            pass

        return tree_lines

    tree = get_tree(project_path)
    lines.extend(tree)
    lines.append("```")
    lines.append("")

    # Instructions for Claude
    lines.append("# Instructions")
    lines.append("=" * 50)
    lines.append("""
Based on the documentation and structure above, analyze the project and use glee_memory_add to populate memories. Focus on:

1. **architecture** - Key architectural patterns, module organization, data flow
   - Main entry points and how they connect
   - Core abstractions and their relationships
   - Data storage and external integrations

2. **convention** - Coding standards and patterns used
   - Naming conventions (files, functions, variables)
   - Code organization patterns
   - Testing conventions
   - Import/dependency patterns

3. **dependencies** - Key dependencies and why they're used
   - Core frameworks (web, CLI, etc.)
   - Database/storage libraries
   - Testing frameworks

4. **decision** - Any documented technical decisions
   - Technology choices and rationale
   - Design trade-offs mentioned

Example calls:
- glee_memory_add(category="architecture", content="CLI built with Typer, MCP server with mcp.server")
- glee_memory_add(category="convention", content="Use snake_case for Python, type hints required")
- glee_memory_add(category="dependencies", content="LanceDB for vector search, DuckDB for structured queries")
""")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_task(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_task tool call - spawn an agent to execute a task."""
    import asyncio
    import concurrent.futures
    import time
    from pathlib import Path

    # Import session module functions directly
    import glee.session as session_mod
    from glee.agents import registry
    from glee.config import get_project_config

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    project_path = Path(config.get("project", {}).get("path", "."))

    description: str = arguments.get("description", "")
    prompt: str = arguments.get("prompt", "")
    agent_name_arg: str | None = arguments.get("agent_name")
    agent_cli_arg: str | None = arguments.get("agent_cli")
    background: bool = arguments.get("background", False)
    session_id_arg: str | None = arguments.get("session_id")

    if not description or not prompt:
        return [TextContent(type="text", text="Both 'description' and 'prompt' are required.")]

    # Load or create session
    session: session_mod.Session | None = None
    if session_id_arg:
        session = session_mod.load_session(project_path, session_id_arg)
        if not session:
            return [TextContent(type="text", text=f"Session not found: {session_id_arg}")]
        # Add new prompt to session
        session_mod.add_message(project_path, session_id_arg, "user", prompt)

    # Agent selection - resolution order:
    # 1. agent_name provided → use subagent definition from .glee/agents/
    # 2. agent_cli provided → run CLI directly
    # 3. Neither provided → auto-select based on heuristics
    from glee.subagent import SubagentLoadError, load_subagent, render_prompt

    agent_cli: str  # CLI to use
    subagent_name: str | None = None  # For session tracking
    subagent_prompt: str | None = None  # Subagent system prompt

    if agent_name_arg:
        # Load subagent from .glee/agents/{agent_name}.yml
        try:
            subagent = load_subagent(project_path, agent_name_arg)
        except SubagentLoadError as e:
            return [TextContent(type="text", text=str(e))]

        subagent_name = agent_name_arg

        # Use subagent's preferred CLI, or auto-select if not specified
        if subagent.get("agent"):
            agent_cli = subagent["agent"]  # type: ignore[assignment]
        else:
            agent_cli = _select_agent(prompt)

        agent = registry.get(agent_cli)
        if not agent:
            return [TextContent(type="text", text=f"Unknown agent CLI: {agent_cli}. Available: codex, claude, gemini")]
        if not agent.is_available():
            # Try fallback if subagent's preferred CLI is not available
            for fallback in ["codex", "claude", "gemini"]:
                fallback_agent = registry.get(fallback)
                if fallback_agent and fallback_agent.is_available():
                    agent = fallback_agent
                    agent_cli = fallback
                    break
            else:
                return [TextContent(type="text", text=f"Agent CLI '{agent_cli}' is not installed.")]

        # Render prompt with subagent instructions
        subagent_prompt = render_prompt(subagent, prompt)

    elif agent_cli_arg:
        # Use specified CLI directly
        agent_cli = agent_cli_arg
        agent = registry.get(agent_cli)
        if not agent:
            return [TextContent(type="text", text=f"Unknown agent CLI: {agent_cli_arg}. Available: codex, claude, gemini")]
        if not agent.is_available():
            return [TextContent(type="text", text=f"Agent CLI '{agent_cli_arg}' is not installed.")]
    else:
        # Auto-select using heuristics
        agent_cli = _select_agent(prompt)
        agent = registry.get(agent_cli)

    if not agent:
        return [TextContent(type="text", text="No agent available. Install codex, claude, or gemini CLI.")]

    if not agent.is_available():
        # Try fallback agents
        for fallback in ["codex", "claude", "gemini"]:
            fallback_agent = registry.get(fallback)
            if fallback_agent and fallback_agent.is_available():
                agent = fallback_agent
                agent_cli = fallback
                break
        else:
            return [TextContent(type="text", text="No agent CLI available. Install codex, claude, or gemini.")]

    # Create session if not resuming
    if not session:
        session = session_mod.create_session(
            project_path, description, agent_cli, prompt, agent_name=subagent_name
        )

    # session is guaranteed to be non-None here (either loaded or created)
    assert session is not None
    current_session_id: str = session["session_id"]

    # Build full prompt with context
    # If using a subagent, use the rendered subagent prompt; otherwise use regular prompt
    effective_prompt = subagent_prompt if subagent_prompt else prompt
    full_prompt = _build_task_prompt(project_path, session, effective_prompt)

    # Run agent
    start_time = time.time()

    # TODO: Implement background execution
    if background:
        return [TextContent(type="text", text="Background execution not yet implemented.")]

    # Get running event loop for thread-safe async calls
    loop = asyncio.get_running_loop()

    def run_agent() -> tuple[str | None, str | None]:
        agent.project_path = project_path
        try:
            result = agent.run(prompt=full_prompt, stream=True)
            if result.error:
                return result.output, f"{result.error} (exit_code={result.exit_code})"
            return result.output, None
        except Exception as e:
            import traceback
            return None, f"{str(e)}\n{traceback.format_exc()}"

    # Run in thread to not block event loop
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        output, error = await loop.run_in_executor(executor, run_agent)

    duration_ms = int((time.time() - start_time) * 1000)

    # Complete session
    status = "error" if error else "completed"
    session_mod.complete_session(project_path, current_session_id, output or error or "", status)

    lines = [
        f"Task: {description}",
        f"Agent: {agent_cli}",
        f"Session: {current_session_id}",
        f"Duration: {duration_ms}ms",
        "",
    ]

    if error:
        lines.append(f"Error: {error}")
    if output:
        lines.append(output)

    return [TextContent(type="text", text="\n".join(lines))]


def _select_agent(prompt: str) -> str:
    """Select the best agent based on prompt content using simple heuristics."""
    from glee.agents import registry

    prompt_lower = prompt.lower()

    # Heuristics for agent selection
    heuristics: dict[str, list[str]] = {
        "gemini": [
            "search web", "google", "find online", "latest", "news",
            "research", "look up", "what is", "documentation", "search for",
        ],
        "codex": [
            "analyze code", "review", "find bugs", "refactor",
            "security", "performance", "fix", "debug", "code",
        ],
        "claude": [
            "summarize", "explain", "write", "draft", "quick",
            "simple", "help me understand",
        ],
    }

    for agent_name, keywords in heuristics.items():
        if any(kw in prompt_lower for kw in keywords):
            agent = registry.get(agent_name)
            if agent and agent.is_available():
                return agent_name

    # Fallback: first available
    for agent_name in ["codex", "claude", "gemini"]:
        agent = registry.get(agent_name)
        if agent and agent.is_available():
            return agent_name

    return "codex"  # Default


def _build_task_prompt(
    project_path: Path, session: dict[str, Any], new_prompt: str
) -> str:
    """Build the full prompt with context injection."""
    import glee.session as session_mod
    from glee.memory import Memory

    lines: list[str] = []

    # 1. Read AGENTS.md if exists
    agents_md = project_path / "AGENTS.md"
    if agents_md.exists():
        try:
            content = agents_md.read_text()
            lines.append("<project_instructions>")
            lines.append(content)
            lines.append("</project_instructions>")
            lines.append("")
        except Exception:
            pass

    # 2. Get relevant memories
    try:
        memory = Memory(str(project_path))
        # Search for memories relevant to the task
        results = memory.search(query=new_prompt, limit=5)
        memory.close()

        if results:
            lines.append("<project_context>")
            for r in results:
                lines.append(f"- [{r.get('category')}] {r.get('content')}")
            lines.append("</project_context>")
            lines.append("")
    except Exception:
        pass

    # 3. Add session context (previous conversation)
    context_prompt = session_mod.build_context_prompt(session, new_prompt)
    lines.append(context_prompt)

    return "\n".join(lines)


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
