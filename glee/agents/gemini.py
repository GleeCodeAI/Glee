"""Gemini CLI agent adapter."""

from typing import Any

from .base import AgentResult, BaseAgent


class GeminiAgent(BaseAgent):
    """Wrapper for Gemini CLI."""

    name = "gemini"
    command = "gemini"
    capabilities = ["code", "review"]

    def run(self, prompt: str, **kwargs: Any) -> AgentResult:
        """Run Gemini with a prompt.

        Uses: gemini -p "prompt"
        """
        args = [
            self.command,
            "-p", prompt,
        ]

        # Add sandbox mode if specified
        if kwargs.get("sandbox"):
            args.append("--sandbox")

        # Add yolo mode for auto-approval
        if kwargs.get("yolo"):
            args.append("--yolo")

        return self._run_subprocess(args, prompt=prompt, timeout=kwargs.get("timeout", 300))

    def run_review(self, files: list[str], focus: list[str] | None = None) -> AgentResult:
        """Run a code review with Gemini.

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

        return self.run(prompt, sandbox=True)

    def run_code(self, task: str, files: list[str] | None = None) -> AgentResult:
        """Run a coding task with Gemini.

        Args:
            task: Description of the coding task
            files: Optional list of files to focus on
        """
        context = ""
        if files:
            context = f"Focus on these files: {', '.join(files)}. "

        prompt = f"{context}{task}"

        return self.run(prompt, yolo=True)
