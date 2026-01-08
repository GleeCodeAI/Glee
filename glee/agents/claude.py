"""Claude Code CLI agent adapter."""

from typing import Any

from .base import AgentResult, BaseAgent


class ClaudeAgent(BaseAgent):
    """Wrapper for Claude Code CLI."""

    name = "claude"
    command = "claude"
    capabilities = ["code", "review", "explain"]

    def run(self, prompt: str, **kwargs: Any) -> AgentResult:
        """Run Claude with a prompt.

        Uses: claude -p "prompt" --output-format text
        """
        args = [
            self.command,
            "-p", prompt,
            "--output-format", "text",
        ]

        # Add any additional flags
        if kwargs.get("allowedTools"):
            for tool in kwargs["allowedTools"]:
                args.extend(["--allowedTools", tool])

        return self._run_subprocess(args, prompt=prompt, timeout=kwargs.get("timeout", 300))

    def run_review(self, files: list[str], focus: list[str] | None = None) -> AgentResult:
        """Run a code review with Claude.

        Args:
            files: List of file paths to review
            focus: Optional focus areas (security, performance, etc.)
        """
        # Build review prompt
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

        return self.run(prompt, allowedTools=["Read", "Glob", "Grep"])

    def run_code(self, task: str, files: list[str] | None = None) -> AgentResult:
        """Run a coding task with Claude.

        Args:
            task: Description of the coding task
            files: Optional list of files to focus on
        """
        context = ""
        if files:
            context = f"Focus on these files: {', '.join(files)}. "

        prompt = f"""{context}{task}

Implement the requested changes. Use the available tools to read and modify files."""

        return self.run(
            prompt,
            allowedTools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        )
