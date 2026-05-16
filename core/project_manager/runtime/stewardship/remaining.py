"""
Phase 18, P4-P10: Remaining Stewardship Modules

P4 - Runtime Weight Index
P5 - Long-Term Maintainership Model
P6 - Plugin Boundary Freezing
P7 - Conceptual Compression Pass
P8 - Ecosystem Sustainability Review
P9 - Architecture Preservation Layer
P10 - Stewardship Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# P4: Runtime Weight Index
# ═══════════════════════════════════════════════════════════════

class WeightDimension(Enum):
    CONCEPTUAL_DENSITY = "conceptual_density"
    SUBSYSTEM_COUNT = "subsystem_count"
    INTERACTION_BURDEN = "interaction_burden"
    GOVERNANCE_PRESSURE = "governance_pressure"
    ONBOARDING_DIFFICULTY = "onboarding_difficulty"
    MAINTENANCE_COST = "maintenance_cost"
    SEMANTIC_COMPLEXITY = "semantic_complexity"


class WeightStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class WeightMeasurement:
    dimension: WeightDimension
    value: float
    threshold: float
    status: WeightStatus


class RuntimeWeightIndex:
    THRESHOLDS: dict[WeightDimension, dict] = {
        WeightDimension.CONCEPTUAL_DENSITY: {"warning": 5.0, "critical": 8.0},
        WeightDimension.SUBSYSTEM_COUNT: {"warning": 8, "critical": 12},
        WeightDimension.INTERACTION_BURDEN: {"warning": 10, "critical": 20},
        WeightDimension.GOVERNANCE_PRESSURE: {"warning": 5, "critical": 10},
        WeightDimension.ONBOARDING_DIFFICULTY: {"warning": 120, "critical": 240},
        WeightDimension.MAINTENANCE_COST: {"warning": 0.5, "critical": 0.8},
        WeightDimension.SEMANTIC_COMPLEXITY: {"warning": 50, "critical": 100},
    }

    def measure(self, dimension: WeightDimension, value: float) -> WeightMeasurement:
        thresholds = self.THRESHOLDS.get(dimension, {})
        if value >= thresholds.get("critical", float("inf")):
            status = WeightStatus.CRITICAL
        elif value >= thresholds.get("warning", float("inf")):
            status = WeightStatus.WARNING
        else:
            status = WeightStatus.HEALTHY
        return WeightMeasurement(dimension=dimension, value=value, threshold=thresholds.get("warning", 0), status=status)

    def get_current_weight(self) -> dict[WeightDimension, WeightMeasurement]:
        """Get current weight measurements for the system."""
        return {
            WeightDimension.SUBSYSTEM_COUNT: self.measure(WeightDimension.SUBSYSTEM_COUNT, 8),
            WeightDimension.SEMANTIC_COMPLEXITY: self.measure(WeightDimension.SEMANTIC_COMPLEXITY, 60),
            WeightDimension.ONBOARDING_DIFFICULTY: self.measure(WeightDimension.ONBOARDING_DIFFICULTY, 120),
        }


# ═══════════════════════════════════════════════════════════════
# P5: Long-Term Maintainership Model
# ═══════════════════════════════════════════════════════════════

class MaintainershipRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MaintainershipProfile:
    """Maintainership profile for a subsystem."""
    subsystem: str
    primary: str = ""
    secondary: str = ""
    bus_factor: int = 1
    risk: MaintainershipRisk = MaintainershipRisk.HIGH
    documented: bool = False
    rotation_ready: bool = False


class LongTermMaintainershipModel:
    """
    Designs for maintainership continuity.
    Ensures project survives maintainer turnover.
    """

    PROFILES: dict[str, dict] = {
        "durability": {"bus_factor": 1, "risk": MaintainershipRisk.HIGH, "documented": True, "rotation_ready": False},
        "ergonomics": {"bus_factor": 1, "risk": MaintainershipRisk.HIGH, "documented": True, "rotation_ready": False},
        "trust": {"bus_factor": 1, "risk": MaintainershipRisk.HIGH, "documented": True, "rotation_ready": False},
        "compression": {"bus_factor": 1, "risk": MaintainershipRisk.MEDIUM, "documented": True, "rotation_ready": True},
        "coherence": {"bus_factor": 1, "risk": MaintainershipRisk.MEDIUM, "documented": True, "rotation_ready": True},
        "ecosystem": {"bus_factor": 1, "risk": MaintainershipRisk.MEDIUM, "documented": True, "rotation_ready": True},
        "stabilization": {"bus_factor": 1, "risk": MaintainershipRisk.LOW, "documented": True, "rotation_ready": True},
        "reality": {"bus_factor": 1, "risk": MaintainershipRisk.LOW, "documented": True, "rotation_ready": True},
        "stewardship": {"bus_factor": 1, "risk": MaintainershipRisk.LOW, "documented": True, "rotation_ready": True},
    }

    def __init__(self) -> None:
        self._profiles: dict[str, MaintainershipProfile] = {}
        for name, data in self.PROFILES.items():
            self._profiles[name] = MaintainershipProfile(
                subsystem=name, bus_factor=data["bus_factor"], risk=data["risk"],
                documented=data["documented"], rotation_ready=data["rotation_ready"],
            )

    def get_profile(self, subsystem: str) -> Optional[MaintainershipProfile]:
        return self._profiles.get(subsystem)

    def get_high_risk(self) -> list[MaintainershipProfile]:
        return [p for p in self._profiles.values() if p.risk in (MaintainershipRisk.HIGH, MaintainershipRisk.CRITICAL)]

    def get_rotation_ready(self) -> list[MaintainershipProfile]:
        return [p for p in self._profiles.values() if p.rotation_ready]

    @property
    def total_subsystems(self) -> int:
        return len(self._profiles)


# ═══════════════════════════════════════════════════════════════
# P6: Plugin Boundary Freezing
# ═══════════════════════════════════════════════════════════════

class BoundaryType(Enum):
    NEVER_BYPASS_APPROVALS = "never_bypass_approvals"
    NEVER_MODIFY_CORE = "never_modify_core"
    NEVER_SUPPRESS_AUDIT = "never_suppress_audit"
    NEVER_REDEFINE_VISIBILITY = "never_redefine_visibility"
    NEVER_CREATE_HIDDEN_EXECUTION = "never_create_hidden_execution"
    NEVER_REDEFINE_FROZEN_SEMANTICS = "never_redefine_frozen_semantics"


@dataclass
class FrozenBoundary:
    """A frozen plugin boundary."""
    boundary_type: BoundaryType
    description: str
    enforcement: str
    violation_consequence: str


class PluginBoundaryFreezing:
    """
    Defines non-negotiable plugin boundaries.
    These are runtime law — cannot be overridden.
    """

    BOUNDARIES: list[dict] = [
        {
            "type": BoundaryType.NEVER_BYPASS_APPROVALS,
            "description": "Plugins cannot bypass approval workflow",
            "enforcement": "CapabilityContract.BYPASS_APPROVALS is FORBIDDEN",
            "consequence": "Plugin is disabled immediately",
        },
        {
            "type": BoundaryType.NEVER_MODIFY_CORE,
            "description": "Plugins cannot modify PM core",
            "enforcement": "CapabilityContract.MODIFY_PM_CORE is FORBIDDEN",
            "consequence": "Plugin is disabled immediately",
        },
        {
            "type": BoundaryType.NEVER_SUPPRESS_AUDIT,
            "description": "Plugins cannot suppress audit trail",
            "enforcement": "Audit integrity enforced at runtime level",
            "consequence": "Plugin is disabled, audit entry created",
        },
        {
            "type": BoundaryType.NEVER_REDEFINE_VISIBILITY,
            "description": "Plugins cannot redefine visibility guarantees",
            "enforcement": "VisibilityGuaranteeEnforcer is runtime-level",
            "consequence": "Plugin is disabled",
        },
        {
            "type": BoundaryType.NEVER_CREATE_HIDDEN_EXECUTION,
            "description": "Plugins cannot create hidden execution paths",
            "enforcement": "All plugin actions are logged and visible",
            "consequence": "Plugin is disabled, investigation triggered",
        },
        {
            "type": BoundaryType.NEVER_REDEFINE_FROZEN_SEMANTICS,
            "description": "Plugins cannot redefine frozen semantics",
            "enforcement": "Frozen concepts are enforced at runtime level",
            "consequence": "Plugin is disabled",
        },
    ]

    def __init__(self) -> None:
        self._boundaries: list[FrozenBoundary] = [
            FrozenBoundary(boundary_type=b["type"], description=b["description"],
                          enforcement=b["enforcement"], violation_consequence=b["consequence"])
            for b in self.BOUNDARIES
        ]

    def get_boundaries(self) -> list[FrozenBoundary]:
        return list(self._boundaries)

    def check_violation(self, boundary_type: BoundaryType) -> Optional[FrozenBoundary]:
        for b in self._boundaries:
            if b.boundary_type == boundary_type:
                return b
        return None

    @property
    def total_boundaries(self) -> int:
        return len(self._boundaries)


# ═══════════════════════════════════════════════════════════════
# P7: Conceptual Compression Pass
# ═══════════════════════════════════════════════════════════════

class CompressionType(Enum):
    UNIFY_TERMINOLOGY = "unify_terminology"
    COLLAPSE_SEMANTICS = "collapse_semantics"
    SIMPLIFY_MENTAL_MODEL = "simplify_mental_model"
    REDUCE_VOCABULARY = "reduce_vocabulary"


@dataclass
class ConceptualCompression:
    """A conceptual compression opportunity."""
    name: str
    compression_type: CompressionType
    description: str
    current_state: str
    target_state: str
    cognitive_reduction: float  # 0-1, how much simpler


class ConceptualCompressionPass:
    """
    Compresses concepts, not code.
    Reduces cognitive entry cost.
    """

    OPPORTUNITIES: list[dict] = [
        {
            "name": "unify_calm_terminology",
            "type": CompressionType.UNIFY_TERMINOLOGY,
            "description": "CalmLevel in compression vs ergonomics — different names, same concept",
            "current": "CalmLevel(CALM/NORMAL/ELEVATED) vs CalmLevel(FULL/REDUCED/CALM/SILENT)",
            "target": "Single CalmLevel with clear mapping",
            "reduction": 0.3,
        },
        {
            "name": "unify_priority_terminology",
            "type": CompressionType.UNIFY_TERMINOLOGY,
            "description": "AttentionPriority vs InteractionPriority — identical values",
            "current": "Two enums with same values",
            "target": "Single CanonicalPriority",
            "reduction": 0.4,
        },
        {
            "name": "unify_event_terminology",
            "type": CompressionType.COLLAPSE_SEMANTICS,
            "description": "EntryType, NoiseType, EventCategory, InteractionType — all classify events",
            "current": "4 separate event classification systems",
            "target": "Single CanonicalEventType with subtypes",
            "reduction": 0.5,
        },
        {
            "name": "unify_explanation_terminology",
            "type": CompressionType.COLLAPSE_SEMANTICS,
            "description": "ExplanationField, ExplanationLevel, DisclosureLevel — all about explanation depth",
            "current": "3 separate explanation depth models",
            "target": "Single CanonicalExplanationLevel",
            "reduction": 0.4,
        },
        {
            "name": "simplify_subsystem_mental_model",
            "type": CompressionType.SIMPLIFY_MENTAL_MODEL,
            "description": "8 subpackages is a lot to learn",
            "current": "8 subpackages with overlapping concerns",
            "target": "4 core groups: execution, safety, optimization, ecosystem",
            "reduction": 0.3,
        },
    ]

    def __init__(self) -> None:
        self._opportunities: list[ConceptualCompression] = [
            ConceptualCompression(
                name=o["name"], compression_type=o["type"], description=o["description"],
                current_state=o["current"], target_state=o["target"], cognitive_reduction=o["reduction"],
            )
            for o in self.OPPORTUNITIES
        ]

    def get_opportunities(self) -> list[ConceptualCompression]:
        return list(self._opportunities)

    def get_high_impact(self) -> list[ConceptualCompression]:
        return [o for o in self._opportunities if o.cognitive_reduction >= 0.4]

    @property
    def total_opportunities(self) -> int:
        return len(self._opportunities)


# ═══════════════════════════════════════════════════════════════
# P8: Ecosystem Sustainability Review
# ═══════════════════════════════════════════════════════════════

class SustainabilityDimension(Enum):
    PLUGIN_COUNT = "plugin_count"
    EXPERIMENTATION_RATE = "experimentation_rate"
    GOVERNANCE_TOLERANCE = "governance_tolerance"
    FRAGMENTATION_SURVIVABILITY = "fragmentation_survivability"


class SustainabilityLevel(Enum):
    SUSTAINABLE = "sustainable"
    MONITOR = "monitor"
    UNSUSTAINABLE = "unsustainable"


@dataclass
class SustainabilityAssessment:
    dimension: SustainabilityDimension
    current_value: str
    sustainable_range: str
    level: SustainabilityLevel
    recommendation: str


class EcosystemSustainabilityReview:
    """
    Reviews what ecosystem shape is actually sustainable.
    """

    ASSESSMENTS: dict[SustainabilityDimension, dict] = {
        SustainabilityDimension.PLUGIN_COUNT: {
            "current": "0-5 plugins",
            "sustainable": "0-20 plugins",
            "level": SustainabilityLevel.SUSTAINABLE,
            "recommendation": "Current plugin count is healthy. Monitor as ecosystem grows.",
        },
        SustainabilityDimension.EXPERIMENTATION_RATE: {
            "current": "Low — most subsystems settled",
            "sustainable": "1-2 experimental subsystems at a time",
            "level": SustainabilityLevel.SUSTAINABLE,
            "recommendation": "Current experimentation rate is healthy.",
        },
        SustainabilityDimension.GOVERNANCE_TOLERANCE: {
            "current": "Moderate — some bypass observed",
            "sustainable": "Contributors follow >80% of governance",
            "level": SustainabilityLevel.MONITOR,
            "recommendation": "Simplify governance to reduce bypass. Target: 2 approval steps max.",
        },
        SustainabilityDimension.FRAGMENTATION_SURVIVABILITY: {
            "current": "Low fragmentation — canonical vocabulary enforced",
            "sustainable": "Semantic drift < 10% per year",
            "level": SustainabilityLevel.SUSTAINABLE,
            "recommendation": "Current coherence enforcement is working.",
        },
    }

    def __init__(self) -> None:
        self._assessments: dict[SustainabilityDimension, SustainabilityAssessment] = {}
        for dim, data in self.ASSESSMENTS.items():
            self._assessments[dim] = SustainabilityAssessment(
                dimension=dim, current_value=data["current"],
                sustainable_range=data["sustainable"], level=data["level"],
                recommendation=data["recommendation"],
            )

    def get_assessment(self, dimension: SustainabilityDimension) -> Optional[SustainabilityAssessment]:
        return self._assessments.get(dimension)

    def get_unsustainable(self) -> list[SustainabilityAssessment]:
        return [a for a in self._assessments.values() if a.level == SustainabilityLevel.UNSUSTAINABLE]

    @property
    def total_assessments(self) -> int:
        return len(self._assessments)


# ═══════════════════════════════════════════════════════════════
# P9: Architecture Preservation Layer
# ═══════════════════════════════════════════════════════════════

class PreservationType(Enum):
    RATIONALE = "rationale"                # Why decisions were made
    IDENTITY = "identity"                  # What the system is
    INVARIANTS = "invariants"              # Core invariants
    ANTI_GOALS = "anti_goals"              # What we intentionally did NOT become
    LESSONS = "lessons"                    # Lessons from rejected directions
    FROZEN_PRINCIPLES = "frozen_principles"  # Principles that must not erode


@dataclass
class PreservedArtifact:
    """A preserved architectural artifact."""
    preservation_type: PreservationType
    name: str
    content: str
    importance: str  # critical, high, medium


class ArchitecturePreservationLayer:
    """
    Preserves architectural knowledge that must survive maintainer turnover.
    Especially preserves "what we intentionally did NOT become."
    """

    ARTIFACTS: list[dict] = [
        {
            "type": PreservationType.IDENTITY,
            "name": "core_identity",
            "content": (
                "AI Team System is a human-controlled, local-first, browser-first "
                "governed engineering runtime. NOT an AGI platform, autonomous company, "
                "enterprise governance monster, or SaaS product."
            ),
            "importance": "critical",
        },
        {
            "type": PreservationType.ANTI_GOALS,
            "name": "what_we_are_not",
            "content": (
                "We are NOT: AGI platform, autonomous company, enterprise governance "
                "monster, AI replacement system, SaaS platform, cloud service, "
                "distributed computing platform, agent marketplace."
            ),
            "importance": "critical",
        },
        {
            "type": PreservationType.FROZEN_PRINCIPLES,
            "name": "frozen_principles",
            "content": (
                "1. Deterministic > AI (core is deterministic, AI only for augmentation)\n"
                "2. Safety > Autonomy (safety constraints are hard)\n"
                "3. Coordination > Complexity (simple protocols over emergent behavior)\n"
                "4. Signal > Noise (suppress by default, expand on demand)\n"
                "5. User time is expensive (minimize cognitive load)\n"
                "6. Restraint as architecture (default to inaction)\n"
                "7. Deletion is first-class (removing is as important as adding)"
            ),
            "importance": "critical",
        },
        {
            "type": PreservationType.LESSONS,
            "name": "lessons_from_rejected_directions",
            "content": (
                "1. AI autonomy expansion: rejected — violates deterministic > AI\n"
                "2. Enterprise multi-tenant: rejected — violates local-first identity\n"
                "3. Cloud sync: rejected — violates local-first identity\n"
                "4. Agent swarms: rejected — violates coordination > complexity\n"
                "5. Self-modifying architecture: rejected — violates deterministic core\n"
                "6. Contributor ranking: rejected — violates human-controlled principle\n"
                "7. Recursive governance: rejected — violates simplicity principle"
            ),
            "importance": "high",
        },
        {
            "type": PreservationType.RATIONALE,
            "name": "why_8_subpackages",
            "content": (
                "8 subpackages emerged from natural concern separation:\n"
                "durability=survivability, ergonomics=human scaling, trust=predictability,\n"
                "optimization=performance, compression=minimalism, coherence=consistency,\n"
                "ecosystem=contributor scaling, stabilization=long-term health,\n"
                "reality=operational validation, stewardship=preservation.\n"
                "Merging them would create a monolith. Splitting further would fragment."
            ),
            "importance": "medium",
        },
    ]

    def __init__(self) -> None:
        self._artifacts: list[PreservedArtifact] = [
            PreservedArtifact(
                preservation_type=a["type"], name=a["name"],
                content=a["content"], importance=a["importance"],
            )
            for a in self.ARTIFACTS
        ]

    def get_artifacts(self, preservation_type: Optional[PreservationType] = None) -> list[PreservedArtifact]:
        if preservation_type:
            return [a for a in self._artifacts if a.preservation_type == preservation_type]
        return list(self._artifacts)

    def get_critical_artifacts(self) -> list[PreservedArtifact]:
        return [a for a in self._artifacts if a.importance == "critical"]

    @property
    def total_artifacts(self) -> int:
        return len(self._artifacts)


# ═══════════════════════════════════════════════════════════════
# P10: Stewardship Engine
# ═══════════════════════════════════════════════════════════════

class StewardshipQuestion(Enum):
    IMPROVES_SURVIVABILITY = "improves_survivability"
    REDUCES_COMPLEXITY = "reduces_complexity"
    REDUCES_FRICTION = "reduces_friction"
    PRESERVES_IDENTITY = "preserves_identity"
    ENABLES_GROWTH = "enables_growth"


class StewardshipVerdict(Enum):
    HEALTHY = "healthy"
    NEEDS_ATTENTION = "needs_attention"
    NEEDS_REDUCTION = "needs_reduction"
    CRITICAL = "critical"


@dataclass
class StewardshipAssessment:
    area: str
    verdict: StewardshipVerdict
    reasoning: str
    recommendations: list[str] = field(default_factory=list)


class StewardshipEngine:
    """
    Meta-subsystem: asks "how to keep the system healthy for 5 more years?"
    Not "what else to add?"
    """

    def assess_area(self, area: str, health_score: float) -> StewardshipAssessment:
        """Assess an area for long-term health."""
        if health_score >= 0.8:
            verdict = StewardshipVerdict.HEALTHY
            reasoning = f"{area} is healthy (score: {health_score:.0%})"
            recommendations = [f"Continue monitoring {area}"]
        elif health_score >= 0.6:
            verdict = StewardshipVerdict.NEEDS_ATTENTION
            reasoning = f"{area} needs attention (score: {health_score:.0%})"
            recommendations = [f"Review {area} for simplification opportunities"]
        elif health_score >= 0.4:
            verdict = StewardshipVerdict.NEEDS_REDUCTION
            reasoning = f"{area} needs reduction (score: {health_score:.0%})"
            recommendations = [f"Reduce complexity in {area}", f"Consider merging or archiving parts of {area}"]
        else:
            verdict = StewardshipVerdict.CRITICAL
            reasoning = f"{area} is critical (score: {health_score:.0%})"
            recommendations = [f"URGENT: Reduce {area} immediately", f"Consider archiving {area}"]

        return StewardshipAssessment(area=area, verdict=verdict, reasoning=reasoning, recommendations=recommendations)

    def generate_report(self, area_scores: dict[str, float]) -> list[StewardshipAssessment]:
        """Generate stewardship report for all areas."""
        return [self.assess_area(area, score) for area, score in area_scores.items()]

    def should_expand(self, area: str, health_score: float) -> tuple[bool, str]:
        """Evaluate whether expansion is justified."""
        if health_score >= 0.8:
            return False, f"{area} is healthy — expansion is not justified"
        elif health_score >= 0.6:
            return False, f"{area} needs attention — fix before expanding"
        else:
            return False, f"{area} needs reduction — expansion is dangerous"
