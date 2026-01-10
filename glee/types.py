"""Type definitions for Glee."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional


class ReviewStatus(StrEnum):
    """Status of a review session."""

    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    MAX_ITERATIONS = "max_iterations"


class AutonomyLevel(StrEnum):
    """Autonomy level for checkpoint handling."""

    HITL = "hitl"  # Human-in-the-loop: human approves every step
    SUPERVISED = "supervised"  # AI suggests, human approves major decisions (default)
    AUTONOMOUS = "autonomous"  # AI drives, human reviews at end
    YOLO = "yolo"  # AI drives, no human intervention


class CheckpointSeverity(StrEnum):
    """Severity level for checkpoints."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CheckpointAction(StrEnum):
    """Action to take at a checkpoint."""

    AUTO = "auto"  # Auto-continue without waiting
    SUSPEND = "suspend"  # Suspend and wait for human approval


# Default checkpoint policies per autonomy level
# Maps severity -> action for each level
DEFAULT_CHECKPOINT_POLICIES: dict[AutonomyLevel, dict[CheckpointSeverity, CheckpointAction]] = {
    AutonomyLevel.HITL: {
        CheckpointSeverity.LOW: CheckpointAction.SUSPEND,
        CheckpointSeverity.MEDIUM: CheckpointAction.SUSPEND,
        CheckpointSeverity.HIGH: CheckpointAction.SUSPEND,
        CheckpointSeverity.CRITICAL: CheckpointAction.SUSPEND,
    },
    AutonomyLevel.SUPERVISED: {
        CheckpointSeverity.LOW: CheckpointAction.AUTO,
        CheckpointSeverity.MEDIUM: CheckpointAction.AUTO,
        CheckpointSeverity.HIGH: CheckpointAction.SUSPEND,
        CheckpointSeverity.CRITICAL: CheckpointAction.SUSPEND,
    },
    AutonomyLevel.AUTONOMOUS: {
        CheckpointSeverity.LOW: CheckpointAction.AUTO,
        CheckpointSeverity.MEDIUM: CheckpointAction.AUTO,
        CheckpointSeverity.HIGH: CheckpointAction.AUTO,
        CheckpointSeverity.CRITICAL: CheckpointAction.SUSPEND,
    },
    AutonomyLevel.YOLO: {
        CheckpointSeverity.LOW: CheckpointAction.AUTO,
        CheckpointSeverity.MEDIUM: CheckpointAction.AUTO,
        CheckpointSeverity.HIGH: CheckpointAction.AUTO,
        CheckpointSeverity.CRITICAL: CheckpointAction.AUTO,
    },
}


@dataclass
class AutonomyConfig:
    """Autonomy configuration for checkpoint handling.

    Resolution order for should_suspend():
    1. require_approval_for (force suspend for specific checkpoint types)
    2. checkpoint_policy overrides (if configured)
    3. Autonomy level defaults
    """

    level: AutonomyLevel = AutonomyLevel.SUPERVISED
    checkpoint_policy: dict[CheckpointSeverity, CheckpointAction] = field(
        default_factory=lambda: {}  # type: ignore[arg-type]
    )
    require_approval_for: list[str] = field(
        default_factory=lambda: []  # type: ignore[arg-type]
    )

    def should_suspend(self, severity: CheckpointSeverity, checkpoint_type: str | None = None) -> bool:
        """Determine if a checkpoint should suspend based on policy.

        Args:
            severity: The severity level of the checkpoint
            checkpoint_type: Optional type of checkpoint (e.g., "commit", "deploy")

        Returns:
            True if the checkpoint should suspend and wait for approval
        """
        # 1. require_approval_for always overrides (forces suspend)
        if checkpoint_type and checkpoint_type in self.require_approval_for:
            return True

        # 2. checkpoint_policy overrides (if configured for this severity)
        if severity in self.checkpoint_policy:
            return self.checkpoint_policy[severity] == CheckpointAction.SUSPEND

        # 3. Fall back to autonomy level defaults
        default_policy = DEFAULT_CHECKPOINT_POLICIES[self.level]
        return default_policy[severity] == CheckpointAction.SUSPEND

    def get_effective_policy(self) -> dict[CheckpointSeverity, CheckpointAction]:
        """Get the effective checkpoint policy (defaults merged with overrides)."""
        policy = dict(DEFAULT_CHECKPOINT_POLICIES[self.level])
        policy.update(self.checkpoint_policy)
        return policy

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "AutonomyConfig":
        """Create AutonomyConfig from a dictionary (e.g., from YAML config)."""
        if not data:
            return cls()

        level_str = data.get("level", "supervised")
        level = AutonomyLevel(str(level_str))

        # Parse checkpoint_policy
        checkpoint_policy: dict[CheckpointSeverity, CheckpointAction] = {}
        raw_policy = data.get("checkpoint_policy")
        if isinstance(raw_policy, dict):
            for key, value in raw_policy.items():
                sev_str: str = str(key)
                action_str: str = str(value)
                severity = CheckpointSeverity(sev_str)
                action = CheckpointAction(action_str)
                checkpoint_policy[severity] = action

        raw_require = data.get("require_approval_for")
        require_approval_for: list[str] = []
        if isinstance(raw_require, list):
            for item in raw_require:
                require_approval_for.append(str(item))

        return cls(
            level=level,
            checkpoint_policy=checkpoint_policy,
            require_approval_for=require_approval_for,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for YAML serialization."""
        result: dict[str, object] = {"level": self.level.value}

        if self.checkpoint_policy:
            result["checkpoint_policy"] = {
                sev.value: action.value for sev, action in self.checkpoint_policy.items()
            }

        if self.require_approval_for:
            result["require_approval_for"] = self.require_approval_for

        return result


class CheckpointError(Exception):
    """Error raised when a checkpoint is invalid."""

    pass


@dataclass
class Checkpoint:
    """Represents a checkpoint in task execution.

    Every checkpoint must have a severity. Checkpoints without severity are invalid.
    """

    checkpoint_id: str
    severity: CheckpointSeverity
    checkpoint_type: str  # e.g., "commit", "deploy", "delete", "file_write"
    description: str
    task_id: Optional[str] = None
    metadata: dict[str, object] = field(
        default_factory=lambda: {}  # type: ignore[arg-type]
    )

    def __post_init__(self):
        """Validate checkpoint has required fields."""
        if not self.severity:
            raise CheckpointError(f"Checkpoint {self.checkpoint_id} must have a severity")
        if not self.checkpoint_type:
            raise CheckpointError(f"Checkpoint {self.checkpoint_id} must have a type")


@dataclass
class ReviewSession:
    """Represents a review session."""

    review_id: str
    files: list[str]
    project_path: str
    status: ReviewStatus = ReviewStatus.IN_PROGRESS
    iteration: int = 0
    max_iterations: int = 10
    feedback: Optional[str] = None
