"""
P11 — Change Governance.

Tracks the impact of every change to the runtime.
Every modification is governed.

Tracks:
- Architectural impact (which subsystems affected)
- Governance violations (policy breaches)
- Complexity increase (budget consumption)
- Coupling growth (new dependencies)
- Stability degradation (health score change)
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ChangeType(Enum):
    ADD = "add"
    MODIFY = "modify"
    REMOVE = "remove"
    REFACTOR = "refactor"


class ImpactLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ChangeRecord:
    """A single change record."""
    change_id: str
    change_type: ChangeType
    target: str  # what was changed
    subsystem: str
    timestamp: float
    author: str = ""
    description: str = ""

    # Impact analysis
    architectural_impact: ImpactLevel = ImpactLevel.LOW
    affected_subsystems: List[str] = field(default_factory=list)
    new_dependencies: List[str] = field(default_factory=list)
    removed_dependencies: List[str] = field(default_factory=list)
    complexity_delta: float = 0.0  # positive = more complex

    # Governance
    policy_violations: List[str] = field(default_factory=list)
    budget_violations: List[str] = field(default_factory=list)
    requires_approval: bool = False
    approved: bool = False
    approved_by: str = ""

    # Stability
    health_before: float = 1.0
    health_after: float = 1.0
    stability_delta: float = 0.0


class ChangeGovernance:
    """
    Governs all changes to the platform.
    Tracks impact, violations, and stability effects.
    """

    def __init__(self):
        self._changes: List[ChangeRecord] = []
        self._lock = threading.Lock()
        self._max_changes = 10000

    def record_change(self, change: ChangeRecord) -> Dict[str, Any]:
        """
        Record a change and analyze its impact.
        Returns a summary of the change analysis.
        """
        with self._lock:
            # Analyze impact
            change = self._analyze_impact(change)

            self._changes.append(change)
            if len(self._changes) > self._max_changes:
                self._changes = self._changes[-self._max_changes:]

        return {
            'change_id': change.change_id,
            'type': change.change_type.value,
            'target': change.target,
            'impact': change.architectural_impact.value,
            'affected_subsystems': change.affected_subsystems,
            'complexity_delta': change.complexity_delta,
            'requires_approval': change.requires_approval,
            'policy_violations': change.policy_violations,
            'budget_violations': change.budget_violations,
        }

    def _analyze_impact(self, change: ChangeRecord) -> ChangeRecord:
        """Analyze the impact of a change."""
        # Determine impact level based on change type and target
        if change.change_type == ChangeType.REFACTOR:
            change.architectural_impact = ImpactLevel.HIGH
        elif change.change_type == ChangeType.ADD:
            if 'core/' in change.target:
                change.architectural_impact = ImpactLevel.MEDIUM
            else:
                change.architectural_impact = ImpactLevel.LOW
        elif change.change_type == ChangeType.REMOVE:
            change.architectural_impact = ImpactLevel.HIGH
            change.requires_approval = True
        elif change.change_type == ChangeType.MODIFY:
            if 'governance/' in change.target or 'policy' in change.target:
                change.architectural_impact = ImpactLevel.CRITICAL
                change.requires_approval = True
            elif 'core/' in change.target:
                change.architectural_impact = ImpactLevel.MEDIUM
            else:
                change.architectural_impact = ImpactLevel.LOW

        # Check if new dependencies increase coupling
        if change.new_dependencies:
            change.complexity_delta = len(change.new_dependencies) * 0.1

        return change

    def approve_change(self, change_id: str, approver: str) -> bool:
        """Approve a change that requires approval."""
        with self._lock:
            for change in self._changes:
                if change.change_id == change_id:
                    change.approved = True
                    change.approved_by = approver
                    return True
        return False

    def get_changes(self, subsystem: Optional[str] = None,
                    change_type: Optional[ChangeType] = None,
                    limit: int = 100) -> List[ChangeRecord]:
        """Get change records, optionally filtered."""
        changes = self._changes
        if subsystem:
            changes = [c for c in changes if c.subsystem == subsystem]
        if change_type:
            changes = [c for c in changes if c.change_type == change_type]
        return changes[-limit:]

    def get_impact_summary(self) -> Dict[str, Any]:
        """Get summary of all changes and their impact."""
        if not self._changes:
            return {'total_changes': 0}

        by_type = defaultdict(int)
        by_impact = defaultdict(int)
        total_complexity_delta = 0.0
        total_violations = 0

        for c in self._changes:
            by_type[c.change_type.value] += 1
            by_impact[c.architectural_impact.value] += 1
            total_complexity_delta += c.complexity_delta
            total_violations += len(c.policy_violations) + len(c.budget_violations)

        return {
            'total_changes': len(self._changes),
            'by_type': dict(by_type),
            'by_impact': dict(by_impact),
            'total_complexity_delta': round(total_complexity_delta, 2),
            'total_violations': total_violations,
            'pending_approval': len([c for c in self._changes if c.requires_approval and not c.approved]),
        }
