"""Glee CLI - The Conductor for Your AI Orchestra."""

import os
from pathlib import Path
from typing import Any

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from glee.logging import get_agent_logger, setup_logging

app = typer.Typer(
    name="glee",
    help="""The Conductor for Your AI Orchestra

Orchestrate multiple AI coding agents (Claude, Codex, Gemini) with:
  - Multiple coders with domain specialization
  - Multiple reviewers with focus areas
  - Shared memory and context injection
  - Dispute resolution with judge role

Quick start:
  glee init                              Initialize project
  glee connect claude --role coder       Add a coder
  glee connect codex --role reviewer     Add a reviewer
  glee connect claude --role judge       Add a judge (for disputes)
  glee status                            View connected agents
  glee review src/                       Run multi-agent review
""",
    no_args_is_help=True,
)
console = Console()


def get_version() -> str:
    """Get the package version."""
    from importlib.metadata import version
    return version("glee")


@app.command()
def version():
    """Show Glee version."""
    console.print(f"glee {get_version()}")


@app.callback()
def main_callback() -> None:
    """Initialize logging for all commands."""
    project_path = Path(os.getcwd())
    glee_dir = project_path / ".glee"
    if glee_dir.exists():
        setup_logging(project_path)
        # Initialize agent logger for run tracking
        get_agent_logger(project_path)
    else:
        setup_logging(None)  # Console only


@app.command()
def start():
    """Start the Glee daemon."""
    console.print("[green]Starting Glee daemon...[/green]")
    # TODO: Implement daemon start
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def stop():
    """Stop the Glee daemon."""
    console.print("[red]Stopping Glee daemon...[/red]")
    # TODO: Implement daemon stop
    console.print("[yellow]Not implemented yet[/yellow]")


def check_mcp_registration(project_path: str | None = None) -> bool:
    """Check if Glee MCP server is registered in project's .mcp.json."""
    import json
    from pathlib import Path

    if project_path is None:
        project_path = os.getcwd()

    # Project-local MCP config
    mcp_config = Path(project_path) / ".mcp.json"
    if not mcp_config.exists():
        return False

    try:
        with open(mcp_config) as f:
            config = json.load(f)
        mcp_servers = config.get("mcpServers", {})
        return "glee" in mcp_servers
    except Exception:
        return False


@app.command()
def status():
    """Show Glee global status and current project status."""
    from glee.agents import registry
    from glee.config import get_connected_agents, get_project_config

    # === Global Status ===
    console.print(f"[bold]Glee v{get_version()}[/bold]")

    # CLI availability
    cli_agents = ["claude", "codex", "gemini"]
    for i, cli_name in enumerate(cli_agents):
        agent = registry.get(cli_name)
        is_last_cli = i == len(cli_agents) - 1
        prefix = "└─" if is_last_cli else "├─"
        if agent and agent.is_available():
            console.print(f"{prefix} {cli_name.title()} CLI: [green]found ✓[/green]")
        else:
            console.print(f"{prefix} {cli_name.title()} CLI: [dim]not found[/dim]")

    console.print()

    # === Project Status ===
    config = get_project_config()
    if not config:
        console.print("[dim]Current directory: not configured[/dim]")
        return

    project = config.get("project", {})
    console.print(f"[bold]Project: {project.get('name')}[/bold]")
    console.print(f"├─ Path: {project.get('path')}")

    # MCP Server registration (project-local)
    mcp_registered = check_mcp_registration()
    mcp_status = "[green]registered ✓[/green]" if mcp_registered else "[dim]not registered[/dim]"
    console.print(f"├─ MCP: {mcp_status}")

    # Show connected agents
    coders = get_connected_agents(role="coder")
    reviewers = get_connected_agents(role="reviewer")
    judges = get_connected_agents(role="judge")

    all_agents: list[str] = []
    for c in coders:
        cmd = c.get("command")
        agent = registry.get(cmd) if cmd else None
        available = "✓" if agent and agent.is_available() else "✗"
        domain = ", ".join(c.get("domain", [])) or "general"
        all_agents.append(f"[{available}] {c.get('name')} (coder) → {domain}")

    for r in reviewers:
        cmd = r.get("command")
        agent = registry.get(cmd) if cmd else None
        available = "✓" if agent and agent.is_available() else "✗"
        focus = ", ".join(r.get("focus", [])) or "general"
        all_agents.append(f"[{available}] {r.get('name')} (reviewer) → {focus}")

    for j in judges:
        cmd = j.get("command")
        agent = registry.get(cmd) if cmd else None
        available = "✓" if agent and agent.is_available() else "✗"
        all_agents.append(f"[{available}] {j.get('name')} (judge) → arbitration")

    if all_agents:
        console.print("└─ Agents:")
        for i, agent_line in enumerate(all_agents):
            is_last = i == len(all_agents) - 1
            prefix = "   └─" if is_last else "   ├─"
            console.print(f"{prefix} {agent_line}")
    else:
        console.print("└─ Agents: [dim]none connected[/dim]")


@app.command()
def agents():
    """List connected agents by role."""
    from glee.agents import registry

    table = Table(title="Registered Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Command", style="green")
    table.add_column("Capabilities", style="yellow")
    table.add_column("Available", style="magenta")

    for name, agent in registry.agents.items():
        available = "Yes" if agent.is_available() else "No"
        table.add_row(
            name,
            agent.command,
            ", ".join(agent.capabilities),
            available,
        )

    console.print(table)


@app.command()
def connect(
    command: str = typer.Argument(..., help="CLI command (claude, codex, gemini)"),
    role: str = typer.Option(..., "--role", "-r", help="Role: coder, reviewer, or judge"),
    domain: str | None = typer.Option(None, "--domain", "-d", help="Domain areas for coders (comma-separated)"),
    focus: str | None = typer.Option(None, "--focus", "-f", help="Focus areas for reviewers (comma-separated)"),
    priority: int | None = typer.Option(None, "--priority", "-p", help="Priority for coders (lower = higher priority)"),
):
    """Connect an agent with a role to the current project."""
    from glee.agents import registry
    from glee.config import connect_agent, get_project_config

    # Validate project is initialized
    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    # Validate command
    if command not in registry.agents:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print(f"Available: {', '.join(registry.agents.keys())}")
        raise typer.Exit(1)

    # Validate role
    if role not in ("coder", "reviewer", "judge"):
        console.print(f"[red]Invalid role: {role}[/red]")
        console.print("Valid roles: coder, reviewer, judge")
        raise typer.Exit(1)

    # Check CLI is available
    agent_instance = registry.agents[command]
    if not agent_instance.is_available():
        console.print(f"[yellow]Warning: {command} CLI is not installed[/yellow]")

    # Parse comma-separated values
    domain_list = [d.strip() for d in domain.split(",")] if domain else None
    focus_list = [f.strip() for f in focus.split(",")] if focus else None

    # Connect the agent
    agent_config = connect_agent(
        command=command,
        role=role,
        domain=domain_list,
        focus=focus_list,
        priority=priority,
    )

    logger.info(f"Connected agent {agent_config['name']} ({command}) as {role}")
    console.print(f"[green]Connected {agent_config['name']} ({command}) as {role}[/green]")
    if domain_list:
        console.print(f"  Domain: {', '.join(domain_list)}")
    if focus_list:
        console.print(f"  Focus: {', '.join(focus_list)}")
    if priority is not None:
        console.print(f"  Priority: {priority}")


@app.command()
def disconnect(
    agent: str = typer.Argument(..., help="Agent name (claude, codex, gemini)"),
    role: str = typer.Option(None, "--role", "-r", help="Role to disconnect (all if not specified)"),
):
    """Disconnect an agent from the current project."""
    from glee.config import disconnect_agent, get_project_config

    # Validate project is initialized
    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    # Disconnect the agent
    success = disconnect_agent(agent_name=agent, role=role)

    if success:
        if role:
            console.print(f"[green]Disconnected {agent} from {role} role[/green]")
        else:
            console.print(f"[green]Disconnected {agent} from all roles[/green]")
    else:
        console.print(f"[yellow]Agent {agent} was not connected[/yellow]")


@app.command()
def init(
    agent: str | None = typer.Argument(None, help="Primary agent (claude, codex, gemini, opencode, cursor, etc.)"),
    new_id: bool = typer.Option(False, "--new-id", help="Generate new project ID"),
):
    """Initialize Glee in current directory.

    Examples:
        glee init           # Prompts for agent choice
        glee init claude    # Integrate with Claude Code
        glee init codex     # Integrate with Codex
    """
    import os
    import uuid

    from glee.config import init_project

    valid_agents = [
        "claude", "codex", "gemini", "opencode", "crush",
        "mistral", "vibe", "cursor", "trae", "antigravity"
    ]

    # If no agent specified, prompt user
    if agent is None:
        console.print("[bold]Which coding agent do you primarily use?[/bold]")
        console.print("  1. claude       (Claude Code)")
        console.print("  2. codex        (OpenAI Codex)")
        console.print("  3. gemini       (Google Gemini)")
        console.print("  4. opencode     (OpenCode)")
        console.print("  5. crush        (Crush)")
        console.print("  6. mistral      (Mistral)")
        console.print("  7. vibe         (Vibe)")
        console.print("  8. cursor       (Cursor)")
        console.print("  9. trae         (Trae)")
        console.print(" 10. antigravity  (Antigravity)")
        console.print(" 11. none         (Skip agent integration)")
        console.print()
        choice = typer.prompt("Enter choice (1-11 or agent name)", default="1")

        choice_map = {
            "1": "claude", "2": "codex", "3": "gemini", "4": "opencode",
            "5": "crush", "6": "mistral", "7": "vibe", "8": "cursor",
            "9": "trae", "10": "antigravity", "11": None
        }
        if choice in choice_map:
            agent = choice_map[choice]
        elif choice.lower() in valid_agents:
            agent = choice.lower()
        elif choice.lower() == "none":
            agent = None
        else:
            console.print(f"[red]Invalid choice: {choice}[/red]")
            raise typer.Exit(1)

    # Validate agent if provided
    if agent is not None and agent not in valid_agents:
        console.print(f"[red]Unknown agent: {agent}[/red]")
        console.print(f"Valid agents: {', '.join(valid_agents)}")
        raise typer.Exit(1)

    project_path = os.getcwd()
    project_id = str(uuid.uuid4()) if new_id else None

    config = init_project(project_path, project_id, agent=agent)
    console.print(f"[green]Initialized Glee project:[/green]")
    console.print(f"  ID: {config['project']['id']}")
    console.print(f"  Path: {config['project']['path']}")
    console.print(f"  Config: .glee/config.yml")

    # Show agent integration status
    if agent == "claude":
        if config.get("_mcp_registered"):
            console.print(f"  MCP: [green].mcp.json created[/green]")
        else:
            console.print(f"  MCP: [dim].mcp.json already exists[/dim]")
        if config.get("_hook_registered"):
            console.print(f"  Hook: [green]context injection enabled[/green]")
        else:
            console.print(f"  Hook: [dim]already configured[/dim]")
    elif agent == "codex":
        console.print(f"  Codex: [yellow]integration not yet implemented[/yellow]")
    elif agent == "gemini":
        console.print(f"  Gemini: [yellow]integration not yet implemented[/yellow]")
    else:
        console.print(f"  Agent: [dim]no integration configured[/dim]")


@app.command()
def review(
    target: str | None = typer.Argument(None, help="What to review: file, directory, 'git:changes', 'git:staged', or description"),
    focus: str | None = typer.Option(None, "--focus", "-f", help="Focus areas (comma-separated: security, performance, etc.)"),
    reviewer: str | None = typer.Option(None, "--reviewer", "-r", help="Specific reviewer to use"),
) -> None:
    """Trigger multi-reviewer workflow."""
    import concurrent.futures

    from glee.agents import registry
    from glee.agents.base import AgentResult
    from glee.config import get_connected_agents, get_project_config
    from glee.dispatch import select_reviewers

    # Validate project is initialized
    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    # Default target
    review_target = target or "."

    # Get reviewers using dispatch module
    reviewers = select_reviewers()
    if not reviewers:
        console.print("[red]No reviewers connected. Use 'glee connect <command> --role reviewer' first.[/red]")
        raise typer.Exit(1)

    # Filter to specific reviewer if requested (by name or command)
    if reviewer:
        all_reviewers = get_connected_agents(role="reviewer")
        reviewers = [r for r in all_reviewers if r.get("name") == reviewer or r.get("command") == reviewer]
        if not reviewers:
            console.print(f"[red]Reviewer {reviewer} not connected[/red]")
            raise typer.Exit(1)

    # Parse focus areas
    focus_list = [f.strip() for f in focus.split(",")] if focus else None

    # Show review plan
    console.print("[bold]Review Plan[/bold]")
    console.print(f"  Target: {review_target}")
    console.print(f"  Reviewers: {', '.join(r.get('name', 'unknown') for r in reviewers)}")
    if focus_list:
        console.print(f"  Focus: {', '.join(focus_list)}")
    console.print()

    # Run reviews
    results: dict[str, dict[str, Any]] = {}

    def run_single_review(
        reviewer_config: dict[str, Any],
    ) -> tuple[str, AgentResult | None, str | None]:
        name = reviewer_config.get("name", "unknown")
        command = reviewer_config.get("command")
        agent = registry.get(command) if command else None
        if not agent:
            return name, None, f"Command {command} not found in registry"
        if not agent.is_available():
            return name, None, f"CLI {command} not installed"

        # Merge focus areas
        review_focus: list[str] = focus_list or []
        config_focus = reviewer_config.get("focus")
        if config_focus:
            review_focus = list(set(review_focus + config_focus))

        try:
            result = agent.run_review(target=review_target, focus=review_focus if review_focus else None)
            return name, result, None
        except Exception as e:
            return name, None, str(e)

    # Run reviews in parallel
    reviewer_names = [r.get('name', 'unknown') for r in reviewers]
    logger.info(f"Starting review with reviewers: {', '.join(reviewer_names)}")
    console.print("[green]Running reviews...[/green]")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(reviewers)) as executor:
        futures = {executor.submit(run_single_review, r): r for r in reviewers}
        for future in concurrent.futures.as_completed(futures):
            agent_name, result, error = future.result()
            results[agent_name] = {"result": result, "error": error}

    # Display results
    console.print()
    console.print("[bold]Review Results[/bold]")
    console.print("=" * 60)

    all_approved = True
    for agent_name, data in results.items():
        console.print(f"\n[bold cyan]{agent_name.upper()}[/bold cyan]")
        console.print("-" * 40)

        if data["error"]:
            console.print(f"[red]Error: {data['error']}[/red]")
            all_approved = False
        elif data["result"]:
            result = data["result"]
            if result.error:
                console.print(f"[red]Error: {result.error}[/red]")
                all_approved = False
            else:
                console.print(result.output)
                # Check for approval
                if "NEEDS_CHANGES" in result.output.upper():
                    all_approved = False

    console.print()
    console.print("=" * 60)
    if all_approved:
        logger.info("Review completed: all reviewers approved")
        console.print("[bold green]✓ All reviewers approved[/bold green]")
    else:
        logger.warning("Review completed: changes requested")
        console.print("[bold yellow]⚠ Changes requested[/bold yellow]")


@app.command()
def context(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only output if context exists (for hooks)"),
):
    """Get project context (for hook injection)."""
    import os

    from glee.config import get_project_context
    from glee.memory import Memory

    ctx = get_project_context()
    memory_ctx = ""

    # Get memory context if available
    try:
        memory = Memory(os.getcwd())
        memory_ctx = memory.get_context()
        memory.close()
    except Exception:
        pass  # Memory not initialized yet

    # In quiet mode, only output if there's actual content
    if quiet:
        if ctx or memory_ctx:
            if ctx:
                print(ctx)
            if memory_ctx:
                print(memory_ctx)
        return

    # Normal mode - show messages
    if not ctx and not memory_ctx:
        console.print("[yellow]No project context found. Run 'glee init' first.[/yellow]")
        return

    if ctx:
        console.print(ctx)
    if memory_ctx:
        console.print(memory_ctx)


@app.command()
def test_agent(
    agent: str = typer.Argument(..., help="Agent name (claude, codex, gemini)"),
    prompt: str = typer.Option("Say hello", "--prompt", "-p", help="Test prompt"),
):
    """Test an agent with a simple prompt."""
    from glee.agents import registry

    if agent not in registry.agents:
        console.print(f"[red]Unknown agent: {agent}[/red]")
        console.print(f"Available: {', '.join(registry.agents.keys())}")
        raise typer.Exit(1)

    agent_instance = registry.agents[agent]
    if not agent_instance.is_available():
        console.print(f"[red]Agent {agent} is not available[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Testing {agent}...[/green]")
    console.print(f"Prompt: {prompt}")
    console.print()

    result = agent_instance.run(prompt)
    console.print("[bold]Response:[/bold]")
    console.print(result.output)

    if result.error:
        console.print(f"[red]Error: {result.error}[/red]")


# Memory subcommands
memory_app = typer.Typer(help="Memory management commands")
app.add_typer(memory_app, name="memory")


@memory_app.command("add")
def memory_add(
    category: str = typer.Argument(..., help="Category (e.g., architecture, convention, review, decision, or custom)"),
    content: str = typer.Argument(..., help="Content to remember"),
):
    """Add a memory entry."""
    import os

    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        memory_id = memory.add(category=category, content=content)
        memory.close()
        console.print(f"[green]Added memory {memory_id} to {category}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Search query"),
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(5, "--limit", "-l", help="Max results"),
):
    """Search memories by semantic similarity."""
    import os

    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        results = memory.search(query=query, category=category, limit=limit)
        memory.close()

        if not results:
            console.print("[yellow]No memories found[/yellow]")
            return

        console.print(f"[bold]Found {len(results)} memories:[/bold]")
        for r in results:
            console.print(f"\n[cyan]{r.get('id')}[/cyan] ({r.get('category')})")
            console.print(f"  {r.get('content')}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("show")
def memory_show(
    category: str = typer.Argument(..., help="Category to show"),
):
    """Show all memories in a category."""
    import os

    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        results = memory.get_by_category(category)
        memory.close()

        if not results:
            console.print(f"[yellow]No memories in category '{category}'[/yellow]")
            return

        console.print(f"[bold]{category.title()} ({len(results)} entries):[/bold]")
        for r in results:
            console.print(f"\n[cyan]{r.get('id')}[/cyan] ({r.get('created_at')})")
            console.print(f"  {r.get('content')}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("delete")
def memory_delete(
    memory_id: str = typer.Argument(..., help="Memory ID to delete"),
):
    """Delete a specific memory entry."""
    import os

    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        deleted = memory.delete(memory_id)
        memory.close()

        if deleted:
            console.print(f"[green]Deleted memory {memory_id}[/green]")
        else:
            console.print(f"[yellow]Memory {memory_id} not found[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("clear")
def memory_clear(
    category: str | None = typer.Argument(None, help="Category to clear (all if not specified)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear memories. Clears all if no category specified."""
    import os

    from glee.memory import Memory

    # Confirm unless --force
    if not force:
        if category:
            msg = f"Clear all memories in '{category}'?"
        else:
            msg = "Clear ALL memories? This cannot be undone."
        if not typer.confirm(msg):
            console.print("[dim]Cancelled[/dim]")
            return

    try:
        memory = Memory(os.getcwd())
        count = memory.clear(category)
        memory.close()

        if category:
            console.print(f"[green]Cleared {count} memories from '{category}'[/green]")
        else:
            console.print(f"[green]Cleared all {count} memories[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("stats")
def memory_stats():
    """Show memory statistics."""
    import os

    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        stats = memory.stats()
        memory.close()

        console.print("[bold]Memory Statistics[/bold]")
        console.print(f"  Total: {stats['total']}")

        if stats["by_category"]:
            console.print()
            console.print("[bold]By Category:[/bold]")
            for cat, count in sorted(stats["by_category"].items()):
                console.print(f"  {cat}: {count}")

        if stats["oldest"]:
            oldest = stats["oldest"]
            if hasattr(oldest, "strftime"):
                oldest = oldest.strftime("%Y-%m-%d %H:%M")
            console.print(f"\n  Oldest: {oldest}")

        if stats["newest"]:
            newest = stats["newest"]
            if hasattr(newest, "strftime"):
                newest = newest.strftime("%Y-%m-%d %H:%M")
            console.print(f"  Newest: {newest}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Logs subcommands
logs_app = typer.Typer(help="Log management commands")
app.add_typer(logs_app, name="logs")


@logs_app.command("show")
def logs_show(
    level: str | None = typer.Option(None, "--level", "-l", help="Filter by level (DEBUG, INFO, WARNING, ERROR)"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search in message text"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
):
    """Show recent logs."""
    import os
    from pathlib import Path

    from glee.logging import query_logs

    project_path = Path(os.getcwd())
    results = query_logs(project_path, level=level, search=search, limit=limit)

    if not results:
        console.print("[yellow]No logs found[/yellow]")
        return

    console.print(f"[bold]Recent logs ({len(results)} entries):[/bold]\n")
    for log in results:
        level_color = {
            "DEBUG": "dim",
            "INFO": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
        }.get(log["level"], "white")

        timestamp = log["timestamp"][:19]  # Trim microseconds
        console.print(
            f"[dim]{timestamp}[/dim] [{level_color}]{log['level']:8}[/{level_color}] {log['message']}"
        )


@logs_app.command("stats")
def logs_stats():
    """Show log statistics."""
    import os
    from pathlib import Path

    from glee.logging import get_log_stats

    project_path = Path(os.getcwd())
    stats = get_log_stats(project_path)

    if stats["total"] == 0:
        console.print("[yellow]No logs found[/yellow]")
        return

    console.print("[bold]Log Statistics[/bold]")
    console.print(f"  Total: {stats['total']}")
    console.print()
    console.print("[bold]By Level:[/bold]")
    for level, count in sorted(stats["by_level"].items()):
        console.print(f"  {level}: {count}")


@logs_app.command("agents")
def logs_agents(
    agent: str | None = typer.Option(None, "--agent", "-a", help="Filter by agent (claude, codex, gemini)"),
    success_only: bool = typer.Option(False, "--success", "-s", help="Only show successful runs"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
):
    """Show agent run history."""
    import os
    from pathlib import Path

    from glee.logging import query_agent_logs

    project_path = Path(os.getcwd())
    results = query_agent_logs(project_path, agent=agent, success_only=success_only, limit=limit)

    if not results:
        console.print("[yellow]No agent logs found[/yellow]")
        return

    table = Table(title=f"Agent Logs (last {len(results)})")
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Time", style="dim", width=19)
    table.add_column("Agent", style="green", width=8)
    table.add_column("Duration", style="yellow", width=8)
    table.add_column("Status", width=8)
    table.add_column("Prompt", style="white", max_width=40, overflow="ellipsis")

    for log in results:
        timestamp = log["timestamp"][:19]
        duration = f"{log['duration_ms']}ms" if log["duration_ms"] else "-"
        status = "[green]OK[/green]" if log["success"] else "[red]FAIL[/red]"
        prompt = (log["prompt"][:37] + "...") if len(log["prompt"]) > 40 else log["prompt"]
        prompt = prompt.replace("\n", " ")

        table.add_row(
            log["id"],
            timestamp,
            log["agent"],
            duration,
            status,
            prompt,
        )

    console.print(table)


@logs_app.command("detail")
def logs_detail(
    log_id: str = typer.Argument(..., help="Log ID to show details for"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Show raw output instead of parsed"),
):
    """Show details of a specific agent log."""
    import os
    from pathlib import Path

    from glee.logging import get_agent_log

    project_path = Path(os.getcwd())
    log = get_agent_log(project_path, log_id)

    if not log:
        console.print(f"[red]Log {log_id} not found[/red]")
        raise typer.Exit(1)

    console.print("[bold]Agent Log Details[/bold]")
    console.print(f"  ID: [cyan]{log['id']}[/cyan]")
    console.print(f"  Time: {log['timestamp']}")
    console.print(f"  Agent: [green]{log['agent']}[/green]")
    console.print(f"  Duration: {log['duration_ms']}ms")
    status = "[green]Success[/green]" if log["success"] else "[red]Failed[/red]"
    console.print(f"  Status: {status}")
    console.print()

    console.print("[bold]Prompt:[/bold]")
    console.print(log["prompt"])
    console.print()

    if raw and log.get("raw"):
        console.print("[bold]Raw Output:[/bold]")
        console.print(log["raw"])
    elif log.get("output"):
        console.print("[bold]Output:[/bold]")
        console.print(log["output"])

    if log.get("error"):
        console.print()
        console.print("[bold red]Error:[/bold red]")
        console.print(log["error"])


@app.command()
def mcp():
    """Run Glee MCP server (for Claude Code integration)."""
    import asyncio

    from glee.mcp_server import run_server

    asyncio.run(run_server())


if __name__ == "__main__":
    app()
