"""
Phase 13, P7: Semantic Compression

Unifies conceptual models across subsystems.
Not just code duplication — conceptual duplication.

After Phase 12 audit, these conceptual overlaps were found:
- 3 priority models → CanonicalPriority
- 4+ event type systems → CanonicalEventType
- 3 explanation depth models → CanonicalExplanationLevel
- 2 state models → CanonicalStateTier
- 2 approval models → CanonicalApprovalRisk/Status
- 3 visibility models → CanonicalVisibility

This module provides the migration path from fragmented to unified semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CompressionTarget(Enum):
    PRIORITY = "priority"
    EVENT_TYPE = "event_type"
    EXPLANATION_LEVEL = "explanation_level"
    STATE_TIER = "state_tier"
    APPROVAL = "approval"
    VISIBILITY = "visibility"


@dataclass
class ConceptualOverlap:
    """A detected conceptual overlap between subsystems."""
    target: CompressionTarget
    canonical_name: str
    source_modules: list[str]
    old_types: list[str]           # Old enum/class names
    lines_estimate: int            # Estimated lines that can be saved
    complexity_reduction: float    # Estimated complexity reduction (0-1)
    migration_effort: str          # low, medium, high


@dataclass
class SemanticCompressionPlan:
    """Plan for semantic compression across subsystems."""
    overlaps: list[ConceptualOverlap] = field(default_factory=list)
    total_lines_saved: int = 0
    total_complexity_reduction: float = 0.0

    @property
    def high_impact(self) -> list[ConceptualOverlap]:
        return [o for o in self.overlaps if o.complexity_reduction > 0.3]

    @property
    def quick_wins(self) -> list[ConceptualOverlap]:
        return [o for o in self.overlaps if o.migration_effort == "low"]


class SemanticCompressor:
    """
    Plans and tracks semantic compression across subsystems.
    Provides migration paths from fragmented to unified conceptual models.
    """

    # Known conceptual overlaps from Phase 12 audit
    KNOWN_OVERLAPS: list[dict] = [
        {
            "target": CompressionTarget.PRIORITY,
            "canonical_name": "CanonicalPriority",
            "source_modules": [
                "ergonomics/attention_management",
                "ergonomics/calm_mode",
                "compression/interaction_minimalism",
            ],
            "old_types": ["AttentionPriority", "CalmLevel", "InteractionPriority"],
            "lines_estimate": 80,
            "complexity_reduction": 0.4,
            "migration_effort": "medium",
        },
        {
            "target": CompressionTarget.EVENT_TYPE,
            "canonical_name": "CanonicalEventType",
            "source_modules": [
                "durability/observability",
                "ergonomics/noise_reduction",
                "trust/transparency_contracts",
                "compression/interaction_minimalism",
            ],
            "old_types": ["EntryType", "NoiseType", "EventCategory", "InteractionType"],
            "lines_estimate": 150,
            "complexity_reduction": 0.5,
            "migration_effort": "high",
        },
        {
            "target": CompressionTarget.EXPLANATION_LEVEL,
            "canonical_name": "CanonicalExplanationLevel",
            "source_modules": [
                "durability/explainability_layer",
                "trust/explainability_compression",
                "compression/progressive_disclosure",
            ],
            "old_types": ["ExplanationField", "ExplanationLevel", "DisclosureLevel"],
            "lines_estimate": 60,
            "complexity_reduction": 0.3,
            "migration_effort": "medium",
        },
        {
            "target": CompressionTarget.STATE_TIER,
            "canonical_name": "CanonicalStateTier",
            "source_modules": [
                "durability/state_lifecycle",
                "durability/context_gc",
            ],
            "old_types": ["StateTier", "ContextType"],
            "lines_estimate": 40,
            "complexity_reduction": 0.2,
            "migration_effort": "low",
        },
        {
            "target": CompressionTarget.APPROVAL,
            "canonical_name": "CanonicalApprovalRisk/Status",
            "source_modules": [
                "ergonomics/approval_intelligence",
                "trust/governance_pressure",
                "runtime/approval",
            ],
            "old_types": ["ApprovalRisk", "ApprovalStatus"],
            "lines_estimate": 50,
            "complexity_reduction": 0.25,
            "migration_effort": "low",
        },
        {
            "target": CompressionTarget.VISIBILITY,
            "canonical_name": "CanonicalVisibility",
            "source_modules": [
                "trust/transparency_contracts",
                "trust/visibility_guarantees",
                "compression/interaction_minimalism",
            ],
            "old_types": ["VisibilityAction", "GuaranteeLevel"],
            "lines_estimate": 45,
            "complexity_reduction": 0.3,
            "migration_effort": "medium",
        },
    ]

    def create_plan(self) -> SemanticCompressionPlan:
        """Create semantic compression plan from known overlaps."""
        overlaps = []
        for data in self.KNOWN_OVERLAPS:
            overlaps.append(ConceptualOverlap(
                target=data["target"],
                canonical_name=data["canonical_name"],
                source_modules=data["source_modules"],
                old_types=data["old_types"],
                lines_estimate=data["lines_estimate"],
                complexity_reduction=data["complexity_reduction"],
                migration_effort=data["migration_effort"],
            ))

        total_lines = sum(o.lines_estimate for o in overlaps)
        total_complexity = sum(o.complexity_reduction for o in overlaps) / len(overlaps) if overlaps else 0

        return SemanticCompressionPlan(
            overlaps=overlaps,
            total_lines_saved=total_lines,
            total_complexity_reduction=total_complexity,
        )

    def get_migration_path(self, target: CompressionTarget) -> Optional[ConceptualOverlap]:
        """Get migration path for a specific compression target."""
        plan = self.create_plan()
        for overlap in plan.overlaps:
            if overlap.target == target:
                return overlap
        return None
