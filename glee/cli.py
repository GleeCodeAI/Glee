"""Glee CLI - Stage Manager for Your AI Orchestra."""

import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from glee.memory.capture import capture_memory

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from glee.logging import get_agent_logger, setup_logging

app = typer.Typer(
    name="glee",
    help="""Stage Manager for Your AI Orchestra

Glee orchestrates AI coding agents with shared memory and code review.

Quick start:
  glee init                              Initialize project
  glee config set reviewer.primary codex Set primary reviewer
  glee status                            View configuration
  glee review src/                       Run code review
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
        get_agent_logger(project_path)
    else:
        setup_logging(None)


@app.command()
def start():
    """Start the Glee daemon."""
    console.print("[green]Starting Glee daemon...[/green]")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def stop():
    """Stop the Glee daemon."""
    console.print("[red]Stopping Glee daemon...[/red]")
    console.print("[yellow]Not implemented yet[/yellow]")


def check_mcp_registration(project_path: str | None = None) -> bool:
    """Check if Glee MCP server is registered in project's .mcp.json."""
    import json

    if project_path is None:
        project_path = os.getcwd()

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
    """Show Glee status and current project configuration."""
    from glee.agents import registry
    from glee.config import get_project_config, get_reviewers

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

    # MCP Server registration
    mcp_registered = check_mcp_registration()
    mcp_status = "[green]registered ✓[/green]" if mcp_registered else "[dim]not registered[/dim]"
    console.print(f"├─ MCP: {mcp_status}")

    # Show reviewers
    reviewers = get_reviewers()
    primary = reviewers.get("primary", "codex")
    secondary = reviewers.get("secondary")

    primary_agent = registry.get(primary)
    primary_available = "✓" if primary_agent and primary_agent.is_available() else "✗"
    console.print(f"├─ Primary reviewer: [{primary_available}] {primary}")

    if secondary:
        secondary_agent = registry.get(secondary)
        secondary_available = "✓" if secondary_agent and secondary_agent.is_available() else "✗"
        console.print(f"└─ Secondary reviewer: [{secondary_available}] {secondary}")
    else:
        console.print("└─ Secondary reviewer: [dim]not set[/dim]")


@app.command()
def agents():
    """List available agent CLIs."""
    from glee.agents import registry

    table = Table(title="Available Agent CLIs")
    table.add_column("Name", style="cyan")
    table.add_column("Command", style="green")
    table.add_column("Available", style="magenta")

    for name, agent in registry.agents.items():
        available = "[green]Yes[/green]" if agent.is_available() else "[red]No[/red]"
        table.add_row(name, agent.command, available)

    console.print(table)


@app.command()
def lint(
    root: Path = typer.Option(Path("."), "--root", help="Project root containing .glee/tools"),
):
    """Validate tool manifests in .glee/tools."""
    from glee.tools.lint import lint_tools

    try:
        result = lint_tools(root)
    except FileNotFoundError as exc:
        console.print(f"[red]Schema not found: {exc}[/red]")
        raise typer.Exit(1)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Schema is invalid JSON: {exc}[/red]")
        raise typer.Exit(1)

    if not result.tool_files:
        console.print(f"[yellow]No tools found under {result.tools_dir}[/yellow]")
        raise typer.Exit(0)

    if result.errors:
        for error in result.errors:
            console.print(f"[red]{error}[/red]")
        console.print(f"[red]Found {len(result.errors)} schema error(s).[/red]")
        raise typer.Exit(1)

    console.print(f"[green]All tool manifests are valid ({len(result.tool_files)} tool(s)).[/green]")


# Config subcommands
config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


# Supported config keys
CONFIG_KEYS = {
    "reviewer.primary": "Primary reviewer CLI (codex, claude, gemini)",
    "reviewer.secondary": "Secondary reviewer CLI for second opinions",
}


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g., reviewer.primary)"),
    value: str = typer.Argument(..., help="Value to set"),
):
    """Set a configuration value.

    Examples:
        glee config set reviewer.primary codex
        glee config set reviewer.secondary gemini
    """
    from glee.agents import registry
    from glee.config import get_project_config, set_reviewer

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    if key not in CONFIG_KEYS:
        console.print(f"[red]Unknown config key: {key}[/red]")
        console.print("\nAvailable keys:")
        for k, desc in CONFIG_KEYS.items():
            console.print(f"  {k}: {desc}")
        raise typer.Exit(1)

    if key.startswith("reviewer."):
        tier = key.split(".")[1]  # "primary" or "secondary"

        # Validate command
        if value not in registry.agents:
            console.print(f"[red]Unknown reviewer: {value}[/red]")
            console.print(f"Available: {', '.join(registry.agents.keys())}")
            raise typer.Exit(1)

        # Check CLI is available
        agent_instance = registry.agents[value]
        if not agent_instance.is_available():
            console.print(f"[yellow]Warning: {value} CLI is not installed[/yellow]")

        try:
            set_reviewer(command=value, tier=tier)
            console.print(f"[green]Set {key} = {value}[/green]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@config_app.command("unset")
def config_unset(
    key: str = typer.Argument(..., help="Config key to unset"),
):
    """Unset a configuration value.

    Examples:
        glee config unset reviewer.secondary
    """
    from glee.config import clear_reviewer, get_project_config

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    if key == "reviewer.primary":
        console.print("[red]Cannot unset primary reviewer. Use 'glee config set' to change it.[/red]")
        raise typer.Exit(1)

    if key == "reviewer.secondary":
        if clear_reviewer(tier="secondary"):
            console.print(f"[green]Unset {key}[/green]")
        else:
            console.print(f"[yellow]{key} was not set[/yellow]")
        return

    console.print(f"[red]Unknown config key: {key}[/red]")
    raise typer.Exit(1)


@config_app.command("get")
def config_get(
    key: str | None = typer.Argument(None, help="Config key to get (or omit to show all)"),
):
    """Get configuration value(s).

    Examples:
        glee config get                    Show all config
        glee config get reviewer.primary   Show specific key
    """
    from glee.config import get_project_config, get_reviewers

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    reviewers = get_reviewers()

    if key is None:
        # Show all config
        console.print("[bold]Configuration:[/bold]")
        console.print(f"  reviewer.primary = {reviewers.get('primary', 'codex')}")
        secondary = reviewers.get("secondary")
        if secondary:
            console.print(f"  reviewer.secondary = {secondary}")
        else:
            console.print("  reviewer.secondary = [dim](not set)[/dim]")
        return

    if key == "reviewer.primary":
        console.print(reviewers.get("primary", "codex"))
    elif key == "reviewer.secondary":
        secondary = reviewers.get("secondary")
        if secondary:
            console.print(secondary)
        else:
            console.print("[dim](not set)[/dim]")
    else:
        console.print(f"[red]Unknown config key: {key}[/red]")
        raise typer.Exit(1)


@app.command()
def init(
    agent: str | None = typer.Argument(None, help="Primary agent (claude, codex, gemini, etc.)"),
    new_id: bool = typer.Option(False, "--new-id", help="Generate new project ID"),
):
    """Initialize Glee in current directory.

    Examples:
        glee init           # Prompts for agent choice
        glee init claude    # Integrate with Claude Code
    """
    import uuid

    from glee.config import init_project

    valid_agents = [
        "claude", "codex", "gemini", "opencode", "crush",
        "mistral", "vibe", "cursor", "trae", "antigravity"
    ]

    if agent is None:
        console.print("[bold]Which coding agent do you primarily use?[/bold]")
        console.print("  1. claude       (Claude Code)")
        console.print("  2. codex        (OpenAI Codex)")
        console.print("  3. gemini       (Google Gemini)")
        console.print("  4. opencode     (OpenCode)")
        console.print("  5. cursor       (Cursor)")
        console.print("  6. none         (Skip agent integration)")
        console.print()
        choice = typer.prompt("Enter choice (1-6 or agent name)", default="1")

        choice_map = {
            "1": "claude", "2": "codex", "3": "gemini",
            "4": "opencode", "5": "cursor", "6": None
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

    if agent is not None and agent not in valid_agents:
        console.print(f"[red]Unknown agent: {agent}[/red]")
        console.print(f"Valid agents: {', '.join(valid_agents)}")
        raise typer.Exit(1)

    project_path = os.getcwd()
    project_id = str(uuid.uuid4()) if new_id else None

    config = init_project(project_path, project_id, agent=agent)
    console.print("[green]Initialized Glee project:[/green]")
    console.print(f"  ID: {config['project']['id']}")
    console.print(f"  Config: .glee/config.yml")

    reviewers = config.get("reviewers", {})
    console.print(f"  Primary reviewer: {reviewers.get('primary', 'codex')}")

    if agent == "claude":
        if config.get("_mcp_registered"):
            console.print("  MCP: [green].mcp.json created[/green]")
        else:
            console.print("  MCP: [dim].mcp.json already exists[/dim]")
        if config.get("_hook_registered"):
            console.print("  Hook: [green]SessionStart hook registered[/green]")
        else:
            console.print("  Hook: [dim]already configured[/dim]")
    elif agent:
        console.print(f"  {agent.title()}: [yellow]integration not yet implemented[/yellow]")


@app.command()
def review(
    target: str | None = typer.Argument(None, help="What to review: file, directory, 'git:changes', 'git:staged', or description"),
    focus: str | None = typer.Option(None, "--focus", "-f", help="Focus areas (comma-separated: security, performance, etc.)"),
    second_opinion: bool = typer.Option(False, "--second-opinion", "-2", help="Also run secondary reviewer"),
) -> None:
    """Run code review with configured reviewer.

    By default runs primary reviewer only. Use --second-opinion to also run secondary.
    """
    from glee.agents import registry
    from glee.agents.base import AgentResult
    from glee.config import get_project_config
    from glee.dispatch import get_primary_reviewer, get_secondary_reviewer

    config = get_project_config()
    if not config:
        console.print("[red]Project not initialized. Run 'glee init' first.[/red]")
        raise typer.Exit(1)

    review_target = target or "."
    focus_list = [f.strip() for f in focus.split(",")] if focus else None

    # Get reviewers
    primary = get_primary_reviewer()
    reviewers_to_run = [primary]

    if second_opinion:
        secondary = get_secondary_reviewer()
        if secondary:
            reviewers_to_run.append(secondary)
        else:
            console.print("[yellow]Warning: No secondary reviewer configured[/yellow]")

    console.print("[bold]Review Plan[/bold]")
    console.print(f"  Target: {review_target}")
    console.print(f"  Reviewer(s): {', '.join(reviewers_to_run)}")
    if focus_list:
        console.print(f"  Focus: {', '.join(focus_list)}")
    console.print()

    logger.info(f"Starting review with: {', '.join(reviewers_to_run)}")
    console.print("[green]Running review...[/green]\n")

    results: dict[str, dict[str, Any]] = {}

    def run_single_review(reviewer_cli: str) -> tuple[str, AgentResult | None, str | None]:
        agent = registry.get(reviewer_cli)
        if not agent:
            return reviewer_cli, None, f"CLI {reviewer_cli} not found in registry"
        if not agent.is_available():
            return reviewer_cli, None, f"CLI {reviewer_cli} not installed"

        try:
            result = agent.run_review(target=review_target, focus=focus_list)
            return reviewer_cli, result, None
        except Exception as e:
            return reviewer_cli, None, str(e)

    # Run reviews (sequentially for now, could parallelize if both requested)
    for reviewer_cli in reviewers_to_run:
        name, result, error = run_single_review(reviewer_cli)
        results[name] = {"result": result, "error": error}

    # Display summary
    console.print()
    console.print("[bold]Review Summary[/bold]")
    console.print("=" * 60)

    all_approved = True
    for reviewer_name, data in results.items():
        if data["error"]:
            console.print(f"  {reviewer_name}: [red]Error - {data['error']}[/red]")
            all_approved = False
        elif data["result"]:
            result = data["result"]
            if result.error:
                console.print(f"  {reviewer_name}: [red]Error[/red]")
                all_approved = False
            else:
                if "NEEDS_CHANGES" in result.output.upper():
                    console.print(f"  {reviewer_name}: [yellow]Changes requested[/yellow]")
                    all_approved = False
                else:
                    console.print(f"  {reviewer_name}: [green]Approved[/green]")

    console.print()
    console.print("=" * 60)
    if all_approved:
        logger.info("Review completed: approved")
        console.print("[bold green]✓ Approved[/bold green]")
    else:
        logger.warning("Review completed: changes requested")
        console.print("[bold yellow]⚠ Changes requested[/bold yellow]")


@app.command()
def warmup():
    """Output session warmup context (memory, sessions, git)."""
    from glee.config import get_project_config
    from glee.warmup import build_warmup_text

    try:
        if not get_project_config():
            return
        output = build_warmup_text(os.getcwd())
        if not output:
            return
        console.print(output, markup=False, highlight=False)
    except Exception as e:
        console.print(f"Error: {e}", markup=False)
        raise typer.Exit(1)


@app.command("summarize-session")
def summarize_session(
    summary: str | None = typer.Option(None, "--summary", "-s", help="Short session summary"),
    background: bool = typer.Option(False, "--background", help="Suppress output"),
):
    """Summarize the session and store it in memory."""
    from glee.config import get_project_config
    from glee.session_summary import summarize_session as run_summary

    if not get_project_config():
        return

    try:
        result = run_summary(os.getcwd(), summary=summary)
        if background:
            return

        added = result.get("added", {})
        cleared = result.get("cleared", {})
        if cleared:
            console.print("[bold]Cleared:[/bold]")
            for cat, count in sorted(cleared.items()):
                console.print(f"  {cat}: {count}")
        if added:
            console.print("[bold]Added:[/bold]")
            for cat, count in sorted(added.items()):
                console.print(f"  {cat}: {count}")
        if not added and not cleared:
            console.print("[yellow]No entries captured[/yellow]")
    except Exception as e:
        if background:
            return
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Memory subcommands
memory_app = typer.Typer(help="Memory management commands")
app.add_typer(memory_app, name="memory")


@memory_app.command("ops")
def memory_ops(
    action: str = typer.Option(
        ...,
        "--action",
        "-a",
        help="Action: add, list, delete",
    ),
    category: str | None = typer.Option(None, "--category", "-c", help="Memory category"),
    content: str | None = typer.Option(None, "--content", help="Content to remember (add)"),
    by: str | None = typer.Option(None, "--by", help="Delete by: 'id' or 'category'"),
    value: str | None = typer.Option(None, "--value", help="The ID or category to delete"),
    metadata: str | None = typer.Option(None, "--metadata", help="JSON metadata (add)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results (list)"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm destructive actions"),
):
    """Perform memory operations (add, list, delete)."""
    from glee.memory import Memory

    action_key = action.strip().lower().replace("-", "_")
    allowed = {"add", "list", "delete"}
    if action_key not in allowed:
        console.print(f"[red]Invalid action '{action}'. Use one of: {', '.join(sorted(allowed))}.[/red]")
        raise typer.Exit(1)

    memory = None
    try:
        memory = Memory(os.getcwd())

        if action_key == "add":
            if not category or not content:
                console.print("[red]Both --category and --content are required for add.[/red]")
                raise typer.Exit(1)

            metadata_obj: dict[str, Any] | None = None
            if metadata is not None:
                try:
                    metadata_obj = json.loads(metadata)
                except json.JSONDecodeError as e:
                    console.print(f"[red]Invalid JSON for --metadata: {e}[/red]")
                    raise typer.Exit(1)
                if not isinstance(metadata_obj, dict):
                    console.print("[red]--metadata must be a JSON object.[/red]")
                    raise typer.Exit(1)

            memory_id_value = memory.add(category=category, content=content, metadata=metadata_obj)
            console.print(f"[green]Added memory {memory_id_value} to {category}[/green]")
            return

        if action_key == "list":
            if limit <= 0:
                limit = 50

            if category:
                results = memory.get_by_category(category)[:limit]
                if not results:
                    console.print(f"[yellow]No memories in category '{category}'[/yellow]")
                    return

                title = category.replace("-", " ").replace("_", " ").title()
                console.print(f"[bold]{title} ({len(results)} entries):[/bold]")
                for r in results:
                    console.print(f"\n[cyan]{r.get('id')}[/cyan] ({r.get('created_at')})")
                    console.print(f"  {r.get('content')}")
                return

            categories = memory.get_categories()
            if not categories:
                console.print("[yellow]No memories found[/yellow]")
                return

            console.print("[bold]All Memories:[/bold]\n")
            for cat in categories:
                results = memory.get_by_category(cat)[:limit]
                title = cat.replace("-", " ").replace("_", " ").title()
                console.print(f"[bold cyan]{title}[/bold cyan] ({len(results)} entries)")
                for r in results:
                    console.print(f"  [{r.get('id')}] {r.get('content')}")
                console.print()
            return

        if action_key == "delete":
            if not by or not value:
                console.print("[red]Both --by and --value are required for delete.[/red]")
                raise typer.Exit(1)

            if by == "id":
                deleted = memory.delete(value)
                if deleted:
                    console.print(f"[green]Deleted memory {value}[/green]")
                else:
                    console.print(f"[yellow]Memory {value} not found[/yellow]")
            elif by == "category":
                if not confirm:
                    if not typer.confirm(f"Delete all memories in '{value}'?"):
                        console.print("[dim]Cancelled[/dim]")
                        return
                count = memory.clear(value)
                console.print(f"[green]Deleted {count} memories from '{value}'[/green]")
            else:
                console.print("[red]--by must be 'id' or 'category'.[/red]")
                raise typer.Exit(1)
            return
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


@memory_app.command("capture")
def memory_capture(
    payload: str | None = typer.Option(
        None,
        "--json",
        "-j",
        help="JSON payload for structured capture (goal, constraints, decisions, open_loops, recent_changes).",
    ),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to a JSON file to capture.",
    ),
):
    """Capture structured memory from JSON payload."""
    if payload is None and file is None:
        console.print("[red]Provide --json or --file[/red]")
        raise typer.Exit(1)

    if payload is None and file is not None:
        try:
            payload = file.read_text()
        except OSError as e:
            console.print(f"[red]Error reading file: {e}[/red]")
            raise typer.Exit(1)

    if payload == "-":
        payload = sys.stdin.read()

    try:
        data = json.loads(payload or "")
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1)

    if not isinstance(data, dict):
        console.print("[red]Payload must be a JSON object[/red]")
        raise typer.Exit(1)

    try:
        result = capture_memory(os.getcwd(), cast(dict[str, Any], data), source="cli")
        added = result.get("added", {})
        cleared = result.get("cleared", {})
        if cleared:
            console.print("[bold]Cleared:[/bold]")
            for cat, count in sorted(cleared.items()):
                console.print(f"  {cat}: {count}")
        if added:
            console.print("[bold]Added:[/bold]")
            for cat, count in sorted(added.items()):
                console.print(f"  {cat}: {count}")
        if not added and not cleared:
            console.print("[yellow]No entries captured[/yellow]")
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


@memory_app.command("overview")
def memory_overview():
    """Show formatted memory overview (for LLM context)."""
    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        overview = memory.get_context()
        memory.close()

        if not overview:
            console.print("[yellow]No memories found[/yellow]")
            return

        console.print(overview)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("stats")
def memory_stats():
    """Show memory statistics."""
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
    level: str | None = typer.Option(None, "--level", "-l", help="Filter by level"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search in message text"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
):
    """Show recent logs."""
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

        timestamp = log["timestamp"][:19]
        console.print(
            f"[dim]{timestamp}[/dim] [{level_color}]{log['level']:8}[/{level_color}] {log['message']}"
        )


@logs_app.command("stats")
def logs_stats():
    """Show log statistics."""
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
    agent: str | None = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    success_only: bool = typer.Option(False, "--success", "-s", help="Only show successful runs"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
):
    """Show agent run history."""
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

        table.add_row(log["id"], timestamp, log["agent"], duration, status, prompt)

    console.print(table)


@logs_app.command("detail")
def logs_detail(
    log_id: str = typer.Argument(..., help="Log ID to show details for"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Show raw output"),
):
    """Show details of a specific agent log."""
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
