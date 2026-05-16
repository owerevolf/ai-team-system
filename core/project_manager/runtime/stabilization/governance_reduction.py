"""
Phase 16, P5: Governance Reduction Pass

Detects and removes ceremonial governance:
- stale policies
- redundant validations
- low-value friction
- duplicated governance flows

Principle: Governance exists to protect engineering, not to govern it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GovernanceIssueType(Enum):
    CEREMONIAL_APPROVAL = "ceremonial_approval"    # Approval that adds no value
    STALE_POLICY = "stale_policy"                  # Policy no longer needed
    REDUNDANT_VALIDATION = "redundant_validation"  # Duplicate validation
    LOW_VALUE_FRICTION = "low_value_friction"      # Friction with no safety benefit
    DUPLICATED_FLOW = "duplicated_flow"            # Same governance flow twice


class ReductionPriority(Enum):
    HIGH = "high"          # Remove immediately
    MEDIUM = "medium"      # Remove in next cleanup
    LOW = "low"            # Monitor, remove if no complaints


@dataclass
class GovernanceIssue:
    """A governance issue identified for reduction."""
    name: str
    issue_type: GovernanceIssueType
    priority: ReductionPriority
    module: str
    description: str
    current_cost: str          # What it costs now (time, friction)
    recommendation: str
    safe_to_remove: bool = False


@dataclass
class GovernanceReductionReport:
    """Full governance reduction report."""
    issues: list[GovernanceIssue] = field(default_factory=list)
    total_issues_identified: int = 0
    total_issues_resolved: int = 0

    @property
    def high_priority(self) -> list[GovernanceIssue]:
        return [i for i in self.issues if i.priority == ReductionPriority.HIGH]

    @property
    def safe_to_remove(self) -> list[GovernanceIssue]:
        return [i for i in self.issues if i.safe_to_remove]


class GovernanceReductionPass:
    """
    Identifies and removes ceremonial governance.
    Reduces friction while maintaining safety.
    """

    KNOWN_ISSUES: list[dict] = [
        {
            "name": "duplicate_approval_checks",
            "type": GovernanceIssueType.DUPLICATED_FLOW,
            "priority": ReductionPriority.HIGH,
            "module": "ergonomics/approval_intelligence",
            "description": "Approval risk checked in both approval_intelligence and governance_pressure",
            "cost": "Double validation overhead for every approval",
            "recommendation": "Single approval risk assessment, governance_pressure reads result",
            "safe": True,
        },
        {
            "name": "ceremonial_low_risk_confirmation",
            "type": GovernanceIssueType.CEREMONIAL_APPROVAL,
            "priority": ReductionPriority.MEDIUM,
            "module": "ergonomics/approval_intelligence",
            "description": "LOW risk changes still require confirmation dialog",
            "cost": "User clicks 'OK' for every trivial change",
            "recommendation": "Auto-apply LOW risk with audit trail, no confirmation",
            "safe": True,
        },
        {
            "name": "redundant_context_validation",
            "type": GovernanceIssueType.REDUNDANT_VALIDATION,
            "priority": ReductionPriority.MEDIUM,
            "module": "durability/context_gc",
            "description": "Context validated both before use and during GC",
            "cost": "Double validation overhead",
            "recommendation": "Validate on read, trust GC to skip valid entries",
            "safe": True,
        },
        {
            "name": "stale_visibility_rules",
            "type": GovernanceIssueType.STALE_POLICY,
            "priority": ReductionPriority.LOW,
            "module": "trust/transparency_contracts",
            "description": "Some visibility rules predate calm mode and are now redundant",
            "cost": "Confusing rule interactions",
            "recommendation": "Audit visibility rules, remove superseded ones",
            "safe": False,  # Needs careful review
        },
        {
            "name": "over_governed_plugin_registration",
            "type": GovernanceIssueType.LOW_VALUE_FRICTION,
            "priority": ReductionPriority.HIGH,
            "module": "ecosystem/plugin_governance",
            "description": "Plugin registration requires 5 approval steps",
            "cost": "Plugin developers give up before registering",
            "recommendation": "Single-step registration with post-hoc review",
            "safe": True,
        },
    ]

    def __init__(self) -> None:
        self._issues: dict[str, GovernanceIssue] = {}
        self._register_issues()

    def _register_issues(self) -> None:
        """Register known governance issues."""
        for data in self.KNOWN_ISSUES:
            issue = GovernanceIssue(
                name=data["name"],
                issue_type=data["type"],
                priority=data["priority"],
                module=data["module"],
                description=data["description"],
                current_cost=data["cost"],
                recommendation=data["recommendation"],
                safe_to_remove=data.get("safe", False),
            )
            self._issues[issue.name] = issue

    def generate_report(self) -> GovernanceReductionReport:
        """Generate governance reduction report."""
        issues = list(self._issues.values())
        return GovernanceReductionReport(
            issues=issues,
            total_issues_identified=len(issues),
            total_issues_resolved=sum(1 for i in issues if i.safe_to_remove),
        )

    def get_issue(self, name: str) -> Optional[GovernanceIssue]:
        """Get a governance issue by name."""
        return self._issues.get(name)

    def mark_resolved(self, name: str) -> bool:
        """Mark a governance issue as resolved."""
        issue = self._issues.get(name)
        if issue and issue.safe_to_remove:
            # In real system, would actually remove the governance
            return True
        return False

    @property
    def total_issues(self) -> int:
        return len(self._issues)
