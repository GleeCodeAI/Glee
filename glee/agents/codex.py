"""Codex CLI agent adapter."""

import json
from typing import Any

from .base import AgentResult, BaseAgent


class CodexAgent(BaseAgent):
    """Wrapper for Codex CLI."""

    name = "codex"
    command = "codex"
    capabilities = ["code", "review"]

    def run(self, prompt: str, **kwargs: Any) -> AgentResult:
        """Run Codex with a prompt.

        Uses: codex exec --json --full-auto "prompt"
        """
        args = [
            self.command,
            "exec",
            "--json",
            "--full-auto",
            prompt,
        ]

        result = self._run_subprocess(args, prompt=prompt, timeout=kwargs.get("timeout", 300))

        # Parse JSON output if available
        if result.success and result.output:
            try:
                parsed = self._parse_jsonl(result.output)
                result.metadata["parsed"] = parsed

                # Extract the final agent message
                for item in reversed(parsed):
                    # Handle item.completed with agent_message
                    if item.get("type") == "item.completed":
                        inner = item.get("item", {})
                        if inner.get("type") == "agent_message" and inner.get("text"):
                            result.output = inner["text"]
                            break
                    # Handle direct message type
                    elif item.get("type") == "message" and item.get("content"):
                        result.output = item["content"]
                        break
            except Exception:
                pass  # Keep raw output if parsing fails

        return result

    def _parse_jsonl(self, output: str) -> list[dict[str, Any]]:
        """Parse JSONL output from Codex."""
        results: list[dict[str, Any]] = []
        for line in output.strip().split("\n"):
            if line.strip():
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return results

    def run_review(self, files: list[str], focus: list[str] | None = None) -> AgentResult:
        """Run a code review with Codex.

        Args:
            files: List of file paths to review
            focus: Optional focus areas (security, performance, etc.)
        """
        focus_str = ""
        if focus:
            focus_str = f"Focus on: {', '.join(focus)}. "

        files_str = ", ".join(files) if files else "the current codebase"

        prompt = f"""Review the following code: {files_str}

{focus_str}Provide structured feedback with:
1. Critical issues (must fix)
2. Warnings (should fix)
3. Suggestions (nice to have)

For each issue, specify:
- File and line number
- Description
- Suggested fix

End with APPROVED if no critical issues, or NEEDS_CHANGES if issues found."""

        return self.run(prompt)

    def run_code(self, task: str, files: list[str] | None = None) -> AgentResult:
        """Run a coding task with Codex.

        Args:
            task: Description of the coding task
            files: Optional list of files to focus on
        """
        context = ""
        if files:
            context = f"Focus on these files: {', '.join(files)}. "

        prompt = f"{context}{task}"

        return self.run(prompt)
