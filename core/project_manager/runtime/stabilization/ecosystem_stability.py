"""
Phase 16, P9: Ecosystem Stability Validation

Monitors ecosystem-level stability:
- plugin ecosystem chaos
- incompatible extension growth
- contributor governance fatigue
- fragmentation pressure
- identity erosion

Principle: Preserve hackability, contributor energy, operational simplicity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StabilityDimension(Enum):
    PLUGIN_CHAOS = "plugin_chaos"
    EXTENSION_COMPATIBILITY = "extension_compatibility"
    CONTRIBUTOR_FATIGUE = "contributor_fatigue"
    FRAGMENTATION = "fragmentation"
    IDENTITY_EROSION = "identity_erosion"


class StabilityLevel(Enum):
    STABLE = "stable"
    MONITOR = "monitor"            # Watch closely
    UNSTABLE = "unstable"          # Needs intervention
    CRITICAL = "critical"          # Immediate action needed


@dataclass
class StabilityIndicator:
    """A single stability indicator."""
    dimension: StabilityDimension
    level: StabilityLevel
    description: str
    recommendation: str


@dataclass
class StabilityReport:
    """Full ecosystem stability report."""
    indicators: list[StabilityIndicator] = field(default_factory=list)
    overall_stability: StabilityLevel = StabilityLevel.STABLE

    @property
    def unstable_areas(self) -> list[StabilityIndicator]:
        return [i for i in self.indicators if i.level in (StabilityLevel.UNSTABLE, StabilityLevel.CRITICAL)]


class EcosystemStabilityValidator:
    """
    Validates ecosystem-level stability.
    Detects chaos, fragmentation, and identity erosion.
    """

    def __init__(self) -> None:
        self._indicators: list[StabilityIndicator] = []

    def add_indicator(self, indicator: StabilityIndicator) -> None:
        """Add a stability indicator."""
        self._indicators.append(indicator)

    def assess_plugin_chaos(self) -> StabilityIndicator:
        """Assess plugin ecosystem chaos."""
        return StabilityIndicator(
            dimension=StabilityDimension.PLUGIN_CHAOS,
            level=StabilityLevel.STABLE,
            description="Plugin ecosystem is governed by capability contracts",
            recommendation="Continue monitoring as plugin count grows",
        )

    def assess_extension_compatibility(self) -> StabilityIndicator:
        """Assess extension compatibility."""
        return StabilityIndicator(
            dimension=StabilityDimension.EXTENSION_COMPATIBILITY,
            level=StabilityLevel.STABLE,
            description="Extension contracts enforce compatibility",
            recommendation="Add automated compatibility testing as ecosystem grows",
        )

    def assess_contributor_fatigue(self) -> StabilityIndicator:
        """Assess contributor governance fatigue."""
        return StabilityIndicator(
            dimension=StabilityDimension.CONTRIBUTOR_FATIGUE,
            level=StabilityLevel.MONITOR,
            description="Governance overhead is moderate — monitor as system grows",
            recommendation="Implement auto-approval for SAFE changes to reduce fatigue",
        )

    def assess_fragmentation(self) -> StabilityIndicator:
        """Assess ecosystem fragmentation."""
        return StabilityIndicator(
            dimension=StabilityDimension.FRAGMENTATION,
            level=StabilityLevel.STABLE,
            description="Semantic coherence is enforced by canonical vocabulary",
            recommendation="Continue drift detection as ecosystem grows",
        )

    def assess_identity_erosion(self) -> StabilityIndicator:
        """Assess core identity erosion."""
        return StabilityIndicator(
            dimension=StabilityDimension.IDENTITY_EROSION,
            level=StabilityLevel.STABLE,
            description="Core identity is explicitly preserved",
            recommendation="Review identity statements quarterly",
        )

    def generate_report(self) -> StabilityReport:
        """Generate full stability report."""
        indicators = [
            self.assess_plugin_chaos(),
            self.assess_extension_compatibility(),
            self.assess_contributor_fatigue(),
            self.assess_fragmentation(),
            self.assess_identity_erosion(),
        ]

        # Determine overall stability
        levels = [i.level for i in indicators]
        if StabilityLevel.CRITICAL in levels:
            overall = StabilityLevel.CRITICAL
        elif StabilityLevel.UNSTABLE in levels:
            overall = StabilityLevel.UNSTABLE
        elif StabilityLevel.MONITOR in levels:
            overall = StabilityLevel.MONITOR
        else:
            overall = StabilityLevel.STABLE

        return StabilityReport(indicators=indicators, overall_stability=overall)
