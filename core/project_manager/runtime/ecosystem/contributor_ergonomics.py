"""
Phase 15, P9: Contributor Ergonomics

Optimizes the contribution experience:
- contribution path length
- review friction
- testing burden
- architectural navigation
- governance overhead

Principle: Contribution should feel like engineering, not bureaucracy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FrictionType(Enum):
    CONTRIBUTION_PATH = "contribution_path"    # Steps to make a contribution
    REVIEW_FRICTION = "review_friction"        # Review turnaround time
    TESTING_BURDEN = "testing_burden"          # Tests required for a change
    NAVIGATION = "navigation"                  # Finding relevant code/docs
    GOVERNANCE_OVERHEAD = "governance_overhead"  # Approvals needed


class FrictionLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXHAUSTING = "exhausting"


@dataclass
class FrictionPoint:
    """A specific friction point in the contribution process."""
    friction_type: FrictionType
    level: FrictionLevel
    description: str
    current_value: str          # Current state
    target_value: str           # Target state
    recommendation: str


@dataclass
class ErgonomicsReport:
    """Contributor ergonomics assessment."""
    friction_points: list[FrictionPoint] = field(default_factory=list)
    overall_score: float = 0.0  # 0-100, higher is better

    @property
    def high_friction_areas(self) -> list[FrictionPoint]:
        return [f for f in self.friction_points if f.level in (FrictionLevel.HIGH, FrictionLevel.EXHAUSTING)]


class ContributorErgonomics:
    """
    Assesses and optimizes contributor ergonomics.
    Identifies friction points and suggests improvements.
    """

    def __init__(self) -> None:
        self._friction_points: list[FrictionPoint] = []

    def add_friction_point(self, point: FrictionPoint) -> None:
        """Add a friction point."""
        self._friction_points.append(point)

    def assess_contribution_path(self) -> FrictionPoint:
        """Assess the contribution path length."""
        return FrictionPoint(
            friction_type=FrictionType.CONTRIBUTION_PATH,
            level=FrictionLevel.MODERATE,
            description="Steps required to make a contribution",
            current_value="fork → branch → code → test → PR → review → merge",
            target_value="fork → branch → code → auto-test → PR → auto-review → merge",
            recommendation="Automate testing and add auto-review for low-risk changes",
        )

    def assess_review_friction(self) -> FrictionPoint:
        """Assess review friction."""
        return FrictionPoint(
            friction_type=FrictionType.REVIEW_FRICTION,
            level=FrictionLevel.MODERATE,
            description="Time from PR to review",
            current_value="Depends on maintainer availability",
            target_value="< 24 hours for low-risk changes",
            recommendation="Add auto-approval for SAFE changes (dead code removal, tests)",
        )

    def assess_governance_overhead(self) -> FrictionPoint:
        """Assess governance overhead."""
        return FrictionPoint(
            friction_type=FrictionType.GOVERNANCE_OVERHEAD,
            level=FrictionLevel.HIGH,
            description="Approvals needed for different change types",
            current_value="All changes require architect approval",
            target_value="SAFE changes auto-approved, REVIEW changes need 1 approver",
            recommendation="Implement risk-based approval from evolution_safety rules",
        )

    def generate_report(self) -> ErgonomicsReport:
        """Generate full ergonomics report."""
        points = [
            self.assess_contribution_path(),
            self.assess_review_friction(),
            self.assess_governance_overhead(),
        ]
        points.extend(self._friction_points)

        # Calculate overall score
        level_scores = {
            FrictionLevel.LOW: 100,
            FrictionLevel.MODERATE: 70,
            FrictionLevel.HIGH: 40,
            FrictionLevel.EXHAUSTING: 10,
        }
        score = sum(level_scores.get(p.level, 50) for p in points) / len(points) if points else 50

        return ErgonomicsReport(friction_points=points, overall_score=score)

    def get_optimization_suggestions(self) -> list[str]:
        """Get suggestions for improving contributor ergonomics."""
        return [
            "Auto-approve SAFE changes (dead code removal, test additions, type annotations)",
            "Add PR templates that auto-classify change risk",
            "Provide quick-start guide for each subsystem",
            "Add 'good first issue' labels for low-risk contributions",
            "Create contribution path visualization",
            "Reduce governance overhead for isolated changes",
        ]
