"""
Failure Visibility Module (P15) — Phase 8

When something goes wrong, the user must understand:
  - What broke
  - Why it broke
  - Which workflow failed
  - How to recover
  - What rollback will do

No silent failures. No cryptic errors. Clear, actionable information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone


@dataclass
class FailureInfo:
    """Structured information about a failure."""
    failure_id: str
    timestamp: str
    component: str              # Which component failed
    operation: str             # What was being attempted
    error_type: str            # Category: validation | runtime | import | permission | timeout | unknown
    message: str               # Human-readable error message
    technical_details: str = ""  # Technical details for debugging
    affected_files: list[str] = field(default_factory=list)
    workflow_id: str = ""
    recovery_options: list[dict[str, str]] = field(default_factory=list)
    rollback_available: bool = False
    rollback_checkpoint: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "timestamp": self.timestamp,
            "component": self.component,
            "operation": self.operation,
            "error_type": self.error_type,
            "message": self.message,
            "technical_details": self.technical_details,
            "affected_files": self.affected_files,
            "workflow_id": self.workflow_id,
            "recovery_options": self.recovery_options,
            "rollback_available": self.rollback_available,
            "rollback_checkpoint": self.rollback_checkpoint,
        }


@dataclass
class RecoveryOption:
    """A single recovery option."""
    option_id: str
    name: str
    description: str
    action_type: str           # retry | rollback | skip | manual | restart
    risk_level: str = "low"
    estimated_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "name": self.name,
            "description": self.description,
            "action_type": self.action_type,
            "risk_level": self.risk_level,
            "estimated_time": self.estimated_time,
        }


class FailureVisibility:
    """
    Creates clear, actionable failure reports.

    Usage:
        fv = FailureVisibility()
        failure = fv.create_failure(
            component="RepoRepair",
            operation="fix_imports",
            error_type="import_error",
            message="Could not resolve import 'nonexistent_module'",
        )
        report = fv.format_failure_for_display(failure)
    """

    # User-friendly error type descriptions
    ERROR_TYPE_DESCRIPTIONS = {
        "validation": "A validation check failed. The data doesn't meet the expected format or rules.",
        "runtime": "An error occurred during execution. The operation could not be completed.",
        "import": "An import could not be resolved. A required module or file is missing.",
        "permission": "Access denied. You don't have permission to perform this operation.",
        "timeout": "The operation took too long and was cancelled.",
        "syntax": "There's a syntax error in the code. The file has invalid syntax.",
        "dependency": "A required dependency is missing or incompatible.",
        "unknown": "An unexpected error occurred. See technical details below.",
    }

    def create_failure(
        self,
        component: str,
        operation: str,
        error_type: str,
        message: str,
        technical_details: str = "",
        affected_files: Optional[list[str]] = None,
        workflow_id: str = "",
        rollback_checkpoint: str = "",
    ) -> FailureInfo:
        """
        Create a structured failure info object.

        Args:
            component: Which component failed
            operation: What was being attempted
            error_type: Category of error
            message: Human-readable error message
            technical_details: Technical details for debugging
            affected_files: List of files affected by the failure
            workflow_id: ID of the workflow that failed
            rollback_checkpoint: Checkpoint hash for rollback (if available)

        Returns:
            FailureInfo with recovery options
        """
        import uuid
        failure_id = f"fail-{uuid.uuid4().hex[:8]}"

        # Generate recovery options based on error type
        recovery_options = self._generate_recovery_options(
            error_type, rollback_checkpoint
        )

        return FailureInfo(
            failure_id=failure_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            component=component,
            operation=operation,
            error_type=error_type,
            message=message,
            technical_details=technical_details,
            affected_files=affected_files or [],
            workflow_id=workflow_id,
            recovery_options=[r.to_dict() for r in recovery_options],
            rollback_available=bool(rollback_checkpoint),
            rollback_checkpoint=rollback_checkpoint,
        )

    def _generate_recovery_options(
        self, error_type: str, rollback_checkpoint: str = ""
    ) -> list[RecoveryOption]:
        """Generate recovery options based on error type."""
        import uuid
        options: list[RecoveryOption] = []

        # Rollback option (if checkpoint available)
        if rollback_checkpoint:
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Rollback to checkpoint",
                description=f"Undo all changes and restore to checkpoint {rollback_checkpoint[:12]}",
                action_type="rollback",
                risk_level="low",
                estimated_time="< 1 minute",
            ))

        # Error-type specific options
        if error_type == "import":
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Fix imports manually",
                description="Open the affected files and fix the import statements manually",
                action_type="manual",
                risk_level="low",
            ))
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Install missing packages",
                description="Try installing the missing packages with pip/npm",
                action_type="retry",
                risk_level="low",
            ))

        elif error_type == "validation":
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Review validation errors",
                description="Check the validation report and fix the issues manually",
                action_type="manual",
                risk_level="low",
            ))
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Skip validation",
                description="Continue without validation (not recommended)",
                action_type="skip",
                risk_level="high",
            ))

        elif error_type == "permission":
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Fix permissions",
                description="Check file/directory permissions and try again",
                action_type="manual",
                risk_level="low",
            ))

        elif error_type == "timeout":
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Retry with longer timeout",
                description="Try again with an increased timeout limit",
                action_type="retry",
                risk_level="low",
            ))
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Run in smaller batches",
                description="Split the operation into smaller chunks",
                action_type="manual",
                risk_level="low",
            ))

        elif error_type == "dependency":
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Install dependencies",
                description="Install the missing dependencies",
                action_type="retry",
                risk_level="low",
            ))
            options.append(RecoveryOption(
                option_id=f"rec-{uuid.uuid4().hex[:6]}",
                name="Update dependency versions",
                description="Try updating to compatible versions",
                action_type="manual",
                risk_level="medium",
            ))

        # Always add a "get help" option
        options.append(RecoveryOption(
            option_id=f"rec-{uuid.uuid4().hex[:6]}",
            name="Get help",
            description="Show detailed documentation about this error type",
            action_type="manual",
            risk_level="low",
        ))

        return options

    def format_failure_for_display(self, failure: FailureInfo) -> str:
        """Format a failure as a human-readable display string."""
        lines: list[str] = []
        sep = "!" * 60

        lines.append(sep)
        lines.append("  SOMETHING WENT WRONG")
        lines.append(sep)
        lines.append("")

        # What happened
        lines.append(f"  What:    {failure.message}")
        lines.append(f"  Where:   {failure.component} (during {failure.operation})")
        lines.append(f"  When:    {failure.timestamp}")
        lines.append("")

        # Error type explanation
        type_desc = self.ERROR_TYPE_DESCRIPTIONS.get(
            failure.error_type, self.ERROR_TYPE_DESCRIPTIONS["unknown"]
        )
        lines.append(f"  Error Type: {failure.error_type}")
        lines.append(f"  Explanation: {type_desc}")
        lines.append("")

        # Affected files
        if failure.affected_files:
            lines.append("  Affected Files:")
            for f in failure.affected_files:
                lines.append(f"    - {f}")
            lines.append("")

        # Technical details
        if failure.technical_details:
            lines.append("  Technical Details:")
            lines.append(f"    {failure.technical_details}")
            lines.append("")

        # Recovery options
        lines.append("  What You Can Do:")
        lines.append("  " + "-" * 40)
        for i, opt in enumerate(failure.recovery_options, 1):
            risk_tag = f"[{opt['risk_level'].upper()}]"
            lines.append(f"    {i}. {opt['name']} {risk_tag}")
            lines.append(f"       {opt['description']}")
            if opt["estimated_time"]:
                lines.append(f"       Estimated time: {opt['estimated_time']}")
            lines.append("")

        # Rollback info
        if failure.rollback_available:
            lines.append("  Rollback Available:")
            lines.append(f"    Checkpoint: {failure.rollback_checkpoint[:12]}")
            lines.append("    This will undo all changes made during the failed operation.")
            lines.append("")

        lines.append(sep)
        return "\n".join(lines)

    def format_failure_brief(self, failure: FailureInfo) -> str:
        """Format a brief one-line failure summary."""
        return f"[{failure.error_type.upper()}] {failure.component}: {failure.message}"
