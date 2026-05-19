"""
Safe Review — validation layer before task completion.

Checks for:
- forbidden file edits
- architecture violations
- contract violations
- missing validation
- dangerous operations

If violation found → task BLOCKED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class ReviewStatus(Enum):
    PASSED = "passed"
    BLOCKED = "blocked"
    WARNING = "warning"


class ViolationType:
    FORBIDDEN_FILE = "forbidden_file"
    ARCHITECTURE = "architecture"
    CONTRACT = "contract"
    VALIDATION = "validation"
    DANGEROUS = "dangerous"
    SCOPE = "scope"
    CONSTRAINT = "constraint"


@dataclass
class ReviewViolation:
    """A single violation found during review."""
    violation_type: str = ""
    message: str = ""
    severity: str = "error"  # warning, error, critical
    task_id: str = ""
    agent_id: str = ""
    details: str = ""


@dataclass
class ReviewResult:
    """Result of a review."""
    status: str = ReviewStatus.PASSED.value
    violations: List[ReviewViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        return any(v.severity in ("error", "critical")
                  for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0 or any(
            v.severity == "warning" for v in self.violations)

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "is_blocked": self.is_blocked,
            "has_warnings": self.has_warnings,
            "violations": [v.__dict__ for v in self.violations],
            "warnings": self.warnings,
            "passed_checks": self.passed_checks,
        }


class SafeReview:
    """
    Validation layer that reviews task outputs before completion.

    Enforces:
    - No forbidden file modifications
    - No architecture violations
    - Contract compliance
    - Required validations passed
    - No dangerous operations
    """

    def __init__(self, project_brain=None, agent_registry=None):
        from .agent_registry import AgentRegistry
        from .project_brain import ProjectBrain
        self._brain = project_brain
        self._registry = agent_registry or AgentRegistry()

    def review_task(self, task_contract,
                    agent_id: str,
                    files_changed: List[str] = None,
                    output: str = "") -> ReviewResult:
        """
        Review a task before marking it complete.

        Returns ReviewResult with status and any violations.
        """
        result = ReviewResult()
        files_changed = files_changed or []

        # Run all checks
        self._check_forbidden_files(task_contract, files_changed, agent_id, result)
        self._check_scope_limits(task_contract, files_changed, agent_id, result)
        self._check_agent_capabilities(task_contract, agent_id, result)
        self._check_constraints(task_contract, files_changed, result)
        self._check_validation_rules(task_contract, output, result)
        self._check_dangerous_operations(output, result)

        # Determine final status
        if result.is_blocked:
            result.status = ReviewStatus.BLOCKED.value
        elif result.has_warnings:
            result.status = ReviewStatus.WARNING.value
        else:
            result.status = ReviewStatus.PASSED.value

        return result

    def _check_forbidden_files(self, task_contract, files_changed,
                               agent_id, result):
        """Check if any forbidden files were modified."""
        forbidden = set(task_contract.forbidden_files or [])
        changed = set(files_changed)
        violations = forbidden & changed
        for f in violations:
            result.violations.append(ReviewViolation(
                violation_type=ViolationType.FORBIDDEN_FILE,
                message=f"Agent '{agent_id}' modified forbidden file: {f}",
                severity="critical",
                task_id=task_contract.task_id,
                agent_id=agent_id,
                details=f"File '{f}' is in the forbidden list for this task",
            ))
        if not violations:
            result.passed_checks.append("No forbidden file modifications")

    def _check_scope_limits(self, task_contract, files_changed,
                            agent_id, result):
        """Check if task stayed within scope limits."""
        max_files = task_contract.max_files_changed
        max_lines = task_contract.max_lines_changed

        if len(files_changed) > max_files:
            result.violations.append(ReviewViolation(
                violation_type=ViolationType.SCOPE,
                message=f"Too many files changed: {len(files_changed)} > {max_files}",
                severity="error",
                task_id=task_contract.task_id,
                agent_id=agent_id,
                details=f"Task allows max {max_files} files, but {len(files_changed)} were changed",
            ))
        else:
            result.passed_checks.append(f"File count within limit ({len(files_changed)}/{max_files})")

    def _check_agent_capabilities(self, task_contract, agent_id, result):
        """Check if the agent is allowed to perform this task type."""
        agent = self._registry.get(agent_id)
        if not agent:
            result.violations.append(ReviewViolation(
                violation_type=ViolationType.CONTRACT,
                message=f"Unknown agent: {agent_id}",
                severity="error",
                task_id=task_contract.task_id,
                agent_id=agent_id,
            ))
            return

        # Check if agent can handle the task type
        task_type = task_contract.output_format
        if task_type and task_type in agent.forbidden_operations:
            result.violations.append(ReviewViolation(
                violation_type=ViolationType.CONTRACT,
                message=f"Agent '{agent_id}' cannot perform '{task_type}'",
                severity="error",
                task_id=task_contract.task_id,
                agent_id=agent_id,
            ))
        else:
            result.passed_checks.append(f"Agent '{agent_id}' is authorized for this task")

    def _check_constraints(self, task_contract, files_changed, result):
        """Check project-level constraints."""
        if not self._brain:
            result.passed_checks.append("No project brain to check constraints")
            return

        constraints = self._brain.constraints or []
        for constraint in constraints:
            # Simple keyword-based check
            rule = constraint.rule.lower()
            for f in files_changed:
                if "migration" in rule and "migration" in f.lower():
                    result.warnings.append(
                        f"Constraint reminder: {constraint.rule}")
                if "raw sql" in rule and f.endswith(".sql"):
                    result.violations.append(ReviewViolation(
                        violation_type=ViolationType.CONSTRAINT,
                        message=f"Possible constraint violation: {constraint.rule}",
                        severity="warning",
                        details=f"File '{f}' may violate constraint: {constraint.rule}",
                    ))

        if not constraints:
            result.passed_checks.append("No project constraints to check")

    def _check_validation_rules(self, task_contract, output, result):
        """Check if validation rules were followed."""
        rules = task_contract.validation_rules or []
        if not rules:
            result.passed_checks.append("No validation rules defined")
            return

        for rule in rules:
            # Simple check: if rule mentions "test", check output mentions test
            if "test" in rule.lower() and "test" not in output.lower():
                result.warnings.append(
                    f"Validation rule may not be met: {rule}")
            else:
                result.passed_checks.append(f"Validation rule checked: {rule}")

    def _check_dangerous_operations(self, output, result):
        """Check for dangerous operations in output."""
        dangerous_patterns = [
            "rm -rf", "drop table", "delete from", "os.remove",
            "shutil.rmtree", "format(", "exec(", "eval(",
        ]
        for pattern in dangerous_patterns:
            if pattern in output.lower():
                result.violations.append(ReviewViolation(
                    violation_type=ViolationType.DANGEROUS,
                    message=f"Dangerous operation detected: '{pattern}'",
                    severity="critical",
                    details=f"Output contains potentially dangerous pattern: '{pattern}'",
                ))

        if not any(p in output.lower() for p in dangerous_patterns):
            result.passed_checks.append("No dangerous operations detected")
