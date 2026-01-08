"""Base agent interface for CLI agents."""

import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from glee.logging import get_agent_logger


@dataclass
class AgentResult:
    """Result from an agent invocation."""

    output: str
    error: str | None = None
    exit_code: int = 0
    run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=lambda: {})

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and self.error is None


class BaseAgent(ABC):
    """Base class for CLI agent wrappers."""

    name: str
    command: str
    capabilities: list[str]

    def __init__(self, project_path: Path | None = None):
        self._available: bool | None = None
        self.project_path = project_path

    def is_available(self) -> bool:
        """Check if the agent CLI is installed and available."""
        if self._available is None:
            self._available = shutil.which(self.command) is not None
        return self._available

    def get_version(self) -> str | None:
        """Get the agent's version."""
        if not self.is_available():
            return None
        try:
            result = subprocess.run(
                [self.command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception:
            return None

    @abstractmethod
    def run(self, prompt: str, **kwargs: Any) -> AgentResult:
        """Run the agent with a prompt."""
        pass

    @abstractmethod
    def run_review(self, files: list[str], focus: list[str] | None = None) -> AgentResult:
        """Run a code review."""
        pass

    def _run_subprocess(
        self,
        args: list[str],
        prompt: str = "",
        timeout: int = 300,
        cwd: str | None = None,
    ) -> AgentResult:
        """Run a subprocess and capture output.

        Args:
            args: Command arguments to run.
            prompt: The prompt sent to the agent (for logging).
            timeout: Timeout in seconds.
            cwd: Working directory.

        Returns:
            AgentResult with output, error, and run_id for log lookup.
        """
        start_time = time.time()
        run_id = None

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # Log to SQLite
            agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
            if agent_logger:
                run_id = agent_logger.log(
                    agent=self.name,
                    prompt=prompt,
                    output=result.stdout,
                    raw=result.stdout,
                    error=result.stderr if result.returncode != 0 else None,
                    exit_code=result.returncode,
                    duration_ms=duration_ms,
                )

            return AgentResult(
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode,
                run_id=run_id,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Command timed out after {timeout} seconds"

            agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
            if agent_logger:
                run_id = agent_logger.log(
                    agent=self.name,
                    prompt=prompt,
                    error=error_msg,
                    exit_code=-1,
                    duration_ms=duration_ms,
                )

            return AgentResult(
                output="",
                error=error_msg,
                exit_code=-1,
                run_id=run_id,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            agent_logger = get_agent_logger(self.project_path) if self.project_path else get_agent_logger()
            if agent_logger:
                run_id = agent_logger.log(
                    agent=self.name,
                    prompt=prompt,
                    error=str(e),
                    exit_code=-1,
                    duration_ms=duration_ms,
                )

            return AgentResult(
                output="",
                error=str(e),
                exit_code=-1,
                run_id=run_id,
            )
