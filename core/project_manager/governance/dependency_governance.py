"""
P2 — Dependency Governance.

Defines dependency policies between subsystems.
Enforces: which subsystem can depend on which.
Detects: forbidden imports, boundary violations, cyclic dependencies.

Rules are EXPLICIT — not AI-generated.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum

from core.project_manager.governance.interfaces import Subsystem


class DependencyPolicy(Enum):
    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"
    READ_ONLY = "read_only"  # can read state, cannot modify


@dataclass
class DependencyRule:
    """A single dependency rule."""
    source: Subsystem
    target: Subsystem
    policy: DependencyPolicy
    reason: str = ""


@dataclass
class BoundaryViolation:
    """A detected boundary violation."""
    source: str  # module path
    target: str  # module path
    rule: DependencyRule
    severity: str = "error"  # error, warning
    message: str = ""


class DependencyGovernance:
    """
    Manages dependency policies between subsystems.

    Default rules (can be extended):
    - Telemetry cannot depend on Workflow Runtime
    - Validation cannot import UI
    - Scheduler cannot know Retrieval internals
    - Snapshot Service is read-only relative to PM Core
    - Risk Engine cannot depend on Scheduler
    - Lock Manager cannot depend on Workflow Runtime
    """

    def __init__(self):
        self._rules: List[DependencyRule] = []
        self._build_default_rules()

    def _build_default_rules(self) -> None:
        """Build the default dependency policy rules."""
        rules = [
            # Telemetry isolation
            DependencyRule(
                Subsystem.TELEMETRY, Subsystem.WORKFLOW,
                DependencyPolicy.FORBIDDEN,
                "Telemetry must not depend on Workflow Runtime — prevents circular event chains"
            ),
            DependencyRule(
                Subsystem.TELEMETRY, Subsystem.SCHEDULER,
                DependencyPolicy.FORBIDDEN,
                "Telemetry must not depend on Scheduler — metrics should be passive"
            ),
            # Validation isolation
            DependencyRule(
                Subsystem.VALIDATION, Subsystem.WORKFLOW,
                DependencyPolicy.FORBIDDEN,
                "Validation must not depend on Workflow — validation is a pure function"
            ),
            DependencyRule(
                Subsystem.VALIDATION, Subsystem.SCHEDULER,
                DependencyPolicy.FORBIDDEN,
                "Validation must not depend on Scheduler — no scheduling awareness"
            ),
            # Scheduler isolation
            DependencyRule(
                Subsystem.SCHEDULER, Subsystem.RETRIEVAL,
                DependencyPolicy.FORBIDDEN,
                "Scheduler must not depend on Retrieval internals — use interface only"
            ),
            DependencyRule(
                Subsystem.SCHEDULER, Subsystem.RISK,
                DependencyPolicy.FORBIDDEN,
                "Scheduler must not depend on Risk Engine — scheduling is deterministic"
            ),
            # Snapshot read-only relative to PM Core
            DependencyRule(
                Subsystem.SNAPSHOT, Subsystem.PM_CORE,
                DependencyPolicy.READ_ONLY,
                "Snapshot Service reads PM Core state but must not modify it"
            ),
            # Risk Engine isolation
            DependencyRule(
                Subsystem.RISK, Subsystem.WORKFLOW,
                DependencyPolicy.FORBIDDEN,
                "Risk Engine must not depend on Workflow — risk analysis is stateless"
            ),
            DependencyRule(
                Subsystem.RISK, Subsystem.SCHEDULER,
                DependencyPolicy.FORBIDDEN,
                "Risk Engine must not depend on Scheduler"
            ),
            # Lock Manager isolation
            DependencyRule(
                Subsystem.LOCK_MANAGER, Subsystem.WORKFLOW,
                DependencyPolicy.FORBIDDEN,
                "Lock Manager must not depend on Workflow — locks are lower-level"
            ),
            DependencyRule(
                Subsystem.LOCK_MANAGER, Subsystem.SCHEDULER,
                DependencyPolicy.FORBIDDEN,
                "Lock Manager must not depend on Scheduler"
            ),
            # Retrieval can read from PM Core (for file index)
            DependencyRule(
                Subsystem.RETRIEVAL, Subsystem.PM_CORE,
                DependencyPolicy.READ_ONLY,
                "Retrieval reads PM Core index but must not modify it"
            ),
            # Workflow can use Lock Manager and Snapshot
            DependencyRule(
                Subsystem.WORKFLOW, Subsystem.LOCK_MANAGER,
                DependencyPolicy.ALLOWED,
                "Workflow needs locks for task execution"
            ),
            DependencyRule(
                Subsystem.WORKFLOW, Subsystem.SNAPSHOT,
                DependencyPolicy.ALLOWED,
                "Workflow needs snapshots for rollback"
            ),
            # Scheduler can use Lock Manager
            DependencyRule(
                Subsystem.SCHEDULER, Subsystem.LOCK_MANAGER,
                DependencyPolicy.ALLOWED,
                "Scheduler needs to check lock availability"
            ),
        ]
        self._rules.extend(rules)

    def add_rule(self, rule: DependencyRule) -> None:
        """Add a custom dependency rule."""
        self._rules.append(rule)

    def check_dependency(self, source: Subsystem, target: Subsystem) -> Tuple[bool, str]:
        """
        Check if a dependency is allowed.

        Returns: (allowed, reason)
        """
        for rule in self._rules:
            if rule.source == source and rule.target == target:
                if rule.policy == DependencyPolicy.FORBIDDEN:
                    return False, f"FORBIDDEN: {rule.reason}"
                elif rule.policy == DependencyPolicy.READ_ONLY:
                    return True, f"READ_ONLY: {rule.reason}"
                else:
                    return True, f"ALLOWED: {rule.reason}"
        # No explicit rule = allowed by default (but logged)
        return True, "No explicit rule — allowed by default"

    def get_allowed_dependencies(self, source: Subsystem) -> List[DependencyRule]:
        """Get all allowed dependencies for a subsystem."""
        return [r for r in self._rules if r.source == source and r.policy != DependencyPolicy.FORBIDDEN]

    def get_forbidden_dependencies(self, source: Subsystem) -> List[DependencyRule]:
        """Get all forbidden dependencies for a subsystem."""
        return [r for r in self._rules if r.source == source and r.policy == DependencyPolicy.FORBIDDEN]

    def validate_all(self) -> List[str]:
        """Validate the entire dependency policy. Returns list of issues."""
        issues = []
        # Check for conflicting rules
        seen = {}
        for rule in self._rules:
            key = (rule.source, rule.target)
            if key in seen:
                issues.append(
                    f"Conflicting rules for {rule.source.value} -> {rule.target.value}: "
                    f"{seen[key].policy.value} vs {rule.policy.value}"
                )
            seen[key] = rule
        return issues

    def get_dependency_map(self) -> Dict[str, List[Dict[str, str]]]:
        """Get full dependency map for introspection."""
        result = {}
        for sub in Subsystem:
            deps = []
            for rule in self._rules:
                if rule.source == sub:
                    deps.append({
                        'target': rule.target.value,
                        'policy': rule.policy.value,
                        'reason': rule.reason,
                    })
            result[sub.value] = deps
        return result
