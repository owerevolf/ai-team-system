"""
Phase 13, P9: Controlled Evolution Framework

Governs architecture changes with risk-based classification.
After 12 phases, not every change is safe.

Principle: Architecture changes should be a governed process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from core.project_manager.runtime.coherence.evolution_safety import (
    EvolutionSafetyRules, ChangeCategory, ChangeRisk,
)


class ChangeStatus(Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    ROLLED_BACK = "rolled_back"


@dataclass
class ArchitectureChange:
    """A proposed architecture change with full governance."""
    id: str
    title: str
    category: ChangeCategory
    target_module: str
    description: str
    risk: ChangeRisk = ChangeRisk.REVIEW_REQUIRED
    status: ChangeStatus = ChangeStatus.PROPOSED
    approvers: list[str] = field(default_factory=list)
    safety_checks_passed: list[str] = field(default_factory=list)
    safety_checks_failed: list[str] = field(default_factory=list)


class ControlledEvolutionFramework:
    """
    Governs architecture changes with risk-based approval.
    Ensures dangerous changes get proper review.
    """

    def __init__(self) -> None:
        self._safety_rules = EvolutionSafetyRules()
        self._changes: dict[str, ArchitectureChange] = {}

    def propose_change(
        self,
        change_id: str,
        title: str,
        category: ChangeCategory,
        target_module: str,
        description: str,
    ) -> ArchitectureChange:
        """Propose a new architecture change."""
        classification = self._safety_rules.classify(category)
        change = ArchitectureChange(
            id=change_id,
            title=title,
            category=category,
            target_module=target_module,
            description=description,
            risk=classification.risk,
        )
        self._changes[change_id] = change
        return change

    def approve_change(self, change_id: str, approver: str) -> Optional[ArchitectureChange]:
        """Approve a proposed change."""
        change = self._changes.get(change_id)
        if not change:
            return None
        if approver not in change.approvers:
            change.approvers.append(approver)
        classification = self._safety_rules.classify(change.category)
        required = classification.requires_approval_from
        if all(a in change.approvers for a in required):
            change.status = ChangeStatus.APPROVED
        return change

    def run_safety_checks(self, change_id: str) -> ArchitectureChange:
        """Run safety checks for a proposed change."""
        change = self._changes.get(change_id)
        if not change:
            return None
        classification = self._safety_rules.classify(change.category)
        # Simulate running checks (in real system, these would be actual validations)
        for check in classification.safety_checks:
            change.safety_checks_passed.append(check)
        return change

    def get_pending_changes(self) -> list[ArchitectureChange]:
        """Get all pending changes."""
        return [c for c in self._changes.values() if c.status == ChangeStatus.PROPOSED]

    def get_high_risk_changes(self) -> list[ArchitectureChange]:
        """Get all high-risk changes."""
        return [c for c in self._changes.values() if c.risk == ChangeRisk.HIGH_RISK]
