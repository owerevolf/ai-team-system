"""
Phase 15, P6: Maintainer Load Protection

Detects and prevents maintainer burnout:
- review overload
- governance fatigue
- approval concentration
- contributor dependency hotspots

Principle: Sustainable maintainer load > feature velocity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LoadType(Enum):
    REVIEW = "review"              # Code review load
    GOVERNANCE = "governance"      # Governance decision load
    APPROVAL = "approval"          # Approval bottleneck
    SUPPORT = "support"            # Contributor support
    ARCHITECTURE = "architecture"  # Architecture decision load


class LoadLevel(Enum):
    HEALTHY = "healthy"
    ELEVATED = "elevated"
    HIGH = "high"
    BURNOUT_RISK = "burnout_risk"


@dataclass
class MaintainerLoad:
    """Load metrics for a single maintainer."""
    name: str
    loads: dict[LoadType, int] = field(default_factory=dict)  # count per type
    total_reviews: int = 0
    total_approvals: int = 0
    total_governance_decisions: int = 0
    consecutive_high_load_days: int = 0

    @property
    def overall_load(self) -> LoadLevel:
        total = sum(self.loads.values())
        if total > 50 or self.consecutive_high_load_days > 14:
            return LoadLevel.BURNOUT_RISK
        elif total > 30 or self.consecutive_high_load_days > 7:
            return LoadLevel.HIGH
        elif total > 15:
            return LoadLevel.ELEVATED
        return LoadLevel.HEALTHY


@dataclass
class LoadProtectionReport:
    """Report of maintainer load status."""
    maintainers: list[MaintainerLoad] = field(default_factory=list)
    approval_bottlenecks: list[str] = field(default_factory=list)
    review_overload: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    @property
    def at_risk_maintainers(self) -> list[MaintainerLoad]:
        return [m for m in self.maintainers if m.overall_load == LoadLevel.BURNOUT_RISK]


class MaintainerLoadProtector:
    """
    Monitors and protects maintainer load.
    Detects burnout risk and suggests load distribution.
    """

    def __init__(self) -> None:
        self._maintainers: dict[str, MaintainerLoad] = {}

    def register_maintainer(self, name: str) -> MaintainerLoad:
        """Register a maintainer for load tracking."""
        load = MaintainerLoad(name=name)
        self._maintainers[name] = load
        return load

    def record_activity(self, maintainer: str, load_type: LoadType, count: int = 1) -> None:
        """Record maintainer activity."""
        m = self._maintainers.get(maintainer)
        if m:
            m.loads[load_type] = m.loads.get(load_type, 0) + count
            if load_type == LoadType.REVIEW:
                m.total_reviews += count
            elif load_type == LoadType.APPROVAL:
                m.total_approvals += count
            elif load_type == LoadType.GOVERNANCE:
                m.total_governance_decisions += count

    def get_load(self, maintainer: str) -> Optional[MaintainerLoad]:
        """Get load for a specific maintainer."""
        return self._maintainers.get(maintainer)

    def generate_report(self) -> LoadProtectionReport:
        """Generate load protection report."""
        report = LoadProtectionReport()

        for m in self._maintainers.values():
            report.maintainers.append(m)

            if m.overall_load == LoadLevel.BURNOUT_RISK:
                report.recommendations.append(
                    f"URGENT: {m.name} is at burnout risk — redistribute load immediately"
                )
            elif m.overall_load == LoadLevel.HIGH:
                report.recommendations.append(
                    f"WARNING: {m.name} has high load — consider load distribution"
                )

            if m.total_approvals > 20:
                report.approval_bottlenecks.append(m.name)
                report.recommendations.append(
                    f"{m.name} is an approval bottleneck ({m.total_approvals} approvals)"
                )

            if m.total_reviews > 30:
                report.review_overload.append(m.name)
                report.recommendations.append(
                    f"{m.name} has review overload ({m.total_reviews} reviews)"
                )

        if not report.recommendations:
            report.recommendations.append("All maintainers within healthy load parameters")

        return report

    def suggest_load_distribution(self, overloaded_maintainer: str) -> list[str]:
        """Suggest how to distribute load from an overloaded maintainer."""
        m = self._maintainers.get(overloaded_maintainer)
        if not m:
            return []

        suggestions: list[str] = []

        # Find maintainers with low load
        low_load = [
            name for name, load in self._maintainers.items()
            if name != overloaded_maintainer and load.overall_load == LoadLevel.HEALTHY
        ]

        if low_load:
            suggestions.append(
                f"Transfer some reviews from {overloaded_maintainer} to: {', '.join(low_load[:3])}"
            )

        if m.total_approvals > 10:
            suggestions.append(
                f"Distribute approval authority — {overloaded_maintainer} has {m.total_approvals} approvals"
            )

        if m.total_governance_decisions > 5:
            suggestions.append(
                f"Share governance decisions — {overloaded_maintainer} made {m.total_governance_decisions} decisions"
            )

        suggestions.append("Consider adding a new maintainer to distribute load")

        return suggestions

    @property
    def total_maintainers(self) -> int:
        return len(self._maintainers)
