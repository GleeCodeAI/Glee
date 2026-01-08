"""Glee MCP Server - Exposes Glee tools to Claude Code."""

import os
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
            description="Run multi-agent code review. Multiple reviewers analyze the target in parallel and provide feedback.",
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
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "glee_status":
        return await _handle_status()
    elif name == "glee_review":
        return await _handle_review(arguments)
    elif name == "glee_connect":
        return await _handle_connect(arguments)
    elif name == "glee_disconnect":
        return await _handle_disconnect(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _handle_status() -> list[TextContent]:
    """Handle glee_status tool call."""
    from glee.agents import registry
    from glee.config import get_connected_agents, get_project_config

    lines = []

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


async def _handle_review(arguments: dict) -> list[TextContent]:
    """Handle glee_review tool call."""
    import concurrent.futures
    from pathlib import Path

    from glee.agents import registry
    from glee.config import get_connected_agents, get_project_config

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    # Get reviewers
    reviewers = get_connected_agents(role="reviewer")
    if not reviewers:
        return [TextContent(type="text", text="No reviewers connected. Use glee_connect to add reviewers.")]

    # Parse target - flexible input
    target = arguments.get("target", ".")

    # Parse focus
    focus_str = arguments.get("focus", "")
    focus_list = [f.strip() for f in focus_str.split(",")] if focus_str else None

    lines = [f"Reviewing with {len(reviewers)} reviewer(s)...", f"Target: {target}", ""]

    # Run reviews
    def run_single_review(reviewer_config: dict) -> tuple[str, str | None, str | None]:
        name = reviewer_config.get("name", "unknown")
        command = reviewer_config.get("command")
        agent = registry.get(command) if command else None
        if not agent:
            return name, None, f"Command {command} not found"
        if not agent.is_available():
            return name, None, f"CLI {command} not installed"

        review_focus = focus_list or []
        config_focus = reviewer_config.get("focus")
        if config_focus:
            review_focus = list(set(review_focus + config_focus))

        try:
            result = agent.run_review(target=target, focus=review_focus if review_focus else None)
            return name, result.output, result.error
        except Exception as e:
            return name, None, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(reviewers)) as executor:
        futures = {executor.submit(run_single_review, r): r for r in reviewers}
        for future in concurrent.futures.as_completed(futures):
            agent_name, output, error = future.result()
            lines.append(f"=== {agent_name.upper()} ===")
            if error:
                lines.append(f"Error: {error}")
            elif output:
                lines.append(output)
            lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_connect(arguments: dict) -> list[TextContent]:
    """Handle glee_connect tool call."""
    from glee.agents import registry
    from glee.config import connect_agent, get_project_config

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    command = arguments.get("command")
    role = arguments.get("role")

    if command not in registry.agents:
        return [TextContent(type="text", text=f"Unknown command: {command}. Available: claude, codex, gemini")]

    if role not in ("coder", "reviewer", "judge"):
        return [TextContent(type="text", text=f"Invalid role: {role}. Valid: coder, reviewer, judge")]

    domain_str = arguments.get("domain", "")
    focus_str = arguments.get("focus", "")
    domain_list = [d.strip() for d in domain_str.split(",")] if domain_str else None
    focus_list = [f.strip() for f in focus_str.split(",")] if focus_str else None

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


async def _handle_disconnect(arguments: dict) -> list[TextContent]:
    """Handle glee_disconnect tool call."""
    from glee.config import disconnect_agent, get_project_config

    config = get_project_config()
    if not config:
        return [TextContent(type="text", text="Project not initialized. Run 'glee init' first.")]

    agent_name = arguments.get("agent")
    if not agent_name:
        return [TextContent(type="text", text="Agent name required.")]

    success = disconnect_agent(agent_name=agent_name)
    if success:
        return [TextContent(type="text", text=f"Disconnected {agent_name}")]
    else:
        return [TextContent(type="text", text=f"Agent {agent_name} was not connected")]


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
