"""Codex CLI wrapper"""

import json
import os
import re
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from ..types import CodexOutput, ReviewIssue, IssueSeverity


@dataclass
class CodexReviewResult:
    """Result from Codex CLI call"""
    success: bool
    output: Optional[CodexOutput] = None
    raw_output: str = ""
    error: Optional[str] = None


def build_review_prompt(
    files: list[str],
    context: Optional[str] = None,
    focus_areas: Optional[list[str]] = None,
) -> str:
    """Build the review prompt for Codex"""
    focus_text = f"\nFocus areas: {', '.join(focus_areas)}" if focus_areas else ""
    context_text = f"\nContext: {context}" if context else ""

    return f"""You are a code reviewer. Review the following files for bugs, security issues, and improvements.
{context_text}{focus_text}

Files to review:
{chr(10).join(f'- {f}' for f in files)}

Please analyze the code and provide your response in the following JSON format:
{{
  "status": "approved" | "has_issues" | "needs_clarification",
  "issues": [
    {{
      "severity": "critical" | "warning" | "suggestion",
      "file": "path/to/file.ts",
      "line": 42,
      "message": "Description of the issue",
      "suggested_fix": "How to fix it"
    }}
  ],
  "questions": ["Any questions that need clarification from the developer"],
  "summary": "Brief summary of the review"
}}

If the code looks good with no issues, use status "approved" with an empty issues array.
If you find issues, use status "has_issues" and list all issues.
If you need clarification before completing the review, use status "needs_clarification".

IMPORTANT: Respond ONLY with the JSON object, no markdown or additional text."""


def parse_codex_output(stdout: str) -> Optional[CodexOutput]:
    """Parse JSONL output from Codex"""
    lines = stdout.strip().split("\n")

    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)

            # Look for message content
            if parsed.get("type") == "message" and parsed.get("message", {}).get("content"):
                content = parsed["message"]["content"]

                # Handle array content
                if isinstance(content, list):
                    for block in content:
                        if block.get("type") == "text" and block.get("text"):
                            json_match = re.search(r"\{[\s\S]*\}", block["text"])
                            if json_match:
                                try:
                                    data = json.loads(json_match.group())
                                    return _parse_codex_data(data)
                                except (json.JSONDecodeError, ValueError):
                                    continue

                # Handle string content
                elif isinstance(content, str):
                    json_match = re.search(r"\{[\s\S]*\}", content)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                            return _parse_codex_data(data)
                        except (json.JSONDecodeError, ValueError):
                            continue

        except json.JSONDecodeError:
            continue

    return None


def _parse_codex_data(data: dict) -> CodexOutput:
    """Parse raw dict into CodexOutput"""
    issues = []
    for issue in data.get("issues", []):
        issues.append(ReviewIssue(
            severity=IssueSeverity(issue.get("severity", "suggestion")),
            file=issue.get("file"),
            line=issue.get("line"),
            message=issue.get("message", ""),
            suggested_fix=issue.get("suggested_fix"),
        ))

    return CodexOutput(
        status=data.get("status", "has_issues"),
        issues=issues,
        questions=data.get("questions", []),
        summary=data.get("summary", ""),
    )


def review_with_codex(
    files: list[str],
    working_dir: Optional[str] = None,
    context: Optional[str] = None,
    focus_areas: Optional[list[str]] = None,
    timeout: int = 120,
) -> CodexReviewResult:
    """Run Codex review on files"""
    working_dir = working_dir or os.getcwd()
    prompt = build_review_prompt(files, context, focus_areas)

    try:
        result = subprocess.run(
            ["codex", "exec", "--json", "--full-auto", "-C", working_dir, prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
        )

        if result.returncode != 0:
            return CodexReviewResult(
                success=False,
                raw_output=result.stdout,
                error=result.stderr or f"Codex exited with code {result.returncode}",
            )

        output = parse_codex_output(result.stdout)

        if not output:
            return CodexReviewResult(
                success=True,
                raw_output=result.stdout,
                output=CodexOutput(
                    status="has_issues",
                    issues=[],
                    questions=[],
                    summary="Could not parse structured output from Codex. Raw output available.",
                ),
            )

        return CodexReviewResult(
            success=True,
            output=output,
            raw_output=result.stdout,
        )

    except subprocess.TimeoutExpired:
        return CodexReviewResult(
            success=False,
            error=f"Codex CLI timeout after {timeout}s",
        )
    except Exception as e:
        return CodexReviewResult(
            success=False,
            error=str(e),
        )


def get_changed_files(working_dir: Optional[str] = None) -> list[str]:
    """Get list of changed files using git"""
    working_dir = working_dir or os.getcwd()

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=working_dir,
        )

        if result.returncode != 0:
            return []

        files = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                # Skip the status prefix (e.g., "M ", "?? ")
                file_path = line[3:].strip()
                if not file_path.startswith("."):
                    files.append(file_path)

        return files

    except Exception:
        return []


def get_claude_session_id(project_path: str) -> Optional[str]:
    """Get the current Claude Code session ID"""
    try:
        # Convert path to Claude's directory format
        claude_dir = Path.home() / ".claude" / "projects"
        project_dir_name = project_path.lstrip("/").replace("/", "-")
        project_dir = claude_dir / project_dir_name

        if not project_dir.exists():
            return None

        # Find the most recently modified .jsonl file (excluding agent- files)
        session_files = [
            f for f in project_dir.glob("*.jsonl")
            if not f.name.startswith("agent-")
        ]

        if not session_files:
            return None

        # Sort by modification time, newest first
        session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        return session_files[0].stem

    except Exception:
        return None
