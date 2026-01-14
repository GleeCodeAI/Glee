"""Warmup context builder for session continuity."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from glee.helpers import git_diff_since, git_status_changes, parse_metadata, parse_time
from glee.memory import Memory
from glee.agent_session import load_all_sessions

# Days after which overview memory is considered stale
BOOTSTRAP_STALE_DAYS = 7


def build_warmup_text(project_path: str | Path) -> str | None:
    project_path = Path(project_path)
    glee_dir = project_path / ".glee"
    if not glee_dir.exists():
        return None

    sections: list[str] = []
    reserved_categories = {
        "goal",
        "constraint",
        "decision",
        "open_loop",
        "recent_change",
        "session_summary",
        "overview",
    }

    sessions = load_all_sessions(project_path)

    if sessions:
        last = sessions[0]  # Already sorted by updated_at, newest first
        last_time = parse_time(last.get("updated_at"))
        last_when = last_time.strftime("%Y-%m-%d %H:%M") if last_time else "unknown time"
        last_desc = (last.get("description") or "").strip() or last.get("session_id", "unknown")
        last_status = last.get("status", "unknown")
        sections.append(
            "## Last Session\n"
            f"- {last.get('session_id', 'unknown')} ({last_status}, {last_when}): {last_desc}"
        )

    memory = Memory(str(project_path))
    try:
        # Bootstrap context (project overview)
        overview_entries = memory.get_by_category("overview")
        if overview_entries:
            entry = overview_entries[0]  # Should be a single comprehensive entry
            content = (entry.get("content") or "").strip()
            if content:
                # Check staleness
                created_at = entry.get("created_at")
                stale_warning = ""
                if created_at:
                    created_time = parse_time(created_at)
                    if created_time:
                        now = datetime.now(timezone.utc)
                        if created_time.tzinfo is None:
                            created_time = created_time.replace(tzinfo=timezone.utc)
                        age_days = (now - created_time).days
                        if age_days >= BOOTSTRAP_STALE_DAYS:
                            stale_warning = f"\n\n**Warning: Overview memory is {age_days} days old. Run `glee_memory_overview(generate=true)` to update it.**"

                sections.append(f"## Project Context\n{content}{stale_warning}")

        goal_entries = memory.get_by_category("goal")
        constraint_entries = memory.get_by_category("constraint")
        decision_entries = memory.get_by_category("decision")
        open_loop_entries = memory.get_by_category("open_loop")
        recent_change_entries = memory.get_by_category("recent_change")
        session_summaries = memory.get_by_category("session_summary")
        categories = memory.get_categories()

        if goal_entries:
            goal = (goal_entries[0].get("content") or "").strip()
            if goal:
                sections.append("## Current Goal\n" + goal)

        if constraint_entries:
            lines = ["## Key Constraints"]
            for entry in constraint_entries[:5]:
                content = (entry.get("content") or "").strip()
                if content:
                    lines.append(f"- {content}")
            if len(lines) > 1:
                sections.append("\n".join(lines))

        if decision_entries:
            lines = ["## Recent Decisions"]
            for entry in decision_entries[:3]:
                content = (entry.get("content") or "").strip()
                if content:
                    lines.append(f"- {content}")
            if len(lines) > 1:
                sections.append("\n".join(lines))

        git_base: str | None = None
        if session_summaries:
            # Use [-1] to get the latest session summary (appended, not cleared)
            meta = parse_metadata(session_summaries[-1].get("metadata"))
            git_base = meta.get("git_base")

        recent_changes, _ = git_diff_since(project_path, git_base, limit=10) if git_base else ([], False)
        if not recent_changes and recent_change_entries:
            recent_changes = [
                entry.get("content", "").strip()
                for entry in recent_change_entries[:10]
                if entry.get("content")
            ]
        if not recent_changes:
            recent_changes, _ = git_status_changes(project_path, limit=10)

        if recent_changes:
            lines = ["## Changes Since Last Session"]
            for line in recent_changes:
                lines.append(f"- {line}")
            sections.append("\n".join(lines))

        if open_loop_entries:
            lines = ["## Open Loops"]
            for entry in open_loop_entries[:5]:
                content = (entry.get("content") or "").strip()
                if content:
                    lines.append(f"- {content}")
            if len(lines) > 1:
                sections.append("\n".join(lines))
        elif sessions:
            open_loops = [s for s in sessions if s.get("status") in {"active", "error"}]
            if open_loops:
                lines = ["## Open Loops"]
                for s in open_loops[:5]:
                    desc = (s.get("description") or "").strip() or s.get("session_id", "unknown")
                    status = s.get("status", "unknown")
                    lines.append(f"- {s.get('session_id', 'unknown')} ({status}): {desc}")
                sections.append("\n".join(lines))

        extra_categories = [c for c in categories if c not in reserved_categories]
        if extra_categories:
            lines = ["## Memory"]
            for cat in extra_categories:
                entries = memory.get_by_category(cat)
                title = cat.replace("-", " ").replace("_", " ").title()
                lines.append(f"### {title}")
                for entry in entries[:5]:
                    content = (entry.get("content") or "").strip()
                    if content:
                        lines.append(f"- {content}")
                lines.append("")
            sections.append("\n".join(lines).strip())
    finally:
        memory.close()

    if not sections:
        return None

    return "\n\n".join(["# Glee Warmup", *sections])
