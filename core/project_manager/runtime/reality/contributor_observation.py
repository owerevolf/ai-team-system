"""
Phase 17, P3: Contributor Reality Observation

Observes how real contributors actually use the system:
- How they learn
- Where they get confused
- What they bypass
- What they misunderstand
- What they ignore

Principle: Observe reality, don't defend design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ObservationType(Enum):
    LEARNING_PATTERN = "learning_pattern"      # How contributors learn
    CONFUSION_POINT = "confusion_point"        # Where they get confused
    GOVERNANCE_BYPASS = "governance_bypass"    # What they bypass
    MISUNDERSTANDING = "misunderstanding"      # What they misunderstand
    IGNORED_FEATURE = "ignored_feature"        # What they ignore
    WORKAROUND = "workaround"                  # What workarounds they create


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Observation:
    """A single contributor observation."""
    observation_type: ObservationType
    severity: Severity
    description: str
    context: str                    # When/where this was observed
    impact: str                     # What impact this has
    recommendation: str = ""


@dataclass
class ObservationReport:
    """Full contributor observation report."""
    observations: list[Observation] = field(default_factory=list)

    @property
    def critical_observations(self) -> list[Observation]:
        return [o for o in self.observations if o.severity == Severity.CRITICAL]

    @property
    def high_observations(self) -> list[Observation]:
        return [o for o in self.observations if o.severity == Severity.HIGH]

    @property
    def by_type(self) -> dict[str, list[Observation]]:
        result: dict[str, list[Observation]] = {}
        for o in self.observations:
            result.setdefault(o.observation_type.value, []).append(o)
        return result


class ContributorRealityObserver:
    """
    Records and analyzes real contributor behavior.
    Identifies gaps between design assumptions and reality.
    """

    # Known observations from Phase 17 analysis
    KNOWN_OBSERVATIONS: list[dict] = [
        {
            "type": ObservationType.CONFUSION_POINT,
            "severity": Severity.HIGH,
            "description": "Contributors confuse CalmLevel (ergonomics) with CalmLevel (compression)",
            "context": "Two different enums with same name but different values",
            "impact": "Contributors set wrong calm mode, get unexpected behavior",
            "recommendation": "Unify under single CalmLevel enum",
        },
        {
            "type": ObservationType.GOVERNANCE_BYPASS,
            "severity": Severity.MEDIUM,
            "description": "Contributors auto-approve LOW risk changes without reading",
            "context": "LOW risk confirmation dialog is too frequent",
            "impact": "Governance becomes ceremonial, not protective",
            "recommendation": "Auto-apply LOW risk with audit trail, remove confirmation",
        },
        {
            "type": ObservationType.IGNORED_FEATURE,
            "severity": Severity.MEDIUM,
            "description": "Progressive disclosure is ignored — contributors always expand to FULL",
            "context": "MINIMAL default is too sparse, contributors don't trust it",
            "impact": "Defeats the purpose of progressive disclosure",
            "recommendation": "Make MINIMAL more informative, or default to SUMMARY",
        },
        {
            "type": ObservationType.MISUNDERSTANDING,
            "severity": Severity.HIGH,
            "description": "Contributors think 'do less' means 'runtime is broken'",
            "context": "Runtime suppresses actions, contributors think it's a bug",
            "impact": "Loss of trust in runtime",
            "recommendation": "Add clear indication when do_less suppresses an action",
        },
        {
            "type": ObservationType.WORKAROUND,
            "severity": Severity.MEDIUM,
            "description": "Contributors create scripts to bypass plugin registration",
            "context": "Plugin registration requires 5 approval steps",
            "impact": "Unofficial plugins without governance",
            "recommendation": "Simplify plugin registration to single step with post-hoc review",
        },
        {
            "type": ObservationType.LEARNING_PATTERN,
            "severity": Severity.LOW,
            "description": "Contributors learn by reading tests, not docs",
            "context": "Tests are more up-to-date and concrete than documentation",
            "impact": "Tests become de facto documentation",
            "recommendation": "Make tests more readable, add docstrings to test cases",
        },
    ]

    def __init__(self) -> None:
        self._observations: list[Observation] = []
        self._register_known()

    def _register_known(self) -> None:
        """Register known observations."""
        for data in self.KNOWN_OBSERVATIONS:
            self._observations.append(Observation(
                observation_type=data["type"],
                severity=data["severity"],
                description=data["description"],
                context=data["context"],
                impact=data["impact"],
                recommendation=data.get("recommendation", ""),
            ))

    def record_observation(self, observation: Observation) -> None:
        """Record a new observation."""
        self._observations.append(observation)

    def generate_report(self) -> ObservationReport:
        """Generate observation report."""
        return ObservationReport(observations=list(self._observations))

    def get_observations_by_type(self, obs_type: ObservationType) -> list[Observation]:
        """Get observations of a specific type."""
        return [o for o in self._observations if o.observation_type == obs_type]

    def get_critical_issues(self) -> list[Observation]:
        """Get critical observations that need immediate attention."""
        return [o for o in self._observations if o.severity in (Severity.CRITICAL, Severity.HIGH)]

    @property
    def total_observations(self) -> int:
        return len(self._observations)
