"""Tests for autonomy configuration and checkpoint handling."""

import pytest

from glee.types import (
    AutonomyConfig,
    AutonomyLevel,
    Checkpoint,
    CheckpointAction,
    CheckpointError,
    CheckpointSeverity,
    DEFAULT_CHECKPOINT_POLICIES,
)
from glee.config import validate_autonomy_config


class TestAutonomyLevel:
    """Tests for AutonomyLevel enum."""

    def test_level_values(self):
        assert AutonomyLevel.HITL == "hitl"
        assert AutonomyLevel.SUPERVISED == "supervised"
        assert AutonomyLevel.AUTONOMOUS == "autonomous"
        assert AutonomyLevel.YOLO == "yolo"

    def test_level_from_string(self):
        assert AutonomyLevel("hitl") == AutonomyLevel.HITL
        assert AutonomyLevel("supervised") == AutonomyLevel.SUPERVISED


class TestCheckpointSeverity:
    """Tests for CheckpointSeverity enum."""

    def test_severity_values(self):
        assert CheckpointSeverity.LOW == "low"
        assert CheckpointSeverity.MEDIUM == "medium"
        assert CheckpointSeverity.HIGH == "high"
        assert CheckpointSeverity.CRITICAL == "critical"


class TestDefaultCheckpointPolicies:
    """Tests for default checkpoint policies."""

    def test_hitl_suspends_all(self):
        policy = DEFAULT_CHECKPOINT_POLICIES[AutonomyLevel.HITL]
        for severity in CheckpointSeverity:
            assert policy[severity] == CheckpointAction.SUSPEND

    def test_supervised_suspends_high_and_critical(self):
        policy = DEFAULT_CHECKPOINT_POLICIES[AutonomyLevel.SUPERVISED]
        assert policy[CheckpointSeverity.LOW] == CheckpointAction.AUTO
        assert policy[CheckpointSeverity.MEDIUM] == CheckpointAction.AUTO
        assert policy[CheckpointSeverity.HIGH] == CheckpointAction.SUSPEND
        assert policy[CheckpointSeverity.CRITICAL] == CheckpointAction.SUSPEND

    def test_autonomous_suspends_critical_only(self):
        policy = DEFAULT_CHECKPOINT_POLICIES[AutonomyLevel.AUTONOMOUS]
        assert policy[CheckpointSeverity.LOW] == CheckpointAction.AUTO
        assert policy[CheckpointSeverity.MEDIUM] == CheckpointAction.AUTO
        assert policy[CheckpointSeverity.HIGH] == CheckpointAction.AUTO
        assert policy[CheckpointSeverity.CRITICAL] == CheckpointAction.SUSPEND

    def test_yolo_auto_all(self):
        policy = DEFAULT_CHECKPOINT_POLICIES[AutonomyLevel.YOLO]
        for severity in CheckpointSeverity:
            assert policy[severity] == CheckpointAction.AUTO


class TestAutonomyConfig:
    """Tests for AutonomyConfig class."""

    def test_default_config(self):
        config = AutonomyConfig()
        assert config.level == AutonomyLevel.SUPERVISED
        assert config.checkpoint_policy == {}
        assert config.require_approval_for == []

    def test_should_suspend_default_supervised(self):
        config = AutonomyConfig()
        assert not config.should_suspend(CheckpointSeverity.LOW)
        assert not config.should_suspend(CheckpointSeverity.MEDIUM)
        assert config.should_suspend(CheckpointSeverity.HIGH)
        assert config.should_suspend(CheckpointSeverity.CRITICAL)

    def test_should_suspend_hitl(self):
        config = AutonomyConfig(level=AutonomyLevel.HITL)
        assert config.should_suspend(CheckpointSeverity.LOW)
        assert config.should_suspend(CheckpointSeverity.MEDIUM)
        assert config.should_suspend(CheckpointSeverity.HIGH)
        assert config.should_suspend(CheckpointSeverity.CRITICAL)

    def test_should_suspend_yolo(self):
        config = AutonomyConfig(level=AutonomyLevel.YOLO)
        assert not config.should_suspend(CheckpointSeverity.LOW)
        assert not config.should_suspend(CheckpointSeverity.MEDIUM)
        assert not config.should_suspend(CheckpointSeverity.HIGH)
        assert not config.should_suspend(CheckpointSeverity.CRITICAL)

    def test_checkpoint_policy_override(self):
        config = AutonomyConfig(
            level=AutonomyLevel.SUPERVISED,
            checkpoint_policy={
                CheckpointSeverity.LOW: CheckpointAction.SUSPEND,  # Override: normally auto
                CheckpointSeverity.HIGH: CheckpointAction.AUTO,  # Override: normally suspend
            },
        )
        assert config.should_suspend(CheckpointSeverity.LOW)  # Now suspends
        assert not config.should_suspend(CheckpointSeverity.MEDIUM)  # Still auto
        assert not config.should_suspend(CheckpointSeverity.HIGH)  # Now auto
        assert config.should_suspend(CheckpointSeverity.CRITICAL)  # Still suspend

    def test_require_approval_for_overrides_policy(self):
        config = AutonomyConfig(
            level=AutonomyLevel.YOLO,  # All auto by default
            require_approval_for=["commit", "deploy"],
        )
        # Without checkpoint_type, follows default (all auto in yolo)
        assert not config.should_suspend(CheckpointSeverity.LOW)
        assert not config.should_suspend(CheckpointSeverity.CRITICAL)

        # With checkpoint_type in require_approval_for, always suspends
        assert config.should_suspend(CheckpointSeverity.LOW, checkpoint_type="commit")
        assert config.should_suspend(CheckpointSeverity.CRITICAL, checkpoint_type="deploy")

        # Checkpoint types not in list follow normal policy
        assert not config.should_suspend(CheckpointSeverity.CRITICAL, checkpoint_type="file_write")

    def test_get_effective_policy(self):
        config = AutonomyConfig(
            level=AutonomyLevel.SUPERVISED,
            checkpoint_policy={
                CheckpointSeverity.LOW: CheckpointAction.SUSPEND,
            },
        )
        effective = config.get_effective_policy()
        assert effective[CheckpointSeverity.LOW] == CheckpointAction.SUSPEND
        assert effective[CheckpointSeverity.MEDIUM] == CheckpointAction.AUTO
        assert effective[CheckpointSeverity.HIGH] == CheckpointAction.SUSPEND

    def test_from_dict(self):
        data = {
            "level": "autonomous",
            "checkpoint_policy": {
                "low": "suspend",
                "medium": "suspend",
            },
            "require_approval_for": ["commit", "delete"],
        }
        config = AutonomyConfig.from_dict(data)
        assert config.level == AutonomyLevel.AUTONOMOUS
        assert config.checkpoint_policy[CheckpointSeverity.LOW] == CheckpointAction.SUSPEND
        assert config.checkpoint_policy[CheckpointSeverity.MEDIUM] == CheckpointAction.SUSPEND
        assert config.require_approval_for == ["commit", "delete"]

    def test_from_dict_empty(self):
        config = AutonomyConfig.from_dict({})
        assert config.level == AutonomyLevel.SUPERVISED
        assert config.checkpoint_policy == {}
        assert config.require_approval_for == []

    def test_to_dict(self):
        config = AutonomyConfig(
            level=AutonomyLevel.AUTONOMOUS,
            checkpoint_policy={
                CheckpointSeverity.HIGH: CheckpointAction.SUSPEND,
            },
            require_approval_for=["deploy"],
        )
        data = config.to_dict()
        assert data["level"] == "autonomous"
        assert data["checkpoint_policy"] == {"high": "suspend"}
        assert data["require_approval_for"] == ["deploy"]

    def test_to_dict_minimal(self):
        config = AutonomyConfig()
        data = config.to_dict()
        assert data == {"level": "supervised"}


class TestCheckpoint:
    """Tests for Checkpoint dataclass."""

    def test_valid_checkpoint(self):
        cp = Checkpoint(
            checkpoint_id="cp-123",
            severity=CheckpointSeverity.HIGH,
            checkpoint_type="commit",
            description="Ready to commit changes",
        )
        assert cp.checkpoint_id == "cp-123"
        assert cp.severity == CheckpointSeverity.HIGH
        assert cp.checkpoint_type == "commit"

    def test_checkpoint_with_metadata(self):
        cp = Checkpoint(
            checkpoint_id="cp-456",
            severity=CheckpointSeverity.CRITICAL,
            checkpoint_type="deploy",
            description="Deploy to production",
            task_id="task-789",
            metadata={"environment": "prod", "version": "1.2.3"},
        )
        assert cp.task_id == "task-789"
        assert cp.metadata["environment"] == "prod"

    def test_checkpoint_without_severity_raises(self):
        with pytest.raises(CheckpointError, match="must have a severity"):
            Checkpoint(
                checkpoint_id="cp-bad",
                severity=None,  # type: ignore
                checkpoint_type="commit",
                description="Missing severity",
            )

    def test_checkpoint_without_type_raises(self):
        with pytest.raises(CheckpointError, match="must have a type"):
            Checkpoint(
                checkpoint_id="cp-bad",
                severity=CheckpointSeverity.LOW,
                checkpoint_type="",
                description="Missing type",
            )


class TestValidateAutonomyConfig:
    """Tests for validate_autonomy_config function."""

    def test_valid_config(self):
        data = {
            "level": "supervised",
            "checkpoint_policy": {
                "low": "auto",
                "high": "suspend",
            },
            "require_approval_for": ["commit"],
        }
        errors = validate_autonomy_config(data)
        assert errors == []

    def test_invalid_level(self):
        data = {"level": "invalid"}
        errors = validate_autonomy_config(data)
        assert len(errors) == 1
        assert "Invalid autonomy level" in errors[0]

    def test_invalid_severity_in_policy(self):
        data = {
            "checkpoint_policy": {
                "invalid_sev": "auto",
            }
        }
        errors = validate_autonomy_config(data)
        assert len(errors) == 1
        assert "Invalid severity" in errors[0]

    def test_invalid_action_in_policy(self):
        data = {
            "checkpoint_policy": {
                "low": "invalid_action",
            }
        }
        errors = validate_autonomy_config(data)
        assert len(errors) == 1
        assert "Invalid action" in errors[0]

    def test_require_approval_for_not_list(self):
        data = {"require_approval_for": "commit"}
        errors = validate_autonomy_config(data)
        assert len(errors) == 1
        assert "must be a list" in errors[0]

    def test_require_approval_for_not_strings(self):
        data = {"require_approval_for": [1, 2, 3]}
        errors = validate_autonomy_config(data)
        assert len(errors) == 1
        assert "list of strings" in errors[0]

    def test_multiple_errors(self):
        data = {
            "level": "bad",
            "checkpoint_policy": {"bad": "bad"},
        }
        errors = validate_autonomy_config(data)
        assert len(errors) == 3  # level + severity + action
