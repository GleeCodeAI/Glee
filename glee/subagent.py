"""Subagent loader for glee_task.

Loads subagent definitions from .glee/agents/*.yml and prepares
them for execution.
"""

import re
from pathlib import Path
from typing import Any, TypedDict

import yaml


class SubagentInput(TypedDict, total=False):
    """Input parameter definition for a subagent."""

    name: str
    type: str
    description: str
    required: bool
    default: str | None


class SubagentSource(TypedDict, total=False):
    """Source tracking for imported subagents."""

    from_: str  # 'from' is reserved, use from_
    file: str
    imported_at: str


class Subagent(TypedDict, total=False):
    """A subagent definition loaded from .glee/agents/*.yml."""

    name: str
    description: str
    agent: str | None  # CLI to use: codex, claude, gemini
    prompt: str
    timeout_mins: int
    max_output_kb: int
    inputs: list[SubagentInput]
    tools: list[str]
    source: SubagentSource


class SubagentLoadError(Exception):
    """Error loading a subagent definition."""

    pass


def get_agents_dir(project_path: str | Path) -> Path:
    """Get the agents directory for a project."""
    return Path(project_path) / ".glee" / "agents"


def list_subagents(project_path: str | Path) -> list[str]:
    """List available subagent names."""
    agents_dir = get_agents_dir(project_path)
    if not agents_dir.exists():
        return []

    return [f.stem for f in agents_dir.glob("*.yml") if f.is_file()]


def load_subagent(project_path: str | Path, name: str) -> Subagent:
    """Load a subagent definition from .glee/agents/{name}.yml.

    Args:
        project_path: Path to the project root
        name: Subagent name (without .yml extension)

    Returns:
        Subagent definition

    Raises:
        SubagentLoadError: If the subagent cannot be loaded
    """
    agents_dir = get_agents_dir(project_path)
    agent_file = agents_dir / f"{name}.yml"

    if not agent_file.exists():
        available = list_subagents(project_path)
        if available:
            raise SubagentLoadError(
                f"Subagent not found: {name}. Available: {', '.join(available)}"
            )
        else:
            raise SubagentLoadError(
                f"Subagent not found: {name}. No subagents defined in .glee/agents/"
            )

    try:
        with open(agent_file) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SubagentLoadError(f"Invalid YAML in {agent_file}: {e}") from e

    if not isinstance(data, dict):
        raise SubagentLoadError(f"Invalid subagent format in {agent_file}: expected a mapping")

    # Validate required fields
    if "name" not in data:
        data["name"] = name  # Use filename as name if not specified

    if "prompt" not in data:
        raise SubagentLoadError(f"Missing required field 'prompt' in {agent_file}")

    # Set defaults
    subagent: Subagent = {
        "name": data.get("name", name),
        "description": data.get("description", ""),
        "agent": data.get("agent"),  # None means auto-select
        "prompt": data["prompt"],
        "timeout_mins": data.get("timeout_mins", 5),
        "max_output_kb": data.get("max_output_kb", 100),
        "inputs": data.get("inputs", []),
        "tools": data.get("tools", []),
    }

    # Handle source field (for imported agents)
    if "source" in data:
        source = data["source"]
        subagent["source"] = {
            "from_": source.get("from", ""),
            "file": source.get("file", ""),
            "imported_at": source.get("imported_at", ""),
        }

    return subagent


def render_prompt(
    subagent: Subagent,
    user_prompt: str,
    inputs: dict[str, Any] | None = None,
) -> str:
    """Render the subagent's prompt with input substitution.

    Args:
        subagent: The subagent definition
        user_prompt: The user's task prompt
        inputs: Optional input values for templating

    Returns:
        The rendered prompt combining subagent system prompt and user prompt
    """
    system_prompt = subagent.get("prompt", "")
    inputs = inputs or {}

    # Substitute ${var} patterns in the system prompt
    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in inputs:
            return str(inputs[var_name])
        # Check for default in subagent inputs
        for input_def in subagent.get("inputs", []):
            if input_def.get("name") == var_name and "default" in input_def:
                return str(input_def["default"])
        # Return original if no value found
        return match.group(0)

    system_prompt = re.sub(r"\$\{(\w+)\}", replace_var, system_prompt)

    # Combine system prompt with user prompt
    full_prompt = f"""<subagent_instructions>
{system_prompt}
</subagent_instructions>

<task>
{user_prompt}
</task>"""

    return full_prompt


def validate_inputs(
    subagent: Subagent,
    inputs: dict[str, Any] | None,
) -> list[str]:
    """Validate that required inputs are provided.

    Args:
        subagent: The subagent definition
        inputs: Provided input values

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []
    inputs = inputs or {}

    for input_def in subagent.get("inputs", []):
        name = input_def.get("name", "")
        required = input_def.get("required", False)
        has_default = "default" in input_def

        if required and not has_default and name not in inputs:
            errors.append(f"Missing required input: {name}")

    return errors
