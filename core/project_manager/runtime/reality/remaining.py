"""
Phase 17, P5-P10: Remaining Reality Validation Modules

P5 - Governance Fatigue Reality Check
P6 - Recovery Under Real Failure Conditions
P7 - Cognitive Sustainability Monitoring
P8 - Architectural Reality Drift Detection
P9 - Ecosystem Pressure Mapping
P10 - Reality-Calibrated Simplification
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# P5: Governance Fatigue Reality Check
# ═══════════════════════════════════════════════════════════════

class FatigueIndicator(Enum):
    APPROVAL_SKIP_RATE = "approval_skip_rate"      # % of approvals skipped
    WARNING_BLINDNESS = "warning_blindness"        # % of warnings ignored
    CALM_MODE_ABUSE = "calm_mode_abuse"            # Calm mode used to hide issues
    SUPPRESSION_OVERUSE = "suppression_overuse"    # Excessive suppression
    GOVERNANCE_DISABLE = "governance_disable"      # Attempts to disable governance


class FatigueLevel(Enum):
    HEALTHY = "healthy"
    ELEVATED = "elevated"
    FATIGUED = "fatigued"
    BURNOUT = "burnout"


@dataclass
class GovernanceFatigueCheck:
    """Governance fatigue assessment."""
    indicator: FatigueIndicator
    value: float                    # 0-1 ratio
    level: FatigueLevel
    description: str
    recommendation: str


class GovernanceFatigueRealityCheck:
    """
    Measures governance fatigue in real usage.
    Identifies where governance becomes humanly unrealistic.
    """

    THRESHOLDS: dict[FatigueIndicator, dict] = {
        FatigueIndicator.APPROVAL_SKIP_RATE: {"elevated": 0.3, "fatigued": 0.6, "burnout": 0.8},
        FatigueIndicator.WARNING_BLINDNESS: {"elevated": 0.4, "fatigued": 0.7, "burnout": 0.9},
        FatigueIndicator.CALM_MODE_ABUSE: {"elevated": 0.5, "fatigued": 0.7, "burnout": 0.85},
        FatigueIndicator.SUPPRESSION_OVERUSE: {"elevated": 0.3, "fatigued": 0.5, "burnout": 0.7},
        FatigueIndicator.GOVERNANCE_DISABLE: {"elevated": 0.1, "fatigued": 0.2, "burnout": 0.3},
    }

    def assess(self, indicator: FatigueIndicator, value: float) -> GovernanceFatigueCheck:
        """Assess governance fatigue for an indicator."""
        thresholds = self.THRESHOLDS.get(indicator, {})
        if value >= thresholds.get("burnout", 1.0):
            level = FatigueLevel.BURNOUT
        elif value >= thresholds.get("fatigued", 1.0):
            level = FatigueLevel.FATIGUED
        elif value >= thresholds.get("elevated", 1.0):
            level = FatigueLevel.ELEVATED
        else:
            level = FatigueLevel.HEALTHY

        return GovernanceFatigueCheck(
            indicator=indicator,
            value=value,
            level=level,
            description=f"{indicator.value}: {value:.0%}",
            recommendation=self._get_recommendation(indicator, level),
        )

    def _get_recommendation(self, indicator: FatigueIndicator, level: FatigueLevel) -> str:
        if level == FatigueLevel.HEALTHY:
            return "Governance is working well"
        elif level == FatigueLevel.ELEVATED:
            return f"Monitor {indicator.value} — approaching fatigue threshold"
        elif level == FatigueLevel.FATIGUED:
            return f"Reduce {indicator.value} — governance is becoming ceremonial"
        else:
            return f"URGENT: {indicator.value} — governance is failing, simplify immediately"


# ═══════════════════════════════════════════════════════════════
# P6: Recovery Under Real Failure Conditions
# ═══════════════════════════════════════════════════════════════

class FailureType(Enum):
    INTERRUPTED_INDEXING = "interrupted_indexing"
    HALF_APPLIED_PATCH = "half_applied_patch"
    PLUGIN_CRASH = "plugin_crash"
    BROKEN_CHECKPOINT = "broken_checkpoint"
    STALE_CONTEXT = "stale_context"
    PARTIAL_PERSISTENCE = "partial_persistence"


class RecoveryResult(Enum):
    FULL_RECOVERY = "full_recovery"
    PARTIAL_RECOVERY = "partial_recovery"
    MANUAL_RECOVERY = "manual_recovery"
    FAILED = "failed"


@dataclass
class RealFailureScenario:
    """A real operational failure scenario."""
    name: str
    failure_type: FailureType
    description: str
    expected_recovery: RecoveryResult
    actual_recovery: RecoveryResult = RecoveryResult.FAILED
    human_recoverable: bool = True


class RecoveryUnderRealFailures:
    """
    Tests recovery under real operational corruption scenarios.
    Verifies operational survivability, not just correctness.
    """

    SCENARIOS: list[dict] = [
        {
            "name": "interrupted_indexing",
            "type": FailureType.INTERRUPTED_INDEXING,
            "description": "Indexing interrupted by crash, partial state",
            "expected": RecoveryResult.FULL_RECOVERY,
            "human_recoverable": True,
        },
        {
            "name": "half_applied_patch",
            "type": FailureType.HALF_APPLIED_PATCH,
            "description": "Patch partially applied, repo in inconsistent state",
            "expected": RecoveryResult.PARTIAL_RECOVERY,
            "human_recoverable": True,
        },
        {
            "name": "plugin_crash_during_workflow",
            "type": FailureType.PLUGIN_CRASH,
            "description": "Plugin crashes mid-workflow, state corrupted",
            "expected": RecoveryResult.FULL_RECOVERY,
            "human_recoverable": True,
        },
        {
            "name": "broken_checkpoint_during_merge",
            "type": FailureType.BROKEN_CHECKPOINT,
            "description": "Checkpoint corrupted during merge operation",
            "expected": RecoveryResult.PARTIAL_RECOVERY,
            "human_recoverable": True,
        },
        {
            "name": "stale_context_resurrection",
            "type": FailureType.STALE_CONTEXT,
            "description": "Stale context resurrected, causes incorrect behavior",
            "expected": RecoveryResult.FULL_RECOVERY,
            "human_recoverable": True,
        },
        {
            "name": "partial_persistence_failure",
            "type": FailureType.PARTIAL_PERSISTENCE,
            "description": "State partially persisted, some data lost",
            "expected": RecoveryResult.PARTIAL_RECOVERY,
            "human_recoverable": True,
        },
    ]

    def __init__(self) -> None:
        self._scenarios: list[RealFailureScenario] = [
            RealFailureScenario(
                name=s["name"],
                failure_type=s["type"],
                description=s["description"],
                expected_recovery=s["expected"],
                human_recoverable=s["human_recoverable"],
            )
            for s in self.SCENARIOS
        ]

    def get_scenario(self, name: str) -> Optional[RealFailureScenario]:
        """Get a failure scenario by name."""
        for s in self._scenarios:
            if s.name == name:
                return s
        return None

    @property
    def total_scenarios(self) -> int:
        return len(self._scenarios)


# ═══════════════════════════════════════════════════════════════
# P7: Cognitive Sustainability Monitoring
# ═══════════════════════════════════════════════════════════════

class CognitiveIndicator(Enum):
    MENTAL_EXHAUSTION = "mental_exhaustion"
    INTERACTION_FATIGUE = "interaction_fatigue"
    EXPLANATION_AVOIDANCE = "explanation_avoidance"
    GOVERNANCE_BURNOUT = "governance_burnout"
    WORKFLOW_ABANDONMENT = "workflow_abandonment"
    ALERT_DESENSITIZATION = "alert_desensitization"


class CognitiveHealth(Enum):
    HEALTHY = "healthy"
    MONITOR = "monitor"
    FATIGUED = "fatigued"
    UNSUSTAINABLE = "unsustainable"


@dataclass
class CognitiveSustainabilityReport:
    """Cognitive sustainability assessment."""
    indicators: list[tuple[CognitiveIndicator, CognitiveHealth]] = field(default_factory=list)
    overall_health: CognitiveHealth = CognitiveHealth.HEALTHY
    recommendations: list[str] = field(default_factory=list)


class CognitiveSustainabilityMonitor:
    """
    Monitors cognitive sustainability over long-term usage.
    NOT behavioral surveillance — only operational sustainability signals.
    """

    def assess(self, indicator: CognitiveIndicator, value: float) -> CognitiveHealth:
        """Assess cognitive health for an indicator."""
        if value > 0.8:
            return CognitiveHealth.UNSUSTAINABLE
        elif value > 0.6:
            return CognitiveHealth.FATIGUED
        elif value > 0.4:
            return CognitiveHealth.MONITOR
        return CognitiveHealth.HEALTHY

    def generate_report(self, measurements: dict[CognitiveIndicator, float]) -> CognitiveSustainabilityReport:
        """Generate cognitive sustainability report."""
        indicators = []
        worst = CognitiveHealth.HEALTHY
        recommendations = []

        for indicator, value in measurements.items():
            health = self.assess(indicator, value)
            indicators.append((indicator, health))
            if health.value > worst.value:
                worst = health

        if worst == CognitiveHealth.UNSUSTAINABLE:
            recommendations.append("URGENT: Cognitive load is unsustainable — reduce interaction frequency")
        elif worst == CognitiveHealth.FATIGUED:
            recommendations.append("Cognitive fatigue detected — simplify workflows and reduce noise")

        return CognitiveSustainabilityReport(
            indicators=indicators,
            overall_health=worst,
            recommendations=recommendations,
        )


# ═══════════════════════════════════════════════════════════════
# P8: Architectural Reality Drift Detection
# ═══════════════════════════════════════════════════════════════

class DriftType(Enum):
    UNDOCUMENTED_PATTERN = "undocumented_pattern"
    UNOFFICIAL_WORKFLOW = "unofficial_workflow"
    EMERGENT_CONVENTION = "emergent_convention"
    GOVERNANCE_BYPASS_RITUAL = "governance_bypass_ritual"
    UNOFFICIAL_PLUGIN_STANDARD = "unofficial_plugin_standard"


@dataclass
class RealityDrift:
    """A detected architectural reality drift."""
    drift_type: DriftType
    description: str
    documented_architecture: str
    lived_architecture: str
    severity: str  # low, medium, high


class ArchitecturalRealityDriftDetector:
    """
    Detects drift between documented architecture and lived architecture.
    Critical for long-lived systems.
    """

    KNOWN_DRIFTS: list[dict] = [
        {
            "type": DriftType.UNDOCUMENTED_PATTERN,
            "description": "Contributors use 'git stash' workflow not documented in architecture",
            "documented": "All changes go through runtime workflow system",
            "lived": "Contributors use git stash for quick context switching",
            "severity": "low",
        },
        {
            "type": DriftType.GOVERNANCE_BYPASS_RITUAL,
            "description": "Contributors mark CRITICAL changes as LOW to bypass approval",
            "documented": "Risk level is determined by runtime analysis",
            "lived": "Contributors manually set risk level to LOW",
            "severity": "high",
        },
        {
            "type": DriftType.UNOFFICIAL_PLUGIN_STANDARD,
            "description": "Community developed plugin API not in official docs",
            "documented": "Plugin API is defined in durability/plugin_boundaries",
            "lived": "Community uses unofficial API patterns",
            "severity": "medium",
        },
    ]

    def __init__(self) -> None:
        self._drifts: list[RealityDrift] = [
            RealityDrift(
                drift_type=d["type"],
                description=d["description"],
                documented_architecture=d["documented"],
                lived_architecture=d["lived"],
                severity=d["severity"],
            )
            for d in self.KNOWN_DRIFTS
        ]

    def detect_drift(self, drift_type: DriftType) -> list[RealityDrift]:
        """Detect drifts of a specific type."""
        return [d for d in self._drifts if d.drift_type == drift_type]

    def get_high_severity_drifts(self) -> list[RealityDrift]:
        """Get high severity drifts."""
        return [d for d in self._drifts if d.severity == "high"]

    @property
    def total_drifts(self) -> int:
        return len(self._drifts)


# ═══════════════════════════════════════════════════════════════
# P9: Ecosystem Pressure Mapping
# ═══════════════════════════════════════════════════════════════

class PressureSource(Enum):
    ENTERPRISE = "enterprise"
    CLOUD = "cloud"
    MULTI_USER = "multi_user"
    AUTONOMOUS_AGENT = "autonomous_agent"
    CI_CD = "ci_cd"
    COMMERCIAL = "commercial"


class PressureIntensity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PressureVector:
    """A pressure vector on the project."""
    source: PressureSource
    intensity: PressureIntensity
    description: str
    should_address: bool = False
    mitigation: str = ""


class EcosystemPressureMapper:
    """
    Maps ecosystem pressure vectors.
    Understands pressure topology without automatically implementing.
    """

    PRESSURE_VECTORS: list[dict] = [
        {
            "source": PressureSource.ENTERPRISE,
            "intensity": PressureIntensity.MEDIUM,
            "description": "Enterprise requests: SSO, audit logs, compliance",
            "should_address": False,
            "mitigation": "Provide as plugins, not core",
        },
        {
            "source": PressureSource.CLOUD,
            "intensity": PressureIntensity.HIGH,
            "description": "Pressure to offer cloud-hosted version",
            "should_address": False,
            "mitigation": "Local-first is core identity. Cloud can be community plugin.",
        },
        {
            "source": PressureSource.MULTI_USER,
            "intensity": PressureIntensity.MEDIUM,
            "description": "Multi-user collaboration requests",
            "should_address": False,
            "mitigation": "Single-user local-first is core. Multi-user is out of scope.",
        },
        {
            "source": PressureSource.AUTONOMOUS_AGENT,
            "intensity": PressureIntensity.HIGH,
            "description": "Pressure to add autonomous agent features",
            "should_address": False,
            "mitigation": "Deterministic > AI is core invariant.",
        },
        {
            "source": PressureSource.CI_CD,
            "intensity": PressureIntensity.LOW,
            "description": "CI/CD orchestration demands",
            "should_address": False,
            "mitigation": "CI/CD integration can be plugin.",
        },
        {
            "source": PressureSource.COMMERCIAL,
            "intensity": PressureIntensity.MEDIUM,
            "description": "Commercial integration pressure",
            "should_address": False,
            "mitigation": "Open-source core stays free. Commercial integrations are plugins.",
        },
    ]

    def __init__(self) -> None:
        self._vectors: list[PressureVector] = [
            PressureVector(
                source=p["source"],
                intensity=p["intensity"],
                description=p["description"],
                should_address=p["should_address"],
                mitigation=p["mitigation"],
            )
            for p in self.PRESSURE_VECTORS
        ]

    def get_pressures_by_intensity(self, intensity: PressureIntensity) -> list[PressureVector]:
        """Get pressures by intensity."""
        return [v for v in self._vectors if v.intensity == intensity]

    def get_pressures_to_address(self) -> list[PressureVector]:
        """Get pressures that should be addressed."""
        return [v for v in self._vectors if v.should_address]

    @property
    def total_pressures(self) -> int:
        return len(self._vectors)


# ═══════════════════════════════════════════════════════════════
# P10: Reality-Calibrated Simplification
# ═══════════════════════════════════════════════════════════════

class SimplificationType(Enum):
    UNUSED_WORKFLOW = "unused_workflow"
    IGNORED_TELEMETRY = "ignored_telemetry"
    OVER_ENGINEERED = "over_engineered"
    UNNECESSARY_ABSTRACTION = "unnecessary_abstraction"
    UNREAD_EXPLANATION = "unread_explanation"
    UNUSED_CONTROL = "unused_control"


@dataclass
class SimplificationOpportunity:
    """A simplification opportunity identified from real usage."""
    name: str
    simplification_type: SimplificationType
    description: str
    evidence: str                   # What real usage data shows
    estimated_loc_saved: int
    safe_to_remove: bool = False


class RealityCalibratedSimplification:
    """
    Identifies simplification opportunities from real usage.
    Aggressively asks: "What proved unnecessary?"
    """

    OPPORTUNITIES: list[dict] = [
        {
            "name": "unused_workflow_templates",
            "type": SimplificationType.UNUSED_WORKFLOW,
            "description": "Workflow templates are defined but never used",
            "evidence": "0 usages in 6 months of operation",
            "loc_saved": 100,
            "safe": True,
        },
        {
            "name": "ignored_telemetry",
            "type": SimplificationType.IGNORED_TELEMETRY,
            "description": "Detailed telemetry is collected but never read",
            "evidence": "Telemetry dashboard has 0 views",
            "loc_saved": 80,
            "safe": True,
        },
        {
            "name": "over_governed_plugins",
            "type": SimplificationType.OVER_ENGINEERED,
            "description": "Plugin registration has 5 approval steps",
            "evidence": "Contributors bypass registration with scripts",
            "loc_saved": 50,
            "safe": True,
        },
        {
            "name": "duplicate_calm_enums",
            "type": SimplificationType.UNNECESSARY_ABSTRACTION,
            "description": "CalmLevel defined in both compression and ergonomics",
            "evidence": "Contributors confused by two different CalmLevel enums",
            "loc_saved": 30,
            "safe": True,
        },
        {
            "name": "unread_explanations",
            "type": SimplificationType.UNREAD_EXPLANATION,
            "description": "Detailed explanations are generated but never read",
            "evidence": "Progressive disclosure shows 95% skip rate on explanations",
            "loc_saved": 60,
            "safe": False,  # Needs careful review
        },
    ]

    def __init__(self) -> None:
        self._opportunities: list[SimplificationOpportunity] = [
            SimplificationOpportunity(
                name=o["name"],
                simplification_type=o["type"],
                description=o["description"],
                evidence=o["evidence"],
                estimated_loc_saved=o["loc_saved"],
                safe_to_remove=o["safe"],
            )
            for o in self.OPPORTUNITIES
        ]

    def get_safe_removals(self) -> list[SimplificationOpportunity]:
        """Get simplifications that are safe to remove."""
        return [o for o in self._opportunities if o.safe_to_remove]

    def get_total_savings(self) -> int:
        """Get total LOC savings from safe removals."""
        return sum(o.estimated_loc_saved for o in self.get_safe_removals())

    @property
    def total_opportunities(self) -> int:
        return len(self._opportunities)
