"""Configuration management for Glee."""

import os
import uuid
from pathlib import Path
from typing import IO, Any, cast

import yaml

from glee.types import (
    AutonomyConfig,
    AutonomyLevel,
    CheckpointAction,
    CheckpointSeverity,
)


# XDG config directory
GLEE_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "glee"
GLEE_PROJECT_DIR = ".glee"

# Supported reviewer CLIs
SUPPORTED_REVIEWERS = ["codex", "claude", "gemini"]

# Valid autonomy levels
VALID_AUTONOMY_LEVELS = [level.value for level in AutonomyLevel]
VALID_SEVERITIES = [sev.value for sev in CheckpointSeverity]
VALID_ACTIONS = [action.value for action in CheckpointAction]


def _dump_yaml(data: dict[str, Any], file: IO[str]) -> None:
    """Dump YAML with consistent formatting."""
    yaml.dump(data, file, default_flow_style=False, sort_keys=False)


def ensure_global_config() -> None:
    """Ensure global config directory exists."""
    GLEE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config_path = GLEE_CONFIG_DIR / "config.yml"
    if not config_path.exists():
        with open(config_path, "w") as f:
            _dump_yaml({
                "version": "2.0",
                "defaults": {
                    "reviewers": {"primary": "codex"},
                    "memory": {"embedding_model": "BAAI/bge-small-en-v1.5"},
                },
            }, f)

    projects_path = GLEE_CONFIG_DIR / "projects.yml"
    if not projects_path.exists():
        with open(projects_path, "w") as f:
            _dump_yaml({"projects": []}, f)


def get_projects_registry() -> list[dict[str, Any]]:
    """Get projects registry."""
    ensure_global_config()
    with open(GLEE_CONFIG_DIR / "projects.yml") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return data.get("projects", [])


def save_projects_registry(projects: list[dict[str, Any]]) -> None:
    """Save projects registry."""
    ensure_global_config()
    with open(GLEE_CONFIG_DIR / "projects.yml", "w") as f:
        _dump_yaml({"projects": projects}, f)


def update_project_registry(project_id: str, name: str, path: str) -> None:
    """Update the global projects registry."""
    projects = get_projects_registry()

    for p in projects:
        if p.get("id") == project_id:
            p["name"] = name
            p["path"] = path
            break
    else:
        projects.append({"id": project_id, "name": name, "path": path})

    save_projects_registry(projects)


def _add_to_gitignore(project_path: str, entry: str) -> None:
    """Add an entry to .gitignore if not already present."""
    gitignore_path = Path(project_path) / ".gitignore"

    if not gitignore_path.exists():
        return

    content = gitignore_path.read_text()
    lines = content.splitlines()
    if entry in lines or entry.rstrip("/") in lines:
        return

    with open(gitignore_path, "a") as f:
        if content and not content.endswith("\n"):
            f.write("\n")
        f.write(f"{entry}\n")


def register_mcp_server(project_path: str) -> bool:
    """Register Glee as an MCP server in project's .mcp.json. Idempotent."""
    import json

    project_dir = Path(project_path)
    mcp_config_path = project_dir / ".mcp.json"

    if mcp_config_path.exists():
        with open(mcp_config_path) as f:
            config = json.load(f)
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    if "glee" in config["mcpServers"]:
        return False

    config["mcpServers"]["glee"] = {
        "command": "glee",
        "args": ["mcp"],
    }

    with open(mcp_config_path, "w") as f:
        json.dump(config, f, indent=2)

    return True


def register_session_hook(project_path: str) -> bool:
    """Register Glee hooks in Claude Code settings. Idempotent.

    Registers:
    - SessionStart: Inject warmup context at session start
    - SessionEnd: Capture session summary at session end
    """
    import json

    project_dir = Path(project_path)
    claude_dir = project_dir / ".claude"
    settings_path = claude_dir / "settings.local.json"

    claude_dir.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        with open(settings_path) as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                settings = {}
    else:
        settings = {}

    if "hooks" not in settings:
        settings["hooks"] = {}

    hooks_dict = cast(dict[str, list[dict[str, Any]]], settings["hooks"])
    updated = False

    # Helper to check if a hook command exists
    def has_hook_command(hook_name: str, command_substr: str) -> bool:
        hooks_list = hooks_dict.get(hook_name, [])
        for hook_config in hooks_list:
            inner_hooks = cast(list[dict[str, Any]], hook_config.get("hooks", []))
            for h in inner_hooks:
                cmd = str(h.get("command", ""))
                if command_substr in cmd:
                    return True
        return False

    # Register warmup hook (SessionStart)
    if not has_hook_command("SessionStart", "glee warmup-session"):
        warmup_hook: dict[str, Any] = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": "glee warmup-session 2>/dev/null || true",
                }
            ],
        }
        if "SessionStart" not in hooks_dict:
            hooks_dict["SessionStart"] = []
        hooks_dict["SessionStart"].append(warmup_hook)
        updated = True

    # Register session summary hook (SessionEnd)
    # Note: Read stdin first (blocking), then background the processing
    # This allows Claude Code to exit while glee processes the summary
    if not has_hook_command("SessionEnd", "glee summarize-session"):
        session_end_hook: dict[str, Any] = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": "input=$(cat) && (echo \"$input\" | glee summarize-session --from=claude 2>/dev/null || true) &",
                }
            ],
        }
        if "SessionEnd" not in hooks_dict:
            hooks_dict["SessionEnd"] = []
        hooks_dict["SessionEnd"].append(session_end_hook)
        updated = True

    # Register pre-compact hook (PreCompact) - capture context before compaction
    # Note: Read stdin first (blocking), then background the processing
    if not has_hook_command("PreCompact", "glee summarize-session"):
        pre_compact_hook: dict[str, Any] = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": "input=$(cat) && (echo \"$input\" | glee summarize-session --from=claude 2>/dev/null || true) &",
                }
            ],
        }
        if "PreCompact" not in hooks_dict:
            hooks_dict["PreCompact"] = []
        hooks_dict["PreCompact"].append(pre_compact_hook)
        updated = True

    if updated:
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

    return updated


def init_project(project_path: str, project_id: str | None = None, agent: str | None = None) -> dict[str, Any]:
    """Initialize a Glee project. Idempotent.

    Args:
        project_path: Path to the project directory
        project_id: Optional project ID (generated if not provided)
        agent: Primary agent to integrate with (claude, codex, gemini, or None)

    Returns dict with 'project' config and status flags.
    """
    project_path = os.path.abspath(project_path)
    glee_dir = Path(project_path) / GLEE_PROJECT_DIR

    glee_dir.mkdir(parents=True, exist_ok=True)
    (glee_dir / "sessions").mkdir(exist_ok=True)
    (glee_dir / "stream_logs").mkdir(exist_ok=True)

    config_path = glee_dir / "config.yml"

    # Check for existing config
    existing_config: dict[str, Any] = {}
    existing_id: str | None = None
    if config_path.exists():
        with open(config_path) as f:
            existing_config = yaml.safe_load(f) or {}
            if not project_id:
                existing_id = existing_config.get("project", {}).get("id")

    # Preserve existing reviewers config
    existing_reviewers = existing_config.get("reviewers", {"primary": "codex"})

    config: dict[str, Any] = {
        "project": {
            "id": project_id or existing_id or str(uuid.uuid4()),
            "name": os.path.basename(project_path),
        },
        "reviewers": existing_reviewers,
    }

    with open(config_path, "w") as f:
        _dump_yaml(config, f)

    _add_to_gitignore(project_path, ".glee/")

    # Agent-specific integrations
    mcp_registered = False
    hook_registered = False
    if agent == "claude":
        claude_code_mcp_json_exists = (Path(project_path) / ".mcp.json").exists()
        mcp_registered = register_mcp_server(project_path)
        if mcp_registered and not claude_code_mcp_json_exists:
            _add_to_gitignore(project_path, ".mcp.json")
        hook_registered = register_session_hook(project_path)

    update_project_registry(config["project"]["id"], config["project"]["name"], project_path)

    result = dict(config)
    result["_mcp_registered"] = mcp_registered
    result["_hook_registered"] = hook_registered
    return result


def get_project_config(project_path: str | None = None) -> dict[str, Any] | None:
    """Get project configuration."""
    if project_path is None:
        project_path = os.getcwd()

    config_path = Path(project_path) / GLEE_PROJECT_DIR / "config.yml"
    if not config_path.exists():
        return None

    with open(config_path) as f:
        return yaml.safe_load(f)


def save_project_config(config: dict[str, Any], project_path: str | None = None) -> None:
    """Save project configuration."""
    if project_path is None:
        project_path = os.getcwd()

    ordered: dict[str, Any] = {
        "project": config.get("project", {}),
        "reviewers": config.get("reviewers", {"primary": "codex"}),
    }

    # Include autonomy config if present
    if "autonomy" in config:
        ordered["autonomy"] = config["autonomy"]

    with open(Path(project_path) / GLEE_PROJECT_DIR / "config.yml", "w") as f:
        _dump_yaml(ordered, f)


def set_reviewer(
    command: str,
    tier: str = "primary",
    project_path: str | None = None,
) -> dict[str, Any]:
    """Set a reviewer preference.

    Args:
        command: CLI command (codex, claude, gemini)
        tier: "primary" or "secondary"
        project_path: Optional project path

    Returns:
        Updated reviewers config
    """
    if command not in SUPPORTED_REVIEWERS:
        raise ValueError(f"Unsupported reviewer: {command}. Supported: {', '.join(SUPPORTED_REVIEWERS)}")

    if tier not in ("primary", "secondary"):
        raise ValueError(f"Invalid tier: {tier}. Valid: primary, secondary")

    config = get_project_config(project_path)
    if not config:
        raise ValueError("Project not initialized. Run 'glee init' first.")

    reviewers = config.get("reviewers", {})
    reviewers[tier] = command

    config["reviewers"] = reviewers
    save_project_config(config, project_path)
    return reviewers


def get_reviewers(project_path: str | None = None) -> dict[str, str]:
    """Get configured reviewers.

    Returns:
        Dict with 'primary' and optionally 'secondary' reviewer CLIs
    """
    config = get_project_config(project_path)
    if not config:
        return {"primary": "codex"}
    return config.get("reviewers", {"primary": "codex"})


def clear_reviewer(tier: str = "secondary", project_path: str | None = None) -> bool:
    """Clear a reviewer preference.

    Args:
        tier: "secondary" only (primary is required)
        project_path: Optional project path

    Returns:
        True if cleared, False if not set
    """
    if tier == "primary":
        raise ValueError("Cannot clear primary reviewer. Use set_reviewer to change it.")

    config = get_project_config(project_path)
    if not config:
        return False

    reviewers = config.get("reviewers", {})
    if tier in reviewers:
        del reviewers[tier]
        config["reviewers"] = reviewers
        save_project_config(config, project_path)
        return True
    return False


# =============================================================================
# Autonomy Configuration
# =============================================================================


class AutonomyConfigError(ValueError):
    """Error raised when autonomy configuration is invalid."""

    pass


def validate_autonomy_config(autonomy_data: dict[str, Any]) -> list[str]:
    """Validate autonomy configuration.

    Args:
        autonomy_data: Raw autonomy config dict from YAML

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []

    # Validate level
    level = autonomy_data.get("level")
    if level is not None and level not in VALID_AUTONOMY_LEVELS:
        errors.append(
            f"Invalid autonomy level: '{level}'. "
            f"Valid: {', '.join(VALID_AUTONOMY_LEVELS)}"
        )

    # Validate checkpoint_policy
    checkpoint_policy = autonomy_data.get("checkpoint_policy", {})
    for severity, action in checkpoint_policy.items():
        if severity not in VALID_SEVERITIES:
            errors.append(
                f"Invalid severity in checkpoint_policy: '{severity}'. "
                f"Valid: {', '.join(VALID_SEVERITIES)}"
            )
        if action not in VALID_ACTIONS:
            errors.append(
                f"Invalid action in checkpoint_policy: '{action}'. "
                f"Valid: {', '.join(VALID_ACTIONS)}"
            )

    # Validate require_approval_for
    require_approval_for = autonomy_data.get("require_approval_for", [])
    if not isinstance(require_approval_for, list):
        errors.append("require_approval_for must be a list")
    else:
        raf_list = cast(list[Any], require_approval_for)
        for raf_item in raf_list:
            if not isinstance(raf_item, str):
                errors.append("require_approval_for must be a list of strings")
                break

    return errors


def get_autonomy_config(project_path: str | None = None) -> AutonomyConfig:
    """Get autonomy configuration for a project.

    Returns default (supervised) if not configured.

    Args:
        project_path: Optional project path

    Returns:
        AutonomyConfig instance
    """
    config = get_project_config(project_path)
    if not config:
        return AutonomyConfig()

    autonomy_data = config.get("autonomy", {})

    # Validate before parsing
    errors = validate_autonomy_config(autonomy_data)
    if errors:
        raise AutonomyConfigError(f"Invalid autonomy config: {'; '.join(errors)}")

    return AutonomyConfig.from_dict(autonomy_data)


def set_autonomy_level(
    level: str,
    project_path: str | None = None,
) -> AutonomyConfig:
    """Set the autonomy level.

    Args:
        level: Autonomy level (hitl, supervised, autonomous, yolo)
        project_path: Optional project path

    Returns:
        Updated AutonomyConfig
    """
    if level not in VALID_AUTONOMY_LEVELS:
        raise ValueError(
            f"Invalid autonomy level: '{level}'. "
            f"Valid: {', '.join(VALID_AUTONOMY_LEVELS)}"
        )

    config = get_project_config(project_path)
    if not config:
        raise ValueError("Project not initialized. Run 'glee init' first.")

    autonomy_data = config.get("autonomy", {})
    autonomy_data["level"] = level
    config["autonomy"] = autonomy_data

    save_project_config(config, project_path)
    return AutonomyConfig.from_dict(autonomy_data)


def set_checkpoint_policy(
    severity: str,
    action: str,
    project_path: str | None = None,
) -> AutonomyConfig:
    """Set a checkpoint policy override for a specific severity.

    Args:
        severity: Checkpoint severity (low, medium, high, critical)
        action: Action to take (auto, suspend)
        project_path: Optional project path

    Returns:
        Updated AutonomyConfig
    """
    if severity not in VALID_SEVERITIES:
        raise ValueError(
            f"Invalid severity: '{severity}'. Valid: {', '.join(VALID_SEVERITIES)}"
        )
    if action not in VALID_ACTIONS:
        raise ValueError(
            f"Invalid action: '{action}'. Valid: {', '.join(VALID_ACTIONS)}"
        )

    config = get_project_config(project_path)
    if not config:
        raise ValueError("Project not initialized. Run 'glee init' first.")

    autonomy_data = config.get("autonomy", {})
    if "checkpoint_policy" not in autonomy_data:
        autonomy_data["checkpoint_policy"] = {}
    autonomy_data["checkpoint_policy"][severity] = action
    config["autonomy"] = autonomy_data

    save_project_config(config, project_path)
    return AutonomyConfig.from_dict(autonomy_data)


def add_require_approval_for(
    checkpoint_type: str,
    project_path: str | None = None,
) -> AutonomyConfig:
    """Add a checkpoint type that always requires approval.

    Args:
        checkpoint_type: Type of checkpoint (e.g., "commit", "deploy", "delete")
        project_path: Optional project path

    Returns:
        Updated AutonomyConfig
    """
    config = get_project_config(project_path)
    if not config:
        raise ValueError("Project not initialized. Run 'glee init' first.")

    autonomy_data = config.get("autonomy", {})
    if "require_approval_for" not in autonomy_data:
        autonomy_data["require_approval_for"] = []

    if checkpoint_type not in autonomy_data["require_approval_for"]:
        autonomy_data["require_approval_for"].append(checkpoint_type)

    config["autonomy"] = autonomy_data

    save_project_config(config, project_path)
    return AutonomyConfig.from_dict(autonomy_data)


def remove_require_approval_for(
    checkpoint_type: str,
    project_path: str | None = None,
) -> AutonomyConfig:
    """Remove a checkpoint type from require_approval_for.

    Args:
        checkpoint_type: Type of checkpoint to remove
        project_path: Optional project path

    Returns:
        Updated AutonomyConfig
    """
    config = get_project_config(project_path)
    if not config:
        raise ValueError("Project not initialized. Run 'glee init' first.")

    autonomy_data = config.get("autonomy", {})
    require_list = autonomy_data.get("require_approval_for", [])

    if checkpoint_type in require_list:
        require_list.remove(checkpoint_type)
        autonomy_data["require_approval_for"] = require_list
        config["autonomy"] = autonomy_data
        save_project_config(config, project_path)

    return AutonomyConfig.from_dict(autonomy_data)


def clear_checkpoint_policy(
    severity: str | None = None,
    project_path: str | None = None,
) -> AutonomyConfig:
    """Clear checkpoint policy overrides.

    Args:
        severity: Specific severity to clear, or None to clear all
        project_path: Optional project path

    Returns:
        Updated AutonomyConfig
    """
    config = get_project_config(project_path)
    if not config:
        raise ValueError("Project not initialized. Run 'glee init' first.")

    autonomy_data = config.get("autonomy", {})
    checkpoint_policy = autonomy_data.get("checkpoint_policy", {})

    if severity:
        if severity in checkpoint_policy:
            del checkpoint_policy[severity]
    else:
        checkpoint_policy = {}

    autonomy_data["checkpoint_policy"] = checkpoint_policy
    config["autonomy"] = autonomy_data

    save_project_config(config, project_path)
    return AutonomyConfig.from_dict(autonomy_data)
