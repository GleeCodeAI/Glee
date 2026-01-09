"""Glee MCP Server - Exposes Glee tools to Claude Code."""

from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("glee")


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
                },
                "required": [],
            },
        ),
        Tool(
            name="glee_connect",
            description="Connect an AI agent to the current project with a specific role.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "CLI command: claude, codex, or gemini",
                    },
                    "role": {
                        "type": "string",
                        "description": "Role: coder, reviewer, or judge",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain areas for coders (comma-separated, e.g., 'backend,api')",
                    },
                    "focus": {
                        "type": "string",
                        "description": "Focus areas for reviewers (comma-separated, e.g., 'security,performance')",
                    },
                },
                "required": ["command", "role"],
            },
        ),
        Tool(
            name="glee_disconnect",
            description="Disconnect an agent from the current project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "description": "Agent name to disconnect (e.g., 'claude-a1b2c3')",
                    },
                },
                "required": ["agent"],
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
            name="glee_memory_context",
            description="Get the full project memory context. Returns all remembered architecture decisions, conventions, reviews, and decisions formatted for injection into prompts.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="glee_memory_show",
            description="Show all memories in a specific category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category to show (any category name)",
                    },
                },
                "required": ["category"],
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
            name="glee_memory_clear",
            description="Clear all memories or memories in a specific category. Use with caution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category to clear. If not specified, clears ALL memories.",
                    },
                },
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
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    if name == "glee_status":
        return await _handle_status()
    elif name == "glee_review":
        return await _handle_review(arguments)
    elif name == "glee_connect":
        return await _handle_connect(arguments)
    elif name == "glee_disconnect":
        return await _handle_disconnect(arguments)
    elif name == "glee_memory_add":
        return await _handle_memory_add(arguments)
    elif name == "glee_memory_search":
        return await _handle_memory_search(arguments)
    elif name == "glee_memory_context":
        return await _handle_memory_context()
    elif name == "glee_memory_show":
        return await _handle_memory_show(arguments)
    elif name == "glee_memory_delete":
        return await _handle_memory_delete(arguments)
    elif name == "glee_memory_clear":
        return await _handle_memory_clear(arguments)
    elif name == "glee_memory_stats":
        return await _handle_memory_stats()
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _handle_status() -> list[TextContent]:
    """Handle glee_status tool call."""
    from glee.agents import registry
    from glee.config import get_connected_agents, get_project_config

    lines: list[str] = []

    # Global status
    lines.append("Glee Status")
    lines.append("=" * 40)
    lines.append("")
    lines.append("CLI Availability:")
    for cli_name in ["claude", "codex", "gemini"]:
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
        lines.append(f"Path: {project.get('path')}")
        lines.append("")

        # Agents
        coders = get_connected_agents(role="coder")
        reviewers = get_connected_agents(role="reviewer")
        judges = get_connected_agents(role="judge")

        if coders or reviewers or judges:
            lines.append("Connected Agents:")
            for c in coders:
                domain = ", ".join(c.get("domain", [])) or "general"
                lines.append(f"  {c.get('name')} (coder) -> {domain}")
            for r in reviewers:
                focus = ", ".join(r.get("focus", [])) or "general"
                lines.append(f"  {r.get('name')} (reviewer) -> {focus}")
            for j in judges:
                lines.append(f"  {j.get('name')} (judge) -> arbitration")
        else:
            lines.append("No agents connected.")
            lines.append("Use glee_connect to add agents.")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_review(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_review tool call."""
    import concurrent.futures
    from pathlib import Path

    from glee.agents import registry
    from glee.config import get_connected_agents, get_project_config
    from glee.logging import get_agent_logger

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    # Get project path for logging
    project_path = Path(config.get("project", {}).get("path", "."))

    # Initialize agent logger for this project
    get_agent_logger(project_path)

    # Get reviewers
    reviewers = get_connected_agents(role="reviewer")
    if not reviewers:
        # Show available agents so Claude can ask user which to use
        lines: list[str] = ["No reviewers connected.", ""]
        lines.append("Available agents:")
        for cli_name in ["claude", "codex", "gemini"]:
            agent = registry.get(cli_name)
            status = "installed" if agent and agent.is_available() else "not installed"
            lines.append(f"  - {cli_name}: {status}")
        lines.append("")
        lines.append("Ask the user which agent to use as a reviewer, then use glee_connect.")
        lines.append('Example: glee_connect(command="codex", role="reviewer", focus="security")')
        return [TextContent(type="text", text="\n".join(lines))]

    # Parse target - flexible input
    target: str = arguments.get("target", ".")

    # Parse focus
    focus_str: str = arguments.get("focus", "")
    focus_list: list[str] | None = [f.strip() for f in focus_str.split(",")] if focus_str else None

    lines: list[str] = [f"Reviewing with {len(reviewers)} reviewer(s)...", f"Target: {target}", ""]

    # Run reviews
    def run_single_review(reviewer_config: dict[str, Any]) -> tuple[str, str | None, str | None]:
        name = reviewer_config.get("name", "unknown")
        command = reviewer_config.get("command")
        agent = registry.get(command) if command else None
        if not agent:
            return name, None, f"Command {command} not found"
        if not agent.is_available():
            return name, None, f"CLI {command} not installed"

        # Set project_path for logging
        agent.project_path = project_path

        review_focus = focus_list or []
        config_focus = reviewer_config.get("focus")
        if config_focus:
            review_focus = list(set(review_focus + config_focus))

        try:
            result = agent.run_review(target=target, focus=review_focus if review_focus else None)
            # Include both output and error in response for visibility
            if result.error:
                return name, result.output, f"{result.error} (exit_code={result.exit_code})"
            return name, result.output, None
        except Exception as e:
            import traceback
            return name, None, f"{str(e)}\n{traceback.format_exc()}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(reviewers)) as executor:
        futures = {executor.submit(run_single_review, r): r for r in reviewers}
        for future in concurrent.futures.as_completed(futures):
            agent_name, output, error = future.result()
            lines.append(f"=== {agent_name.upper()} ===")
            if error:
                lines.append(f"Error: {error}")
            if output:
                lines.append(output)
            if not error and not output:
                lines.append("(no output)")
            lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_connect(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_connect tool call."""
    from glee.agents import registry
    from glee.config import connect_agent, get_project_config

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    command: str | None = arguments.get("command")
    role: str | None = arguments.get("role")

    if command not in registry.agents:
        return [TextContent(type="text", text=f"Unknown command: {command}. Available: claude, codex, gemini")]

    if role not in ("coder", "reviewer", "judge"):
        return [TextContent(type="text", text=f"Invalid role: {role}. Valid: coder, reviewer, judge")]

    domain_str: str = arguments.get("domain", "")
    focus_str: str = arguments.get("focus", "")
    domain_list: list[str] | None = [d.strip() for d in domain_str.split(",")] if domain_str else None
    focus_list: list[str] | None = [f.strip() for f in focus_str.split(",")] if focus_str else None

    agent_config = connect_agent(
        command=command,
        role=role,
        domain=domain_list,
        focus=focus_list,
    )

    lines = [f"Connected {agent_config['name']} ({command}) as {role}"]
    if domain_list:
        lines.append(f"Domain: {', '.join(domain_list)}")
    if focus_list:
        lines.append(f"Focus: {', '.join(focus_list)}")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_disconnect(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_disconnect tool call."""
    from glee.config import disconnect_agent, get_project_config

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    agent_name: str | None = arguments.get("agent")
    if not agent_name:
        return [TextContent(type="text", text="Agent name required.")]

    success = disconnect_agent(agent_name=agent_name)
    if success:
        return [TextContent(type="text", text=f"Disconnected {agent_name}")]
    else:
        return [TextContent(type="text", text=f"Agent {agent_name} was not connected")]


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


async def _handle_memory_context() -> list[TextContent]:
    """Handle glee_memory_context tool call."""
    from glee.config import get_project_config, get_project_context
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    lines: list[str] = []

    # Get agent context
    agent_ctx = get_project_context()
    if agent_ctx:
        lines.append(agent_ctx)
        lines.append("")

    # Get memory context
    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        memory_ctx = memory.get_context()
        memory.close()

        if memory_ctx:
            lines.append(memory_ctx)
    except Exception:
        pass  # Memory not initialized yet

    if not lines:
        return [TextContent(type="text", text="No project context available. Add memories with glee_memory_add.")]

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_memory_show(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_memory_show tool call."""
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
        results = memory.get_by_category(category)
        memory.close()

        if not results:
            return [TextContent(type="text", text=f"No memories in category '{category}'")]

        lines = [f"{category.title()} ({len(results)} entries):", ""]
        for r in results:
            created = r.get("created_at", "")
            if hasattr(created, "strftime"):
                created = created.strftime("%Y-%m-%d %H:%M")
            lines.append(f"[{r.get('id')}] ({created})")
            lines.append(f"  {r.get('content')}")
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error showing memories: {e}")]


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


async def _handle_memory_clear(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle glee_memory_clear tool call."""
    from glee.config import get_project_config
    from glee.memory import Memory

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    category: str | None = arguments.get("category")

    try:
        project_path = config.get("project", {}).get("path", ".")
        memory = Memory(project_path)
        count = memory.clear(category)
        memory.close()

        if category:
            return [TextContent(type="text", text=f"Cleared {count} memories from '{category}'")]
        else:
            return [TextContent(type="text", text=f"Cleared all {count} memories")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error clearing memories: {e}")]


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


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
