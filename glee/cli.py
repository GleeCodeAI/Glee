"""Glee CLI - Stage Manager for Your AI Orchestra."""

import json
import os
from pathlib import Path
from typing import Any, cast

import typer
from loguru import logger
from rich.console import Console, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from glee.logging import get_agent_logger, setup_logging

# Theme colors for consistent styling
class Theme:
    """Consistent color theme for CLI output."""
    PRIMARY = "cyan"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    MUTED = "dim"
    ACCENT = "magenta"
    INFO = "blue"
    HEADER = "bold cyan"
    TITLE = "bold white"


# Layout constants
LEFT_PAD = 2  # Left margin for all output


def padded(renderable: RenderableType, top: int = 1, bottom: int = 1) -> Padding:
    """Wrap a renderable with consistent padding (top, right, bottom, left)."""
    return Padding(renderable, (top, 0, bottom, LEFT_PAD))


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
    console.print(padded(Text.assemble(
        ("🎭 ", "bold"),
        ("Glee", f"bold {Theme.PRIMARY}"),
        (f" v{get_version()}", Theme.MUTED),
    ), bottom=0))
    line_width = max(20, (console.width - LEFT_PAD) // 2)
    console.print(padded(Text("─" * line_width, style=Theme.MUTED), top=0))


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


def check_hooks_registration(project_path: str | None = None) -> dict[str, bool]:
    """Check if Glee hooks are registered in .claude/settings.local.json."""
    import json

    if project_path is None:
        project_path = os.getcwd()

    settings_path = Path(project_path) / ".claude" / "settings.local.json"
    result = {"SessionStart": False, "SessionEnd": False, "PreCompact": False}

    if not settings_path.exists():
        return result

    try:
        with open(settings_path) as f:
            settings = json.load(f)
        hooks = settings.get("hooks", {})

        for hook_name in result:
            hook_list = hooks.get(hook_name, [])
            for hook_config in hook_list:
                inner_hooks = hook_config.get("hooks", [])
                for h in inner_hooks:
                    cmd = str(h.get("command", ""))
                    if "glee" in cmd:
                        result[hook_name] = True
                        break
    except Exception:
        pass

    return result


@app.command()
def status():
    """Show Glee status and current project configuration."""
    from glee.agents import registry
    from glee.config import get_project_config, get_reviewers

    # === Header ===
    console.print(padded(Text.assemble(
        ("🎭 ", "bold"),
        ("Glee", f"bold {Theme.PRIMARY}"),
        (f" v{get_version()}", Theme.MUTED),
    ), bottom=0))
    line_width = max(20, (console.width - LEFT_PAD) // 2)
    console.print(padded(Text("─" * line_width, style=Theme.MUTED), top=0, bottom=0))

    # === Agent CLIs ===
    cli_tree = Tree(f"[{Theme.HEADER}]🤖 Agent CLIs[/{Theme.HEADER}]")
    cli_agents = ["claude", "codex", "gemini"]
    for cli_name in cli_agents:
        agent = registry.get(cli_name)
        if agent and agent.is_available():
            cli_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {cli_name.title()}")
        else:
            cli_tree.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] {cli_name.title()} [{Theme.MUTED}]not found[/{Theme.MUTED}]")
    console.print(padded(cli_tree, top=0, bottom=0))

    # === Project Status ===
    config = get_project_config()
    if not config:
        console.print(padded(Panel(
            f"[{Theme.MUTED}]No project configured in current directory[/{Theme.MUTED}]\n"
            f"Run [{Theme.PRIMARY}]glee init <agent>[/{Theme.PRIMARY}] to get started",
            title="[dim]Project[/dim]",
            border_style=Theme.MUTED
        )))
        return

    project = config.get("project", {})
    project_tree = Tree(f"[{Theme.HEADER}]📁 {project.get('name')}[/{Theme.HEADER}]")

    # MCP Server registration
    mcp_registered = check_mcp_registration()
    if mcp_registered:
        project_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] MCP registered")
    else:
        project_tree.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] MCP [{Theme.MUTED}]not registered[/{Theme.MUTED}]")

    # Hooks registration
    hooks = check_hooks_registration()
    hooks_branch = project_tree.add(f"[{Theme.INFO}]🪝 Hooks[/{Theme.INFO}]")
    if hooks["SessionStart"]:
        hooks_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] SessionStart")
    else:
        hooks_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] SessionStart [{Theme.MUTED}]not set[/{Theme.MUTED}]")
    if hooks["SessionEnd"]:
        hooks_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] SessionEnd")
    else:
        hooks_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] SessionEnd [{Theme.MUTED}]not set[/{Theme.MUTED}]")
    if hooks["PreCompact"]:
        hooks_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] PreCompact")
    else:
        hooks_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] PreCompact [{Theme.MUTED}]not set[/{Theme.MUTED}]")

    # Show reviewers
    reviewers = get_reviewers()
    primary = reviewers.get("primary", "codex")
    secondary = reviewers.get("secondary")

    reviewer_branch = project_tree.add(f"[{Theme.INFO}]👥 Reviewers[/{Theme.INFO}]")
    primary_agent = registry.get(primary)
    if primary_agent and primary_agent.is_available():
        reviewer_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Primary: [{Theme.PRIMARY}]{primary}[/{Theme.PRIMARY}]")
    else:
        reviewer_branch.add(f"[{Theme.WARNING}]![/{Theme.WARNING}] Primary: [{Theme.PRIMARY}]{primary}[/{Theme.PRIMARY}] [{Theme.MUTED}]not available[/{Theme.MUTED}]")

    if secondary:
        secondary_agent = registry.get(secondary)
        if secondary_agent and secondary_agent.is_available():
            reviewer_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Secondary: [{Theme.ACCENT}]{secondary}[/{Theme.ACCENT}]")
        else:
            reviewer_branch.add(f"[{Theme.WARNING}]![/{Theme.WARNING}] Secondary: [{Theme.ACCENT}]{secondary}[/{Theme.ACCENT}] [{Theme.MUTED}]not available[/{Theme.MUTED}]")
    else:
        reviewer_branch.add(f"[{Theme.MUTED}]○ Secondary: not set[/{Theme.MUTED}]")

    console.print(padded(project_tree, top=0))


@app.command()
def agents():
    """List available agent CLIs."""
    from glee.agents import registry

    table = Table(
        title="🤖 Available Agent CLIs",
        title_style=Theme.HEADER,
        border_style=Theme.MUTED,
        header_style=f"bold {Theme.PRIMARY}",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("Agent", style=Theme.PRIMARY)
    table.add_column("Command", style=Theme.MUTED)
    table.add_column("Status", justify="center")

    for name, agent in registry.agents.items():
        if agent.is_available():
            status = Text("● Ready", style=Theme.SUCCESS)
        else:
            status = Text("○ Not found", style=Theme.MUTED)
        table.add_row(name.title(), agent.command, status)

    console.print(padded(table))


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
        from glee.config import get_autonomy_config

        config_tree = Tree(f"[{Theme.HEADER}]⚙️  Configuration[/{Theme.HEADER}]")

        # Autonomy (first)
        try:
            autonomy = get_autonomy_config()
            autonomy_branch = config_tree.add(f"[{Theme.INFO}]🤖 Autonomy[/{Theme.INFO}]")
            autonomy_branch.add(f"[{Theme.MUTED}]level:[/{Theme.MUTED}] [{Theme.PRIMARY}]{autonomy.level}[/{Theme.PRIMARY}]")

            if autonomy.checkpoint_policy:
                policy_branch = autonomy_branch.add(f"[{Theme.MUTED}]checkpoint_policy:[/{Theme.MUTED}]")
                for severity, action in autonomy.checkpoint_policy.items():
                    policy_branch.add(f"[{Theme.MUTED}]{severity}:[/{Theme.MUTED}] [{Theme.ACCENT}]{action}[/{Theme.ACCENT}]")

            if autonomy.require_approval_for:
                autonomy_branch.add(f"[{Theme.MUTED}]require_approval_for:[/{Theme.MUTED}] [{Theme.ACCENT}]{', '.join(autonomy.require_approval_for)}[/{Theme.ACCENT}]")
        except Exception:
            pass  # No autonomy config set

        # Reviewers
        reviewer_branch = config_tree.add(f"[{Theme.INFO}]👥 Reviewers[/{Theme.INFO}]")
        reviewer_branch.add(f"[{Theme.MUTED}]primary:[/{Theme.MUTED}] [{Theme.PRIMARY}]{reviewers.get('primary', 'codex')}[/{Theme.PRIMARY}]")
        secondary = reviewers.get("secondary")
        if secondary:
            reviewer_branch.add(f"[{Theme.MUTED}]secondary:[/{Theme.MUTED}] [{Theme.ACCENT}]{secondary}[/{Theme.ACCENT}]")
        else:
            reviewer_branch.add(f"[{Theme.MUTED}]secondary:[/{Theme.MUTED}] [{Theme.MUTED}]not set[/{Theme.MUTED}]")

        console.print(padded(config_tree))
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


@config_app.command("list")
def config_list():
    """List all configuration values.

    Alias for 'glee config get' without arguments.
    """
    config_get(key=None)


@app.command()
def init(
    agent: str = typer.Argument(..., help="Primary agent: claude, codex, gemini, cursor, etc."),
    new_id: bool = typer.Option(False, "--new-id", help="Generate new project ID"),
):
    """Initialize Glee in current directory.

    Examples:
        glee init claude    # Integrate with Claude Code (installs SessionStart/SessionEnd hooks)
        glee init codex     # Integrate with Codex CLI
        glee init gemini    # Integrate with Gemini CLI
    """
    import uuid

    from glee.config import init_project

    valid_agents = [
        "claude", "codex", "gemini", "opencode", "crush",
        "mistral", "vibe", "cursor", "trae", "antigravity"
    ]

    if agent not in valid_agents:
        console.print(padded(Panel(
            f"Unknown agent: [{Theme.ERROR}]{agent}[/{Theme.ERROR}]\n\n"
            f"Valid agents: [{Theme.PRIMARY}]{', '.join(valid_agents)}[/{Theme.PRIMARY}]",
            title=f"[{Theme.ERROR}]Error[/{Theme.ERROR}]",
            border_style=Theme.ERROR
        )))
        raise typer.Exit(1)

    project_path = os.getcwd()
    project_id = str(uuid.uuid4()) if new_id else None

    config = init_project(project_path, project_id, agent=agent)

    # Build success tree
    init_tree = Tree(f"[{Theme.SUCCESS}]✓ Initialized Glee project[/{Theme.SUCCESS}]")
    init_tree.add(f"[{Theme.MUTED}]ID:[/{Theme.MUTED}] [{Theme.PRIMARY}]{config['project']['id'][:8]}...[/{Theme.PRIMARY}]")
    init_tree.add(f"[{Theme.MUTED}]Config:[/{Theme.MUTED}] .glee/config.yml")

    reviewers = config.get("reviewers", {})
    init_tree.add(f"[{Theme.MUTED}]Primary reviewer:[/{Theme.MUTED}] [{Theme.PRIMARY}]{reviewers.get('primary', 'codex')}[/{Theme.PRIMARY}]")

    if agent == "claude":
        integration_branch = init_tree.add(f"[{Theme.INFO}]Claude integration[/{Theme.INFO}]")
        if config.get("_mcp_registered"):
            integration_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] MCP: .mcp.json created")
        else:
            integration_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] MCP: already exists")
        if config.get("_hook_registered"):
            integration_branch.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Hooks: SessionStart + SessionEnd")
        else:
            integration_branch.add(f"[{Theme.MUTED}]○[/{Theme.MUTED}] Hooks: already configured")
    else:
        init_tree.add(f"[{Theme.WARNING}]![/{Theme.WARNING}] {agent.title()}: hook integration not yet implemented")

    console.print(padded(init_tree))


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

    # Review plan panel
    plan_content = Text()
    plan_content.append("Target: ", style=Theme.MUTED)
    plan_content.append(f"{review_target}\n", style=Theme.PRIMARY)
    plan_content.append("Reviewers: ", style=Theme.MUTED)
    plan_content.append(f"{', '.join(reviewers_to_run)}", style=Theme.ACCENT)
    if focus_list:
        plan_content.append("\nFocus: ", style=Theme.MUTED)
        plan_content.append(f"{', '.join(focus_list)}", style=Theme.INFO)

    console.print(Panel(plan_content, title=f"[{Theme.HEADER}]📋 Review Plan[/{Theme.HEADER}]", border_style=Theme.PRIMARY))
    console.print()

    logger.info(f"Starting review with: {', '.join(reviewers_to_run)}")
    console.print(f"[{Theme.INFO}]Running review...[/{Theme.INFO}]")
    console.print()

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
    console.print(Rule(f"[{Theme.HEADER}]Review Summary[/{Theme.HEADER}]", style=Theme.MUTED))
    console.print()

    all_approved = True
    summary_tree = Tree(f"[{Theme.INFO}]📊 Results[/{Theme.INFO}]")
    for reviewer_name, data in results.items():
        if data["error"]:
            summary_tree.add(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] {reviewer_name}: [{Theme.ERROR}]{data['error']}[/{Theme.ERROR}]")
            all_approved = False
        elif data["result"]:
            result = data["result"]
            if result.error:
                summary_tree.add(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] {reviewer_name}: [{Theme.ERROR}]Error[/{Theme.ERROR}]")
                all_approved = False
            else:
                if "NEEDS_CHANGES" in result.output.upper():
                    summary_tree.add(f"[{Theme.WARNING}]![/{Theme.WARNING}] {reviewer_name}: [{Theme.WARNING}]Changes requested[/{Theme.WARNING}]")
                    all_approved = False
                else:
                    summary_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {reviewer_name}: [{Theme.SUCCESS}]Approved[/{Theme.SUCCESS}]")

    console.print(summary_tree)
    console.print()

    if all_approved:
        logger.info("Review completed: approved")
        console.print(Panel(
            f"[{Theme.SUCCESS}]✓ All reviewers approved[/{Theme.SUCCESS}]",
            border_style=Theme.SUCCESS,
            padding=(0, 2)
        ))
    else:
        logger.warning("Review completed: changes requested")
        console.print(Panel(
            f"[{Theme.WARNING}]⚠ Changes requested[/{Theme.WARNING}]",
            border_style=Theme.WARNING,
            padding=(0, 2)
        ))


@app.command("warmup-session")
def warmup_session():
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
    from_source: str = typer.Option(..., "--from", help="Agent to use: 'claude', 'codex', 'gemini'"),
    session_id: str | None = typer.Option(None, "--session-id", help="Session ID (prints only, no save)"),
):
    """Summarize the session using an LLM.

    Uses the specified agent to generate structured memory (goal, decisions, open_loops, summary).

    Examples:
        # From SessionEnd hook (stdin) → saves to DB
        glee summarize-session --from=claude

        # Manual with session ID → prints only, no save
        glee summarize-session --from=claude --session-id=abc123
    """
    import sys
    from datetime import datetime
    from pathlib import Path

    from glee.agents import registry
    from glee.claude_session import (
        format_conversation_for_summary,
        get_claude_session_file,
        parse_claude_session,
    )
    from glee.config import get_project_config
    from glee.memory.capture import capture_memory

    # Set up logging to .glee/stream_logs/
    log_file: Path | None = None
    glee_dir = Path(os.getcwd()) / ".glee"
    if glee_dir.exists():
        log_dir = glee_dir / "stream_logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"summarize-session-{datetime.now().strftime('%Y%m%d')}.log"

    def log(msg: str) -> None:
        if log_file:
            with open(log_file, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] {msg}\n")

    log(f"summarize-session started with --from={from_source}")

    # Currently only Claude is supported for session summarization
    if from_source != "claude":
        log(f"Agent '{from_source}' is not supported for session summarization")
        console.print(f"[red]Agent '{from_source}' is not supported. Only 'claude' is currently supported for session summarization.[/red]")
        return

    try:
        # Get the agent
        agent = registry.get(from_source)
        if not agent:
            log(f"Unknown agent: {from_source}")
            console.print(f"[red]Unknown agent: {from_source}[/red]")
            return

        if not agent.is_available():
            log(f"Agent '{from_source}' is not available")
            console.print(f"[red]Agent '{from_source}' is not available[/red]")
            return

        session_file: Path | None = None
        effective_session_id: str | None = None
        save_to_db = False

        # Option 1: --session-id provided (manual - print only)
        if session_id:
            log(f"Manual mode with session_id={session_id}")
            session_file = get_claude_session_file(os.getcwd(), session_id)
            if not session_file:
                log(f"Session not found: {session_id}")
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)
            effective_session_id = session_id
            save_to_db = False

        # Option 2: Read from stdin (hook mode - save to DB)
        else:
            if sys.stdin.isatty():
                log("No stdin data (tty)")
                console.print("[red]No stdin data. Use --session-id or run from a SessionEnd hook.[/red]")
                return

            transcript_path: str | None = None
            stdin_session_id: str | None = None

            try:
                stdin_data = sys.stdin.read()
                log(f"Read stdin: {len(stdin_data)} bytes")
                if stdin_data.strip():
                    hook_data = json.loads(stdin_data)
                    transcript_path = hook_data.get("transcript_path")
                    stdin_session_id = hook_data.get("session_id")
                    log(f"Hook data: session_id={stdin_session_id}, transcript_path={transcript_path}")
            except (json.JSONDecodeError, OSError) as e:
                log(f"Failed to parse stdin JSON: {e}")
                console.print(f"[red]Failed to parse stdin JSON: {e}[/red]")
                return

            if not transcript_path:
                log("No transcript_path in stdin")
                console.print("[red]No transcript_path in stdin. Expected SessionEnd hook data.[/red]")
                return

            session_file = Path(transcript_path).expanduser()
            effective_session_id = stdin_session_id
            save_to_db = True

        if not session_file or not session_file.exists():
            log(f"Session file not found: {session_file}")
            console.print("[yellow]No session file found[/yellow]")
            return

        log(f"Parsing session file: {session_file}")
        conversation = parse_claude_session(session_file)
        if not conversation or not conversation["messages"]:
            log("No conversation found in session")
            console.print("[yellow]No conversation found in session[/yellow]")
            return

        if not effective_session_id:
            effective_session_id = conversation["session_id"]

        log(f"Conversation has {len(conversation['messages'])} messages")

        def find_project_root(start: Path) -> Path | None:
            for candidate in [start] + list(start.parents):
                if (candidate / ".glee" / "config.yml").exists():
                    return candidate
            return None

        project_hint = conversation.get("project_path") or os.getcwd()
        project_path = Path(project_hint).expanduser()
        if project_path.is_file():
            project_path = project_path.parent
        project_root = find_project_root(project_path.resolve())
        if not project_root or not get_project_config(str(project_root)):
            log(f"No project config found for {project_path}")
            console.print("[red]No project config found. Run 'glee init' in the project.[/red]")
            return

        if log_file is None or (project_root / ".glee" / "stream_logs") != log_file.parent:
            log_dir = project_root / ".glee" / "stream_logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"summarize-session-{datetime.now().strftime('%Y%m%d')}.log"

        # Format conversation for the agent
        conversation_text = format_conversation_for_summary(conversation, max_chars=8000)

        console.print(f"[dim]Generating structured summary using {from_source}...[/dim]")
        log(f"Calling {from_source} to generate summary")

        # Prompt for structured output
        prompt = f"""Analyze this coding session and extract structured information.

Conversation:
{conversation_text}

Respond in this exact JSON format (no markdown, just raw JSON):
{{
  "goal": "The main task or objective (1 sentence)",
  "decisions": ["Decision 1", "Decision 2"],
  "open_loops": ["Unfinished task 1", "Unfinished task 2"],
  "summary": "2-3 sentence summary of what was accomplished"
}}

If a field doesn't apply, use an empty string or empty array. Be concise."""

        result = agent.run(prompt)
        if result.error:
            log(f"Agent error: {result.error}")
            console.print(f"[red]Error: {result.error}[/red]")
            return

        log(f"Agent returned {len(result.output)} chars")

        # Parse the JSON response
        output = result.output.strip()
        # Remove markdown code blocks if present
        if output.startswith("```"):
            output = output.split("\n", 1)[1] if "\n" in output else output
            if output.endswith("```"):
                output = output.rsplit("```", 1)[0]
            output = output.strip()

        structured: dict[str, Any] = {}
        try:
            parsed = json.loads(output)
            if not isinstance(parsed, dict):
                log(f"JSON is not a dict (got {type(parsed).__name__}), using raw output")
                console.print("[yellow]Response is not a JSON object, using raw output[/yellow]")
                structured = {"summary": output}
            else:
                structured = cast(dict[str, Any], parsed)
                log(f"Parsed structured response: {list(structured.keys())}")
        except json.JSONDecodeError as e:
            log(f"JSON parse error: {e}, using raw output")
            console.print("[yellow]Could not parse structured response, using raw output[/yellow]")
            structured = {"summary": output}

        if save_to_db:
            # Save to memory
            log(f"Saving to DB with session_id={effective_session_id}")
            capture_result = capture_memory(
                str(project_root),
                structured,
                source="summarize_session",
                session_id=effective_session_id,
            )

            added = capture_result.get("added", {})
            cleared = capture_result.get("cleared", {})
            log(f"Saved: added={added}, cleared={cleared}")

            if cleared:
                console.print("[bold]Cleared:[/bold]")
                for cat, count in sorted(cleared.items()):
                    console.print(f"  {cat}: {count}")
            if added:
                console.print("[bold]Added:[/bold]")
                for cat, count in sorted(added.items()):
                    console.print(f"  {cat}: {count}")
        else:
            # Print only
            log("Print mode (no save)")
            console.print("\n[bold]Structured Summary:[/bold]")
            if structured.get("goal"):
                console.print(f"[cyan]Goal:[/cyan] {structured['goal']}")
            if structured.get("decisions"):
                console.print("[cyan]Decisions:[/cyan]")
                for d in structured["decisions"]:
                    console.print(f"  • {d}")
            if structured.get("open_loops"):
                console.print("[cyan]Open Loops:[/cyan]")
                for o in structured["open_loops"]:
                    console.print(f"  • {o}")
            if structured.get("summary"):
                console.print(f"[cyan]Summary:[/cyan] {structured['summary']}")

        log("summarize-session completed successfully")
    except Exception as e:
        log(f"Exception: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Memory subcommands
memory_app = typer.Typer(help="Memory management commands")
app.add_typer(memory_app, name="memory")


@memory_app.command("add")
def memory_add(
    category: str = typer.Option(..., "--category", "-c", help="Memory category"),
    content: str = typer.Option(..., "--content", help="Content to remember"),
    metadata: str | None = typer.Option(None, "--metadata", help="JSON metadata"),
):
    """Add a memory entry."""
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

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

        memory_id = memory.add(category=category, content=content, metadata=metadata_obj)
        console.print(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Added memory [{Theme.PRIMARY}]{memory_id}[/{Theme.PRIMARY}] to [{Theme.ACCENT}]{category}[/{Theme.ACCENT}]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


def _format_relative_time(dt: Any) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')."""
    from datetime import datetime

    if dt is None:
        return "unknown"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt

    now = datetime.now()
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        now = datetime.now(dt.tzinfo)

    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} min{'s' if mins != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime("%b %d, %Y")


def _render_session_summaries(results: list[dict[str, Any]]) -> None:
    """Render session summaries in a tree format."""
    tree = Tree(f"[{Theme.HEADER}]🧠 Sessions[/{Theme.HEADER}]")

    for r in results:
        created_at = r.get("created_at")
        relative_time = _format_relative_time(created_at)

        # Parse metadata for session_id
        metadata_raw = r.get("metadata", {})
        metadata: dict[str, Any] = {}
        if isinstance(metadata_raw, str):
            try:
                parsed = json.loads(metadata_raw)
                if isinstance(parsed, dict):
                    metadata = cast(dict[str, Any], parsed)
            except json.JSONDecodeError:
                pass
        elif isinstance(metadata_raw, dict):
            metadata = cast(dict[str, Any], metadata_raw)

        session_id: str = str(metadata.get("session_id", "") or "")

        # Session branch with ID and time
        if session_id:
            session_label = f"[{Theme.ACCENT}]{session_id[:12]}[/{Theme.ACCENT}]  [{Theme.MUTED}]{relative_time}[/{Theme.MUTED}]"
        else:
            session_label = f"[{Theme.MUTED}]{r.get('id', '?')}[/{Theme.MUTED}]  [{Theme.MUTED}]{relative_time}[/{Theme.MUTED}]"

        session_branch = tree.add(session_label)

        # Content as child
        content = r.get("content", "").strip()
        if content:
            session_branch.add(f"[default]{content}[/default]")

    # Use Panel for consistent padding on all sides
    console.print(Padding(
        Panel(tree, border_style=Theme.MUTED, padding=(0, 2)),
        (1, 0, 0, LEFT_PAD)
    ))


@memory_app.command("list")
def memory_list(
    full: bool = typer.Option(False, "--full", "-f", help="Show full content"),
):
    """List memories."""
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

        categories = memory.get_categories()
        if not categories:
            console.print(f"[{Theme.WARNING}]No memories found[/{Theme.WARNING}]")
            return

        memory_tree = Tree(f"[{Theme.HEADER}]🧠 All Memories[/{Theme.HEADER}]")
        for cat in categories:
            results = memory.get_by_category(cat)
            title = cat.replace("-", " ").replace("_", " ").title()
            cat_branch = memory_tree.add(f"[{Theme.ACCENT}]{title}[/{Theme.ACCENT}] [{Theme.MUTED}]({len(results)})[/{Theme.MUTED}]")
            for r in results:
                mem_id = r.get('id', '')[:8]
                content = r.get('content', '')
                if not full and len(content) > 60:
                    content = content[:60] + "..."
                cat_branch.add(f"[{Theme.MUTED}]{mem_id}[/{Theme.MUTED}] {content}")
        console.print(padded(memory_tree))
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


@memory_app.command("latest")
def memory_latest(
    limit: int = typer.Option(1, "--limit", "-l", help="Number of recent memories to show"),
):
    """Show the most recent memory entries.

    Examples:
        glee memory latest           Show the most recent memory
        glee memory latest -l 5      Show the 5 most recent memories
    """
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

        if limit <= 0:
            limit = 1

        results = memory.get_latest(limit=limit)
        if not results:
            console.print(f"[{Theme.WARNING}]No memories found[/{Theme.WARNING}]")
            return

        # Check if all results are session_summary category
        if all(r.get("category") == "session_summary" for r in results):
            _render_session_summaries(results)
            return

        # Generic rendering for mixed categories
        console.print()
        title = "Latest Memory" if limit == 1 else f"Latest {len(results)} Memories"
        console.print(f"[{Theme.HEADER}]{title}[/{Theme.HEADER}]")
        console.print()

        for r in results:
            category = r.get("category", "unknown")
            relative_time = _format_relative_time(r.get("created_at"))

            header = Text()
            header.append("● ", style=Theme.PRIMARY)
            header.append(f"{r.get('id', '?')}", style=f"bold {Theme.PRIMARY}")
            header.append("  ", style="default")
            header.append(f"[{category}]", style=Theme.ACCENT)
            header.append("  ", style="default")
            header.append(f"{relative_time}", style=Theme.MUTED)

            console.print(header)

            content = r.get("content", "").strip()
            if content:
                console.print(Padding(Text(content, style="default"), (0, 0, 1, 4)))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


@memory_app.command("delete")
def memory_delete(
    by: str = typer.Option(..., "--by", help="Delete by: 'id' or 'category'"),
    value: str = typer.Option(..., "--value", help="The ID or category to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm destructive actions"),
):
    """Delete memory by ID or category."""
    from glee.memory import Memory

    memory = None
    try:
        memory = Memory(os.getcwd())

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
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if memory is not None:
            memory.close()


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
            console.print(f"[{Theme.WARNING}]No memories found[/{Theme.WARNING}]")
            return

        console.print(Panel(
            f"[{Theme.MUTED}]Query:[/{Theme.MUTED}] [{Theme.PRIMARY}]{query}[/{Theme.PRIMARY}]",
            title=f"[{Theme.HEADER}]🔍 Found {len(results)} memories[/{Theme.HEADER}]",
            border_style=Theme.PRIMARY
        ))
        for r in results:
            console.print(f"\n[{Theme.PRIMARY}]{r.get('id')}[/{Theme.PRIMARY}] [{Theme.ACCENT}]{r.get('category')}[/{Theme.ACCENT}]")
            console.print(f"  {r.get('content')}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("overview")
def memory_overview(
    generate: bool = typer.Option(False, "--generate", "-g", help="Generate/update overview using an AI agent"),
    agent: str | None = typer.Option(None, "--agent", "-a", help="Agent to use (claude, codex, gemini). Auto-detects if not specified."),
):
    """Show or generate project overview memory."""
    from datetime import datetime, timezone
    from pathlib import Path

    from glee.helpers import parse_time
    from glee.memory import Memory

    project_path = Path(os.getcwd())

    if generate:
        _generate_overview(project_path, agent)
        return

    # Read mode: show existing overview
    try:
        memory = Memory(str(project_path))
        entries = memory.get_by_category("overview")
        memory.close()

        if not entries:
            console.print("[yellow]No overview memory found.[/yellow]")
            console.print("[dim]Run: glee memory overview --generate[/dim]")
            return

        entry = entries[0]
        content = (entry.get("content") or "").strip()

        # Check age
        created_at = entry.get("created_at")
        age_info = ""
        age_days = 0
        if created_at:
            created_time = parse_time(created_at)
            if created_time:
                now = datetime.now(timezone.utc)
                if created_time.tzinfo is None:
                    created_time = created_time.replace(tzinfo=timezone.utc)
                age_days = (now - created_time).days
                if age_days == 0:
                    age_info = "today"
                elif age_days == 1:
                    age_info = "1 day ago"
                else:
                    age_info = f"{age_days} days ago"

        if age_info:
            console.print(f"[dim]Last updated: {age_info}[/dim]")
            if age_days >= 7:
                console.print("[yellow]Stale - run: glee memory overview --generate[/yellow]")
            console.print()

        from rich.markdown import Markdown

        console.print(Markdown(content))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _generate_overview(project_path: Path, agent_name: str | None = None) -> None:
    """Generate project overview using an AI agent."""
    from glee.agents import registry
    from glee.memory import Memory

    # Find available agent
    agent_order = ["claude", "codex", "gemini"]
    if agent_name:
        agent_order = [agent_name]

    agent = None
    for name in agent_order:
        candidate = registry.get(name)
        if candidate and candidate.is_available():
            agent = candidate
            break

    if not agent:
        if agent_name:
            console.print(f"[red]Agent '{agent_name}' not available.[/red]")
        else:
            console.print("[red]No AI agent available. Install claude, codex, or gemini CLI.[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]Using {agent.name} to generate overview...[/dim]")

    # Gather project context
    context_lines: list[str] = []

    # Documentation files
    doc_files = [
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "docs/README.md",
        "docs/architecture.md",
    ]

    for doc_file in doc_files:
        doc_path = project_path / doc_file
        if doc_path.exists():
            try:
                content = doc_path.read_text()
                if len(content) > 5000:
                    content = content[:5000] + "\n\n... (truncated)"
                context_lines.append(f"## {doc_file}\n```\n{content}\n```\n")
            except Exception:
                pass

    # Package configuration
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
                context_lines.append(f"## {pkg_file}\n```{lang}\n{content}\n```\n")
            except Exception:
                pass

    # Directory structure
    def get_tree(path: Path, prefix: str = "", depth: int = 0) -> list[str]:
        if depth > 3:  # Limit depth for CLI
            return []
        tree_lines: list[str] = []
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            items = [i for i in items if not i.name.startswith(".") and i.name not in (
                "node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build",
                "target", ".pytest_cache", ".mypy_cache"
            )]
            for i, item in enumerate(items[:20]):
                is_last = i == len(items) - 1 or i == 19
                connector = "└── " if is_last else "├── "
                tree_lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    tree_lines.extend(get_tree(item, prefix + extension, depth + 1))
        except PermissionError:
            pass
        return tree_lines

    tree = get_tree(project_path)
    context_lines.append(f"## Directory Structure\n```\n" + "\n".join(tree) + "\n```\n")

    # Build prompt
    prompt = f"""Analyze this project and create a comprehensive overview summary.

# Project Context
{"".join(context_lines)}

# Task
Create a project overview covering:
- **Architecture**: Key patterns, module organization, data flow, entry points
- **Conventions**: Coding standards, naming patterns, file organization
- **Dependencies**: Key libraries and their purposes
- **Decisions**: Notable technical choices and trade-offs

Output ONLY the overview content in markdown format, starting with "# Project Overview".
Do not include any other text, explanations, or tool calls - just the overview itself.
"""

    # Run agent
    console.print(f"[dim]Analyzing project...[/dim]")
    result = agent.run(prompt)

    if not result.success:
        console.print(f"[red]Agent failed: {result.error}[/red]")
        raise typer.Exit(1)

    overview_content = result.output.strip()

    # Basic validation
    if not overview_content or len(overview_content) < 100:
        console.print("[red]Agent returned empty or too short response.[/red]")
        raise typer.Exit(1)

    # Clear existing and save new
    memory = Memory(str(project_path))
    memory.clear("overview")
    memory.add(category="overview", content=overview_content)
    memory.close()

    console.print(f"[green]Overview generated and saved.[/green]")
    console.print()
    console.print(overview_content)


@memory_app.command("stats")
def memory_stats():
    """Show memory statistics."""
    from glee.memory import Memory

    try:
        memory = Memory(os.getcwd())
        stats = memory.stats()
        memory.close()

        stats_tree = Tree(f"[{Theme.HEADER}]📊 Memory Statistics[/{Theme.HEADER}]")
        stats_tree.add(f"[{Theme.MUTED}]Total:[/{Theme.MUTED}] [{Theme.PRIMARY}]{stats['total']}[/{Theme.PRIMARY}]")

        if stats["by_category"]:
            cat_branch = stats_tree.add(f"[{Theme.INFO}]By Category[/{Theme.INFO}]")
            for cat, count in sorted(stats["by_category"].items()):
                cat_branch.add(f"[{Theme.ACCENT}]{cat}[/{Theme.ACCENT}]: [{Theme.PRIMARY}]{count}[/{Theme.PRIMARY}]")

        if stats["oldest"] or stats["newest"]:
            time_branch = stats_tree.add(f"[{Theme.INFO}]Time Range[/{Theme.INFO}]")
            if stats["oldest"]:
                oldest = stats["oldest"]
                if hasattr(oldest, "strftime"):
                    oldest = oldest.strftime("%Y-%m-%d %H:%M")
                time_branch.add(f"[{Theme.MUTED}]Oldest:[/{Theme.MUTED}] {oldest}")
            if stats["newest"]:
                newest = stats["newest"]
                if hasattr(newest, "strftime"):
                    newest = newest.strftime("%Y-%m-%d %H:%M")
                time_branch.add(f"[{Theme.MUTED}]Newest:[/{Theme.MUTED}] {newest}")

        console.print(padded(stats_tree))

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
        console.print(f"[{Theme.WARNING}]No logs found[/{Theme.WARNING}]")
        return

    console.print(Rule(f"[{Theme.HEADER}]📝 Recent Logs ({len(results)} entries)[/{Theme.HEADER}]", style=Theme.MUTED))
    console.print()
    for log in results:
        level_color = {
            "DEBUG": Theme.MUTED,
            "INFO": Theme.INFO,
            "WARNING": Theme.WARNING,
            "ERROR": Theme.ERROR,
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
        console.print(f"[{Theme.WARNING}]No logs found[/{Theme.WARNING}]")
        return

    stats_tree = Tree(f"[{Theme.HEADER}]📊 Log Statistics[/{Theme.HEADER}]")
    stats_tree.add(f"[{Theme.MUTED}]Total:[/{Theme.MUTED}] [{Theme.PRIMARY}]{stats['total']}[/{Theme.PRIMARY}]")

    level_branch = stats_tree.add(f"[{Theme.INFO}]By Level[/{Theme.INFO}]")
    level_colors = {"DEBUG": Theme.MUTED, "INFO": Theme.INFO, "WARNING": Theme.WARNING, "ERROR": Theme.ERROR}
    for level, count in sorted(stats["by_level"].items()):
        color = level_colors.get(level, "white")
        level_branch.add(f"[{color}]{level}[/{color}]: [{Theme.PRIMARY}]{count}[/{Theme.PRIMARY}]")

    console.print(padded(stats_tree))


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
        console.print(f"[{Theme.WARNING}]No agent logs found[/{Theme.WARNING}]")
        return

    table = Table(
        title=f"🤖 Agent Logs (last {len(results)})",
        title_style=Theme.HEADER,
        border_style=Theme.MUTED,
        header_style=f"bold {Theme.PRIMARY}",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("ID", style=Theme.PRIMARY, width=8)
    table.add_column("Time", style=Theme.MUTED, width=19)
    table.add_column("Agent", style=Theme.ACCENT, width=8)
    table.add_column("Duration", style=Theme.WARNING, width=8)
    table.add_column("Status", justify="center", width=8)
    table.add_column("Prompt", style="white", max_width=40, overflow="ellipsis")

    for log in results:
        timestamp = log["timestamp"][:19]
        duration = f"{log['duration_ms']}ms" if log["duration_ms"] else "-"
        status = Text("● OK", style=Theme.SUCCESS) if log["success"] else Text("✗ FAIL", style=Theme.ERROR)
        prompt = (log["prompt"][:37] + "...") if len(log["prompt"]) > 40 else log["prompt"]
        prompt = prompt.replace("\n", " ")

        table.add_row(log["id"], timestamp, log["agent"], duration, status, prompt)

    console.print(padded(table))


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
        console.print(padded(Panel(
            f"Log [{Theme.PRIMARY}]{log_id}[/{Theme.PRIMARY}] not found",
            title=f"[{Theme.ERROR}]Error[/{Theme.ERROR}]",
            border_style=Theme.ERROR
        )))
        raise typer.Exit(1)

    # Build details tree
    detail_tree = Tree(f"[{Theme.HEADER}]🔍 Agent Log Details[/{Theme.HEADER}]")
    detail_tree.add(f"[{Theme.MUTED}]ID:[/{Theme.MUTED}] [{Theme.PRIMARY}]{log['id']}[/{Theme.PRIMARY}]")
    detail_tree.add(f"[{Theme.MUTED}]Time:[/{Theme.MUTED}] {log['timestamp']}")
    detail_tree.add(f"[{Theme.MUTED}]Agent:[/{Theme.MUTED}] [{Theme.ACCENT}]{log['agent']}[/{Theme.ACCENT}]")
    detail_tree.add(f"[{Theme.MUTED}]Duration:[/{Theme.MUTED}] [{Theme.WARNING}]{log['duration_ms']}ms[/{Theme.WARNING}]")
    if log["success"]:
        detail_tree.add(f"[{Theme.MUTED}]Status:[/{Theme.MUTED}] [{Theme.SUCCESS}]✓ Success[/{Theme.SUCCESS}]")
    else:
        detail_tree.add(f"[{Theme.MUTED}]Status:[/{Theme.MUTED}] [{Theme.ERROR}]✗ Failed[/{Theme.ERROR}]")
    console.print(padded(detail_tree, bottom=0))

    console.print(padded(Panel(
        log["prompt"],
        title=f"[{Theme.INFO}]Prompt[/{Theme.INFO}]",
        border_style=Theme.MUTED,
        padding=(0, 1)
    ), top=0, bottom=0))

    if raw and log.get("raw"):
        console.print(padded(Panel(
            log["raw"],
            title=f"[{Theme.INFO}]Raw Output[/{Theme.INFO}]",
            border_style=Theme.MUTED,
            padding=(0, 1)
        ), top=0, bottom=0))
    elif log.get("output"):
        console.print(padded(Panel(
            log["output"],
            title=f"[{Theme.SUCCESS}]Output[/{Theme.SUCCESS}]",
            border_style=Theme.SUCCESS,
            padding=(0, 1)
        ), top=0, bottom=0))

    if log.get("error"):
        console.print(padded(Panel(
            log["error"],
            title=f"[{Theme.ERROR}]Error[/{Theme.ERROR}]",
            border_style=Theme.ERROR,
            padding=(0, 1)
        ), top=0))
    else:
        console.print()  # Bottom padding


@app.command()
def mcp():
    """Run Glee MCP server (for Claude Code integration)."""
    import asyncio

    from glee.mcp_server import run_server

    asyncio.run(run_server())


# Auth subcommands (unified)
auth_app = typer.Typer(help="Authentication management")
app.add_typer(auth_app, name="auth")


def _do_codex_oauth() -> bool:
    """Run Codex OAuth flow. Returns True on success."""
    import asyncio
    import time

    from glee.auth.codex import authenticate, extract_account_id
    from glee.auth import storage

    try:
        tokens, error = asyncio.run(authenticate())

        if error:
            console.print(f"[{Theme.ERROR}]Authentication failed: {error}[/{Theme.ERROR}]")
            return False

        if not tokens:
            console.print(f"[{Theme.ERROR}]No tokens received[/{Theme.ERROR}]")
            return False

        account_id = extract_account_id(tokens.access_token)
        expires_ms = int((time.time() + tokens.expires_in) * 1000)

        # Check if we already have a codex credential
        existing = storage.find_one(vendor="openai", type="oauth")

        credential = storage.OAuthCredential(
            id=existing.id if existing else "",
            label="codex",
            sdk="openai",
            vendor="openai",
            refresh=tokens.refresh_token,
            access=tokens.access_token,
            expires=expires_ms,
            account_id=account_id,
        )

        if existing:
            storage.update(existing.id, credential)
        else:
            storage.add(credential)

        console.print(f"[{Theme.SUCCESS}]✓ Codex authenticated[/{Theme.SUCCESS}]")
        if account_id:
            console.print(f"  [{Theme.MUTED}]Account:[/{Theme.MUTED}] {account_id}")
        return True

    except Exception as e:
        console.print(f"[{Theme.ERROR}]Error: {e}[/{Theme.ERROR}]")
        return False


def _do_copilot_oauth() -> bool:
    """Run GitHub Copilot OAuth flow. Returns True on success."""
    import asyncio

    from glee.auth.copilot import authenticate
    from glee.auth import storage

    try:
        tokens, error = asyncio.run(authenticate())

        if error:
            console.print(f"[{Theme.ERROR}]Authentication failed: {error}[/{Theme.ERROR}]")
            return False

        if not tokens:
            console.print(f"[{Theme.ERROR}]No tokens received[/{Theme.ERROR}]")
            return False

        # Check if we already have a copilot credential
        existing = storage.find_one(vendor="github", type="oauth")

        credential = storage.OAuthCredential(
            id=existing.id if existing else "",
            label="copilot",
            sdk="openai",  # Copilot uses OpenAI-compatible API
            vendor="github",
            refresh=tokens.access_token,  # Same token for both
            access=tokens.access_token,
            expires=0,  # Doesn't expire
        )

        if existing:
            storage.update(existing.id, credential)
        else:
            storage.add(credential)

        console.print(f"[{Theme.SUCCESS}]✓ GitHub Copilot authenticated[/{Theme.SUCCESS}]")
        return True

    except Exception as e:
        console.print(f"[{Theme.ERROR}]Error: {e}[/{Theme.ERROR}]")
        return False


@auth_app.callback(invoke_without_command=True)
def auth_tui(ctx: typer.Context):
    """Add a provider credential.

    Examples:
        glee auth          # Interactive setup
        glee auth status   # Show configured providers
    """
    if ctx.invoked_subcommand is not None:
        return

    from rich.prompt import Prompt
    from glee.auth import storage

    console.print()
    console.print(f"  [{Theme.HEADER}]Select SDK[/{Theme.HEADER}]")
    console.print(f"  [{Theme.PRIMARY}]1[/{Theme.PRIMARY}]  Codex        [{Theme.MUTED}]OpenAI OAuth[/{Theme.MUTED}]")
    console.print(f"  [{Theme.PRIMARY}]2[/{Theme.PRIMARY}]  Copilot      [{Theme.MUTED}]GitHub OAuth[/{Theme.MUTED}]")
    console.print(f"  [{Theme.PRIMARY}]3[/{Theme.PRIMARY}]  OpenAI SDK   [{Theme.MUTED}]OpenRouter, Groq, etc.[/{Theme.MUTED}]")
    console.print(f"  [{Theme.PRIMARY}]4[/{Theme.PRIMARY}]  Anthropic    [{Theme.MUTED}]Claude API[/{Theme.MUTED}]")
    console.print(f"  [{Theme.PRIMARY}]5[/{Theme.PRIMARY}]  Google       [{Theme.MUTED}]Gemini API[/{Theme.MUTED}]")
    console.print()

    choice = Prompt.ask(f"  [{Theme.PRIMARY}]Select[/{Theme.PRIMARY}]", show_default=False, default="")

    if choice == "1":  # Codex OAuth
        _do_codex_oauth()

    elif choice == "2":  # Copilot OAuth
        _do_copilot_oauth()

    elif choice == "3":  # OpenAI SDK
        console.print()
        vendors = list(storage.VENDOR_URLS.items())
        for i, (name, url) in enumerate(vendors, 1):
            console.print(f"  [{Theme.PRIMARY}]{i}[/{Theme.PRIMARY}]  {name:<12} [{Theme.MUTED}]{url}[/{Theme.MUTED}]")
        console.print()

        ep_choice = Prompt.ask(f"  [{Theme.PRIMARY}]Vendor[/{Theme.PRIMARY}]", show_default=False, default="")
        if ep_choice.isdigit() and 1 <= int(ep_choice) <= len(vendors):
            vendor, base_url = vendors[int(ep_choice) - 1]
        else:
            vendor = ep_choice
            base_url = Prompt.ask(f"  [{Theme.PRIMARY}]Base URL[/{Theme.PRIMARY}]")

        label = Prompt.ask(f"  [{Theme.PRIMARY}]Label[/{Theme.PRIMARY}]", default=vendor)
        api_key = Prompt.ask(f"  [{Theme.PRIMARY}]API key[/{Theme.PRIMARY}]", default="")

        storage.add(storage.APICredential(
            id="",
            label=label,
            sdk="openai",
            vendor=vendor,
            key=api_key,
            base_url=base_url,
        ))
        console.print(f"  [{Theme.SUCCESS}]✓ {label} saved[/{Theme.SUCCESS}]")

    elif choice == "4":  # Anthropic
        label = Prompt.ask(f"  [{Theme.PRIMARY}]Label[/{Theme.PRIMARY}]", default="anthropic")
        api_key = Prompt.ask(f"  [{Theme.PRIMARY}]API key[/{Theme.PRIMARY}]")
        if api_key:
            storage.add(storage.APICredential(
                id="",
                label=label,
                sdk="anthropic",
                vendor="anthropic",
                key=api_key,
            ))
            console.print(f"  [{Theme.SUCCESS}]✓ {label} saved[/{Theme.SUCCESS}]")

    elif choice == "5":  # Google
        label = Prompt.ask(f"  [{Theme.PRIMARY}]Label[/{Theme.PRIMARY}]", default="google")
        api_key = Prompt.ask(f"  [{Theme.PRIMARY}]API key[/{Theme.PRIMARY}]")
        if api_key:
            storage.add(storage.APICredential(
                id="",
                label=label,
                sdk="google",
                vendor="google",
                key=api_key,
            ))
            console.print(f"  [{Theme.SUCCESS}]✓ {label} saved[/{Theme.SUCCESS}]")


@auth_app.command("status")
def auth_status():
    """Show authentication status for all providers.

    Examples:
        glee auth status
    """
    from glee.auth import storage

    console.print(padded(Text.assemble(
        ("🔐 ", "bold"),
        ("Auth Status", f"bold {Theme.PRIMARY}"),
    ), bottom=0))

    creds = storage.all()
    if not creds:
        console.print(padded(Text("No credentials configured. Run: glee auth", style=Theme.MUTED)))
        return

    auth_tree = Tree(f"[{Theme.HEADER}]Credentials[/{Theme.HEADER}]")

    for c in creds:
        if isinstance(c, storage.OAuthCredential):
            status = f"[{Theme.WARNING}]expired[/{Theme.WARNING}]" if c.is_expired() else f"[{Theme.SUCCESS}]active[/{Theme.SUCCESS}]"
            branch = auth_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {c.label} [{Theme.ACCENT}]oauth[/{Theme.ACCENT}] {status}")
            branch.add(f"[{Theme.MUTED}]id:[/{Theme.MUTED}] {c.id}")
            branch.add(f"[{Theme.MUTED}]vendor:[/{Theme.MUTED}] {c.vendor}")
            if c.account_id:
                branch.add(f"[{Theme.MUTED}]account:[/{Theme.MUTED}] {c.account_id}")
        else:
            # APICredential
            masked = c.key[:8] + "..." if len(c.key) > 8 else "***"
            branch = auth_tree.add(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {c.label} [{Theme.MUTED}]{masked}[/{Theme.MUTED}]")
            branch.add(f"[{Theme.MUTED}]id:[/{Theme.MUTED}] {c.id}")
            branch.add(f"[{Theme.MUTED}]vendor:[/{Theme.MUTED}] {c.vendor} [{Theme.ACCENT}]{c.sdk}[/{Theme.ACCENT}]")
            if c.base_url:
                branch.add(f"[{Theme.MUTED}]url:[/{Theme.MUTED}] {c.base_url}")

    console.print(padded(auth_tree))


@auth_app.command("list")
def auth_list():
    """List all configured credentials."""
    from glee.auth import storage

    creds = storage.all()
    if not creds:
        console.print(padded(f"[{Theme.WARNING}]No credentials configured. Run: glee auth[/{Theme.WARNING}]"))
        return

    console.print(padded(Text.assemble(
        ("🔑 ", "bold"),
        ("Credentials", f"bold {Theme.PRIMARY}"),
    ), bottom=0))
    console.print()
    for c in creds:
        sdk_info = f"[{Theme.ACCENT}]{c.sdk}[/{Theme.ACCENT}]"
        console.print(f"  [{Theme.MUTED}]{c.id}[/{Theme.MUTED}]  {c.label:<16} {c.vendor:<12} {sdk_info}")
    console.print()


@auth_app.command("test")
def auth_test(
    id: str = typer.Argument(..., help="Credential ID to test"),
):
    """Test a credential by making an API call.

    Examples:
        glee auth test a1b2c3d4e5
    """
    import httpx

    from glee.auth import storage

    cred = storage.get(id)
    if not cred:
        console.print(padded(f"[{Theme.ERROR}]Credential not found: {id}[/{Theme.ERROR}]"))
        return

    c = cred
    label = f"{c.label} ({c.vendor})"

    console.print(padded(Text.assemble(
        ("🧪 ", "bold"),
        (f"Testing {label}", f"bold {Theme.PRIMARY}"),
    ), bottom=0))

    try:
        if c.sdk == "openai":
            if isinstance(c, storage.OAuthCredential):
                # OAuth credentials - test with minimal completion
                if c.vendor == "github":
                    # GitHub Copilot
                    url = "https://api.githubcopilot.com/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {c.access}",
                        "Content-Type": "application/json",
                    }
                    json_body = {
                        "model": "gpt-4o",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "Hi. Please say hello back."}],
                    }
                elif c.vendor == "openai":
                    # Codex OAuth - uses ChatGPT backend API with streaming
                    url = "https://chatgpt.com/backend-api/codex/responses"
                    headers = {
                        "Authorization": f"Bearer {c.access}",
                        "Content-Type": "application/json",
                    }
                    if c.account_id:
                        headers["ChatGPT-Account-Id"] = c.account_id
                    json_body = {
                        "model": "gpt-5.1-codex-mini",
                        "instructions": "You are a helpful assistant.",
                        "input": [{"role": "user", "content": "Hi. Please say hello back."}],
                        "store": False,
                        "stream": True,
                    }
                    # Streaming request
                    with httpx.stream("POST", url, headers=headers, json=json_body, timeout=30) as response:
                        if response.status_code == 200:
                            # Read first chunk to verify stream works
                            for chunk in response.iter_lines():
                                if chunk:
                                    console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Credential valid"))
                                    break
                        else:
                            error_text = response.read().decode()[:100]
                            console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] HTTP {response.status_code}: {error_text}"))
                    return
                else:
                    url = "https://api.openai.com/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {c.access}",
                        "Content-Type": "application/json",
                    }
                    json_body = {
                        "model": "gpt-4o-mini",
                        "max_tokens": 100,
                        "messages": [{"role": "user", "content": "Hi. Please say hello back."}],
                    }

                response = httpx.post(url, headers=headers, json=json_body, timeout=15)

                if response.status_code == 200:
                    console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Credential valid"))
                else:
                    console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] HTTP {response.status_code}: {response.text[:100]}"))
            else:
                # API key credentials - test with /models endpoint
                base_url = c.base_url or "https://api.openai.com/v1"
                headers = {"Authorization": f"Bearer {c.key}"}

                response = httpx.get(f"{base_url}/models", headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get("data", []))
                    console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {model_count} models available"))
                else:
                    console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] HTTP {response.status_code}: {response.text[:100]}"))

        elif c.sdk == "anthropic":
            # Anthropic SDK - requires API key
            if not isinstance(c, storage.APICredential):
                console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] Anthropic requires API key, not OAuth"))
            else:
                headers = {
                    "x-api-key": c.key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                response = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "Hi. Please say hello back."}],
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] API key valid"))
                elif response.status_code == 401:
                    console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] Invalid API key"))
                else:
                    console.print(padded(f"[{Theme.WARNING}]?[/{Theme.WARNING}] HTTP {response.status_code}"))

        elif c.sdk == "google":
            # Google/Gemini - requires API key
            if not isinstance(c, storage.APICredential):
                console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] Google requires API key, not OAuth"))
            else:
                response = httpx.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={c.key}",
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get("models", []))
                    console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] {model_count} models available"))
                else:
                    console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] HTTP {response.status_code}"))

        else:
            console.print(padded(f"[{Theme.WARNING}]?[/{Theme.WARNING}] Unknown SDK: {c.sdk}"))

    except httpx.TimeoutException:
        console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] Timeout"))
    except Exception as e:
        console.print(padded(f"[{Theme.ERROR}]✗[/{Theme.ERROR}] {e}"))


@auth_app.command("add")
def auth_add(
    vendor: str = typer.Argument(..., help="Vendor name (e.g., anthropic, openrouter, groq)"),
    api_key: str = typer.Argument(..., help="API key"),
    label: str | None = typer.Option(None, "--label", "-l", help="Label for this credential"),
    sdk: str = typer.Option("openai", "--sdk", "-s", help="SDK type: openai, anthropic, google"),
    base_url: str | None = typer.Option(None, "--base-url", "-u", help="Base URL (auto-detected for known vendors)"),
):
    """Add an API key credential.

    Examples:
        glee auth add anthropic sk-ant-xxx
        glee auth add openrouter sk-or-xxx
        glee auth add groq gsk-xxx
        glee auth add custom xxx --base-url https://api.example.com/v1 --sdk openai
    """
    from glee.auth import storage

    # Auto-detect base_url for known vendors
    if base_url is None and vendor in storage.VENDOR_URLS:
        base_url = storage.VENDOR_URLS[vendor]

    # Auto-detect SDK for known vendors
    if vendor == "anthropic":
        sdk = "anthropic"
    elif vendor == "google":
        sdk = "google"

    credential = storage.APICredential(
        id="",
        label=label or vendor,
        sdk=sdk,  # type: ignore[arg-type]
        vendor=vendor,
        key=api_key,
        base_url=base_url,
    )
    storage.add(credential)

    console.print(padded(Text.assemble(
        (f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] ", ""),
        (f"Saved {label or vendor} credentials", ""),
    )))


@auth_app.command("remove")
def auth_remove(
    id_or_label: str = typer.Argument(..., help="Credential ID or label to remove"),
):
    """Remove a credential by ID or label.

    Examples:
        glee auth remove a1b2c3d4e5
        glee auth remove openrouter
    """
    from glee.auth import storage

    # Try to find by ID first
    cred = storage.get(id_or_label)
    if cred:
        storage.remove(id_or_label)
        console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Removed {cred.label} ({cred.id})"))
        return

    # Try to find by label
    all_creds = storage.all()
    for c in all_creds:
        if c.label == id_or_label:
            storage.remove(c.id)
            console.print(padded(f"[{Theme.SUCCESS}]✓[/{Theme.SUCCESS}] Removed {c.label} ({c.id})"))
            return

    console.print(padded(f"[{Theme.WARNING}]No credentials found for: {id_or_label}[/{Theme.WARNING}]"))


if __name__ == "__main__":
    app()
