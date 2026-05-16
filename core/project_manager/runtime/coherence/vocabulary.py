"""
Phase 13, P1: Unified Runtime Vocabulary

Central registry of canonical runtime concept definitions.
Ensures all subsystems share the same semantics for core concepts.

Current state after Phase 12 audit:
- 3 different priority models across subsystems
- 2 different state models
- 4+ different event definitions
- 2 different approval models
- 3 different explanation/disclosure models

This module establishes the canonical vocabulary and provides
machine-checkable contracts for semantic consistency.

Principle: Shared concepts must have shared meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# CANONICAL ENUM DEFINITIONS
# ═══════════════════════════════════════════════════════════════

class CanonicalPriority(Enum):
    """
    Single canonical priority model for the entire runtime.

    Replaces:
    - ergonomics/attention_management.AttentionPriority
    - compression/interaction_minimalism.InteractionPriority
    - ergonomics/calm_mode.CalmLevel (mapped)
    """
    CRITICAL = 0    # Must be seen immediately — safety, data loss, integrity
    HIGH = 1        # Should be seen soon — significant operational event
    NORMAL = 2      # Routine operational information
    LOW = 3         # Marginal — suppress by default
    SILENT = 4      # Never show unless explicitly requested


class CanonicalStateTier(Enum):
    """
    Single canonical state lifecycle model.

    Replaces/augments:
    - durability/state_lifecycle.StateTier
    - durability/context_gc.ContextType (mapped to tiers)

    Note: ContextType is a separate concern (what kind of data),
    StateTier is about lifecycle duration. Both are kept but
    cross-referenced for clarity.
    """
    EPHEMERAL = "ephemeral"       # Single operation scope
    SESSION = "session"           # User session scope
    OPERATIONAL = "operational"   # Runtime session scope
    STRUCTURAL = "structural"     # Persistent across sessions


class CanonicalEventType(Enum):
    """
    Single canonical event classification.

    Unifies:
    - durability/observability.EntryType
    - ergonomics/noise_reduction.NoiseType (as noise subtype)
    - trust/transparency_contracts.EventCategory (mapped)
    - compression/interaction_minimalism.InteractionType (subtype)
    """
    # Core operational events
    RUNTIME_EVENT = "runtime_event"
    DECISION = "decision"
    VALIDATION = "validation"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    RECOVERY = "recovery"

    # Interaction events
    USER_INTERACTION = "user_interaction"
    APPROVAL_REQUEST = "approval_request"
    NOTIFICATION = "notification"
    EXPLANATION = "explanation"

    # System events
    NOISE_DETECTED = "noise_detected"
    INTEGRITY_EVENT = "integrity_event"
    GOVERNANCE_EVENT = "governance_event"


class CanonicalApprovalRisk(Enum):
    """Single canonical approval risk model."""
    LOW = "low"           # Auto-applicable, minimal impact
    MEDIUM = "medium"     # Review suggested, moderate impact
    HIGH = "high"         # Review required, significant impact
    CRITICAL = "critical" # Mandatory approval, irreversible impact


class CanonicalApprovalStatus(Enum):
    """Single canonical approval status model."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPLIED = "auto_applied"
    BATCHED = "batched"
    SKIPPED = "skipped"
    EXPIRED = "expired"


class CanonicalExplanationLevel(Enum):
    """
    Single canonical explanation depth model.

    Unifies:
    - durability/explainability_layer.ExplanationField (structural)
    - trust/explainability_compression.ExpressionLevel (depth)
    - compression/progressive_disclosure.DisclosureLevel (UI depth)
    """
    MINIMAL = 0      # What happened (one line)
    SUMMARY = 1      # What + why (short paragraph)
    DETAILED = 2     # What + why + how (structured)
    FULL = 3         # Complete trace with context
    DEBUG = 4        # Raw data, internal state


class CanonicalVisibility(Enum):
    """Single canonical visibility model."""
    SHOW = "show"              # Always visible
    SUMMARIZE = "summarize"    # Compressed representation
    DELAY = "delay"            # Shown after delay/batch
    SUPPRESS = "suppress"      # Hidden unless requested


class CalmDimension(Enum):
    """Canonical calm dimensions (from Phase 12, kept as-is)."""
    INTERRUPTION_DENSITY = "interruption_density"
    ALERT_FREQUENCY = "alert_frequency"
    APPROVAL_PRESSURE = "approval_pressure"
    RECOVERY_STRESS = "recovery_stress"
    WORKFLOW_TURBULENCE = "workflow_turbulence"
    EXPLANATION_OVERLOAD = "explanation_overload"


# ═══════════════════════════════════════════════════════════════
# CROSS-REFERENCE MAP: Old → Canonical
# ═══════════════════════════════════════════════════════════════

PRIORITY_MAPPING: dict[str, CanonicalPriority] = {
    # AttentionPriority (ergonomics)
    "AttentionPriority.CRITICAL": CanonicalPriority.CRITICAL,
    "AttentionPriority.HIGH": CanonicalPriority.HIGH,
    "AttentionPriority.NORMAL": CanonicalPriority.NORMAL,
    "AttentionPriority.LOW": CanonicalPriority.LOW,
    "AttentionPriority.SILENT": CanonicalPriority.SILENT,
    # InteractionPriority (compression)
    "InteractionPriority.CRITICAL": CanonicalPriority.CRITICAL,
    "InteractionPriority.IMPORTANT": CanonicalPriority.HIGH,
    "InteractionPriority.NORMAL": CanonicalPriority.NORMAL,
    "InteractionPriority.LOW": CanonicalPriority.LOW,
    "InteractionPriority.SILENT": CanonicalPriority.SILENT,
    # CalmLevel (ergonomics) — inverted mapping
    "CalmLevel.FULL": CanonicalPriority.CRITICAL,
    "CalmLevel.REDUCED": CanonicalPriority.HIGH,
    "CalmLevel.CALM": CanonicalPriority.NORMAL,
    "CalmLevel.SILENT": CanonicalPriority.SILENT,
}

STATE_TIER_COMPATIBILITY: dict[str, CanonicalStateTier] = {
    "StateTier.EPHEMERAL": CanonicalStateTier.EPHEMERAL,
    "StateTier.SESSION": CanonicalStateTier.SESSION,
    "StateTier.OPERATIONAL": CanonicalStateTier.OPERATIONAL,
    "StateTier.STRUCTURAL": CanonicalStateTier.STRUCTURAL,
}

EXPLANATION_DEPTH_MAPPING: dict[str, CanonicalExplanationLevel] = {
    # ExplanationLevel (trust/explainability_compression)
    "ExplanationLevel.SUMMARY": CanonicalExplanationLevel.SUMMARY,
    "ExplanationLevel.REASONING": CanonicalExplanationLevel.DETAILED,
    "ExplanationLevel.FULL_TRACE": CanonicalExplanationLevel.FULL,
    # DisclosureLevel (compression/progressive_disclosure)
    "DisclosureLevel.MINIMAL": CanonicalExplanationLevel.MINIMAL,
    "DisclosureLevel.SUMMARY": CanonicalExplanationLevel.SUMMARY,
    "DisclosureLevel.DETAILED": CanonicalExplanationLevel.DETAILED,
    "DisclosureLevel.FULL": CanonicalExplanationLevel.FULL,
    "DisclosureLevel.DEBUG": CanonicalExplanationLevel.DEBUG,
}


# ═══════════════════════════════════════════════════════════════
# VOCABULARY REGISTRY
# ═══════════════════════════════════════════════════════════════

@dataclass
class ConceptDefinition:
    """Canonical definition of a runtime concept."""
    name: str
    description: str
    canonical_enum: type[Enum]
    source_modules: list[str]  # Which subpackages use this concept
    aliases: list[str] = field(default_factory=list)  # Old names that map to this
    invariants: list[str] = field(default_factory=list)  # Semantic constraints


class RuntimeVocabularyRegistry:
    """
    Central registry of all canonical runtime concepts.
    Provides lookup, validation, and cross-reference capabilities.
    """

    def __init__(self) -> None:
        self._concepts: dict[str, ConceptDefinition] = {}
        self._register_core_concepts()

    def _register_core_concepts(self) -> None:
        """Register all canonical concepts."""
        self.register(ConceptDefinition(
            name="priority",
            description="Operational priority of events, interactions, and attention requests",
            canonical_enum=CanonicalPriority,
            source_modules=[
                "ergonomics/attention_management",
                "ergonomics/calm_mode",
                "compression/interaction_minimalism",
                "trust/visibility_guarantees",
            ],
            aliases=["AttentionPriority", "InteractionPriority", "CalmLevel"],
            invariants=[
                "CRITICAL must always be shown immediately — no suppression",
                "SILENT must never be shown without explicit user request",
                "Priority must be monotonic: CRITICAL < HIGH < NORMAL < LOW < SILENT",
            ],
        ))

        self.register(ConceptDefinition(
            name="state_tier",
            description="Lifecycle tier determining state persistence scope",
            canonical_enum=CanonicalStateTier,
            source_modules=[
                "durability/state_lifecycle",
                "durability/context_gc",
            ],
            aliases=["StateTier"],
            invariants=[
                "EPHEMERAL state must not persist beyond single operation",
                "STRUCTURAL state must survive session restarts",
                "State can only move to higher tiers (EPHEMERAL → STRUCTURAL), not reverse",
            ],
        ))

        self.register(ConceptDefinition(
            name="event_type",
            description="Classification of runtime events for routing and handling",
            canonical_enum=CanonicalEventType,
            source_modules=[
                "durability/observability",
                "ergonomics/noise_reduction",
                "trust/transparency_contracts",
                "compression/interaction_minimalism",
            ],
            aliases=["EntryType", "NoiseType", "EventCategory", "InteractionType"],
            invariants=[
                "ERROR events must always be logged regardless of calm mode",
                "RECOVERY events must include causality reference",
                "NOISE_DETECTED events must include fingerprint for dedup",
            ],
        ))

        self.register(ConceptDefinition(
            name="approval_risk",
            description="Risk level associated with an approval decision",
            canonical_enum=CanonicalApprovalRisk,
            source_modules=[
                "ergonomics/approval_intelligence",
                "trust/governance_pressure",
                "runtime/approval",
            ],
            aliases=["ApprovalRisk"],
            invariants=[
                "CRITICAL risk requires mandatory human approval — no auto-apply",
                "LOW risk can be auto-applied with audit trail",
                "Risk level must be deterministic given the same operation context",
            ],
        ))

        self.register(ConceptDefinition(
            name="approval_status",
            description="Current state of an approval decision",
            canonical_enum=CanonicalApprovalStatus,
            source_modules=[
                "ergonomics/approval_intelligence",
                "trust/audit_visible_automation",
            ],
            aliases=["ApprovalStatus"],
            invariants=[
                "PENDING must eventually transition — no permanent pending",
                "AUTO_APPLIED must have audit trail with risk justification",
                "EXPIRED approvals must require re-request, not silent skip",
            ],
        ))

        self.register(ConceptDefinition(
            name="explanation_level",
            description="Depth of explanation provided for runtime decisions",
            canonical_enum=CanonicalExplanationLevel,
            source_modules=[
                "durability/explainability_layer",
                "trust/explainability_compression",
                "compression/progressive_disclosure",
            ],
            aliases=["ExplanationLevel", "DisclosureLevel", "ExplanationField"],
            invariants=[
                "MINIMAL must always be available — it's the safe default",
                "DEBUG must never leak internal credentials or tokens",
                "Level must be monotonically expandable — no skip from MINIMAL to FULL",
            ],
        ))

        self.register(ConceptDefinition(
            name="visibility",
            description="Canonical visibility action for runtime information",
            canonical_enum=CanonicalVisibility,
            source_modules=[
                "trust/transparency_contracts",
                "trust/visibility_guarantees",
                "compression/interaction_minimalism",
            ],
            aliases=["VisibilityAction", "GuaranteeLevel"],
            invariants=[
                "CRITICAL priority information must always SHOW, never SUPPRESS",
                "SUPPRESSED information must be recoverable on explicit request",
                "Visibility action must respect both priority AND user preference",
            ],
        ))

    def register(self, concept: ConceptDefinition) -> None:
        """Register a concept definition."""
        self._concepts[concept.name] = concept

    def get(self, name: str) -> Optional[ConceptDefinition]:
        """Get a concept definition by name."""
        return self._concepts.get(name)

    def get_canonical_enum(self, name: str) -> Optional[type[Enum]]:
        """Get the canonical enum for a concept."""
        concept = self._concepts.get(name)
        if concept:
            return concept.canonical_enum
        return None

    def list_concepts(self) -> list[str]:
        """List all registered concept names."""
        return list(self._concepts.keys())

    def get_source_modules(self, concept_name: str) -> list[str]:
        """Get all modules that use a given concept."""
        concept = self._concepts.get(concept_name)
        return concept.source_modules if concept else []

    def get_aliases(self, concept_name: str) -> list[str]:
        """Get all alias names for a concept."""
        concept = self._concepts.get(concept_name)
        return concept.aliases if concept else []

    def get_invariants(self, concept_name: str) -> list[str]:
        """Get semantic invariants for a concept."""
        concept = self._concepts.get(concept_name)
        return concept.invariants if concept else []

    def resolve_priority(self, qualified_name: str) -> Optional[CanonicalPriority]:
        """Resolve any priority variant to canonical."""
        return PRIORITY_MAPPING.get(qualified_name)

    def resolve_explanation_level(self, qualified_name: str) -> Optional[CanonicalExplanationLevel]:
        """Resolve any explanation level variant to canonical."""
        return EXPLANATION_DEPTH_MAPPING.get(qualified_name)

    @property
    def total_concepts(self) -> int:
        return len(self._concepts)

    @property
    def all_invariants(self) -> list[str]:
        """Get all invariants across all concepts."""
        result = []
        for concept in self._concepts.values():
            result.extend(concept.invariants)
        return result
