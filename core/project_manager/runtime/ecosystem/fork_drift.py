"""
Phase 15, P4: Fork Drift Analysis

Detects semantic and governance divergence in forks.
Not anti-fork — but provides visibility into ecosystem divergence.

Principle: Visibility into divergence > centralized control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DriftDimension(Enum):
    SEMANTIC = "semantic"          # Concepts mean different things
    GOVERNANCE = "governance"      # Different approval/contract rules
    RUNTIME = "runtime"            # Different execution behavior
    ARCHITECTURAL = "architectural"  # Different module boundaries


class DriftLevel(Enum):
    NONE = "none"                  # No significant drift
    MINOR = "minor"                # Cosmetic differences
    MODERATE = "moderate"          # Notable divergence
    MAJOR = "major"                # Significant incompatibility
    INCOMPATIBLE = "incompatible"  # Cannot interoperate


@dataclass
class ForkDriftReport:
    """Report of drift between main and a fork."""
    fork_name: str
    drift_dimensions: dict[DriftDimension, DriftLevel] = field(default_factory=dict)
    incompatible_concepts: list[str] = field(default_factory=list)
    missing_concepts: list[str] = field(default_factory=list)
    added_concepts: list[str] = field(default_factory=list)
    governance_divergence: list[str] = field(default_factory=list)

    @property
    def overall_drift(self) -> DriftLevel:
        levels = list(self.drift_dimensions.values())
        if not levels:
            return DriftLevel.NONE
        severity = {
            DriftLevel.NONE: 0, DriftLevel.MINOR: 1,
            DriftLevel.MODERATE: 2, DriftLevel.MAJOR: 3, DriftLevel.INCOMPATIBLE: 4,
        }
        max_level = max(levels, key=lambda l: severity.get(l, 0))
        return max_level


class ForkDriftAnalyzer:
    """
    Analyzes drift between main runtime and forks.
    Provides visibility without enforcing control.
    """

    # Core concepts that should not be redefined by forks
    CORE_CONCEPTS: set[str] = {
        "CanonicalPriority", "CanonicalStateTier", "CanonicalEventType",
        "CanonicalApprovalRisk", "CanonicalApprovalStatus",
        "CanonicalExplanationLevel", "CanonicalVisibility",
        "StateTier", "RecoveryStep", "TransparencyContract",
    }

    # Governance rules that should not be weakened
    CORE_GOVERNANCE: set[str] = {
        "safety_over_autonomy",
        "deterministic_over_ai",
        "mandatory_approval_critical",
        "audit_trail_required",
        "recovery_deterministic",
    }

    def __init__(self) -> None:
        self._forks: dict[str, ForkDriftReport] = {}

    def register_fork(self, fork_name: str) -> ForkDriftReport:
        """Register a fork for drift tracking."""
        report = ForkDriftReport(fork_name=fork_name)
        self._forks[fork_name] = report
        return report

    def analyze_fork(self, fork_name: str) -> ForkDriftReport:
        """Analyze drift for a registered fork."""
        report = self._forks.get(fork_name)
        if not report:
            report = self.register_fork(fork_name)

        # In a real system, this would scan the fork's codebase
        # For now, provide the framework for drift detection
        return report

    def check_concept_compatibility(self, concept: str, fork_name: str) -> tuple[bool, str]:
        """Check if a concept is compatible with main."""
        if concept in self.CORE_CONCEPTS:
            return True, f"'{concept}' is a core concept — should not be redefined"
        return True, f"'{concept}' is safe to modify"

    def check_governance_compatibility(self, rule: str, fork_name: str) -> tuple[bool, str]:
        """Check if a governance rule is compatible with main."""
        if rule in self.CORE_GOVERNANCE:
            return False, f"'{rule}' is a core governance rule — should not be weakened"
        return True, f"'{rule}' is safe to modify"

    def get_incompatible_forks(self) -> list[ForkDriftReport]:
        """Get forks with major or incompatible drift."""
        return [
            r for r in self._forks.values()
            if r.overall_drift in (DriftLevel.MAJOR, DriftLevel.INCOMPATIBLE)
        ]

    @property
    def total_forks_tracked(self) -> int:
        return len(self._forks)
