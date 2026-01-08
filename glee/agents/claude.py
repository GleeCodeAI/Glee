"""Claude Code CLI agent adapter."""

from typing import Any

from .base import AgentResult, BaseAgent
from .prompts import code_prompt, judge_prompt, process_feedback_prompt, review_prompt


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

    def run_review(self, target: str = ".", focus: list[str] | None = None) -> AgentResult:
        """Run a code review with Claude.

        Args:
            target: What to review - file path, directory, 'git:changes', 'git:staged', or description
            focus: Optional focus areas (security, performance, etc.)
        """
        prompt = review_prompt(target, focus)
        return self.run(prompt, allowedTools=["Read", "Glob", "Grep", "Bash"])

    def run_code(self, task: str, files: list[str] | None = None) -> AgentResult:
        """Run a coding task with Claude.

        Args:
            task: Description of the coding task
            files: Optional list of files to focus on
        """
        prompt = code_prompt(task, files)
        return self.run(
            prompt,
            allowedTools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        )

    def run_judge(
        self,
        code_context: str,
        review_item: str,
        coder_objection: str,
    ) -> AgentResult:
        """Arbitrate a dispute between coder and reviewer.

        Args:
            code_context: The relevant code being disputed
            review_item: The reviewer's feedback (MUST or HIGH item)
            coder_objection: The coder's reasoning for disagreeing

        Returns:
            AgentResult with decision: ENFORCE, DISMISS, or ESCALATE
        """
        prompt = judge_prompt(code_context, review_item, coder_objection)
        return self.run(prompt, allowedTools=["Read", "Glob", "Grep"])

    def run_process_feedback(self, review_feedback: str) -> AgentResult:
        """Process review feedback and decide whether to accept or dispute.

        Args:
            review_feedback: The structured review feedback from reviewer

        Returns:
            AgentResult with acceptance or objection for each item
        """
        prompt = process_feedback_prompt(review_feedback)
        return self.run(
            prompt,
            allowedTools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        )
