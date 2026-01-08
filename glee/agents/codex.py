"""Codex CLI agent adapter."""

import json
from typing import Any

from .base import AgentResult, BaseAgent
from .prompts import code_prompt, judge_prompt, process_feedback_prompt, review_prompt


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

    def run_review(self, target: str = ".", focus: list[str] | None = None) -> AgentResult:
        """Run a code review with Codex.

        Args:
            target: What to review - file path, directory, 'git:changes', 'git:staged', or description
            focus: Optional focus areas (security, performance, etc.)
        """
        prompt = review_prompt(target, focus)
        return self.run(prompt)

    def run_code(self, task: str, files: list[str] | None = None) -> AgentResult:
        """Run a coding task with Codex.

        Args:
            task: Description of the coding task
            files: Optional list of files to focus on
        """
        prompt = code_prompt(task, files)
        return self.run(prompt)

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
        return self.run(prompt)

    def run_process_feedback(self, review_feedback: str) -> AgentResult:
        """Process review feedback and decide whether to accept or dispute.

        Args:
            review_feedback: The structured review feedback from reviewer

        Returns:
            AgentResult with acceptance or objection for each item
        """
        prompt = process_feedback_prompt(review_feedback)
        return self.run(prompt)
