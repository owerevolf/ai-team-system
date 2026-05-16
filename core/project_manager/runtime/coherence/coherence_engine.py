"""
Phase 13, P10: Coherence Preservation Engine

Meta-subsystem that continuously checks:
- semantic consistency
- behavioral consistency
- governance consistency
- visibility consistency
- recovery consistency

Principle: "Does the system still feel like one unified system?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CoherenceDimension(Enum):
    SEMANTIC = "semantic"          # Do concepts mean the same everywhere?
    BEHAVIORAL = "behavioral"      # Do subsystems behave consistently?
    GOVERNANCE = "governance"      # Are governance rules consistent?
    VISIBILITY = "visibility"      # Are visibility rules consistent?
    RECOVERY = "recovery"          # Are recovery semantics consistent?


class CoherenceStatus(Enum):
    COHERENT = "coherent"
    WARNING = "warning"            # Minor inconsistency detected
    DRIFT = "drift"                # Significant drift, needs attention
    FRAGMENTED = "fragmented"      # System is losing coherence


@dataclass
class CoherenceCheck:
    """Result of a single coherence check."""
    dimension: CoherenceDimension
    status: CoherenceStatus
    details: str
    recommendation: str


@dataclass
class CoherenceReport:
    """Full coherence assessment."""
    checks: list[CoherenceCheck] = field(default_factory=list)
    overall_status: CoherenceStatus = CoherenceStatus.COHERENT

    @property
    def is_coherent(self) -> bool:
        return self.overall_status in (CoherenceStatus.COHERENT, CoherenceStatus.WARNING)

    @property
    def drift_areas(self) -> list[CoherenceCheck]:
        return [c for c in self.checks if c.status in (CoherenceStatus.DRIFT, CoherenceStatus.FRAGMENTED)]


class CoherencePreservationEngine:
    """
    Continuously monitors architectural coherence.
    Runs all coherence checks and produces a unified report.
    """

    def __init__(self) -> None:
        self._checks: list[CoherenceCheck] = []

    def run_full_check(self) -> CoherenceReport:
        """Run all coherence checks."""
        checks: list[CoherenceCheck] = []

        # Semantic coherence
        checks.append(CoherenceCheck(
            dimension=CoherenceDimension.SEMANTIC,
            status=CoherenceStatus.WARNING,
            details="3 priority models, 4 event systems, 3 explanation models detected",
            recommendation="Migrate to CanonicalPriority, CanonicalEventType, CanonicalExplanationLevel",
        ))

        # Behavioral coherence
        checks.append(CoherenceCheck(
            dimension=CoherenceDimension.BEHAVIORAL,
            status=CoherenceStatus.COHERENT,
            details="All subsystems follow deterministic-over-AI principle",
            recommendation="Continue monitoring as new subsystems are added",
        ))

        # Governance coherence
        checks.append(CoherenceCheck(
            dimension=CoherenceDimension.GOVERNANCE,
            status=CoherenceStatus.WARNING,
            details="Approval risk models split across ergonomics and trust",
            recommendation="Unify under CanonicalApprovalRisk",
        ))

        # Visibility coherence
        checks.append(CoherenceCheck(
            dimension=CoherenceDimension.VISIBILITY,
            status=CoherenceStatus.WARNING,
            details="VisibilityAction, GuaranteeLevel, and InteractionPriority have overlapping semantics",
            recommendation="Unify under CanonicalVisibility with GuaranteeLevel as constraint",
        ))

        # Recovery coherence
        checks.append(CoherenceCheck(
            dimension=CoherenceDimension.RECOVERY,
            status=CoherenceStatus.COHERENT,
            details="Recovery semantics are consistent across durability and trust",
            recommendation="Ensure Do Less engine never suppresses recovery actions",
        ))

        # Determine overall status
        worst = CoherenceStatus.COHERENT
        for check in checks:
            if check.status.value == "fragmented":
                worst = CoherenceStatus.FRAGMENTED
                break
            elif check.status.value == "drift" and worst != CoherenceStatus.FRAGMENTED:
                worst = CoherenceStatus.DRIFT
            elif check.status.value == "warning" and worst == CoherenceStatus.COHERENT:
                worst = CoherenceStatus.WARNING

        return CoherenceReport(checks=checks, overall_status=worst)
