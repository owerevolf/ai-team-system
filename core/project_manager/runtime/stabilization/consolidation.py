"""
Phase 16, P11: Runtime Consolidation Engine

Aggressive subsystem consolidation:
- merge duplicate policies
- collapse overlapping abstractions
- unify runtime utilities
- remove ceremonial layers

Goal: reduce conceptual count, not just LOC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConsolidationType(Enum):
    MERGE_DUPLICATE = "merge_duplicate"        # Same concept, multiple definitions
    COLLAPSE_OVERLAP = "collapse_overlap"      # Overlapping abstractions
    UNIFY_UTILITY = "unify_utility"            # Duplicate utilities
    REMOVE_CEREMONIAL = "remove_ceremonial"    # Unnecessary ceremony
    CROSS_REFERENCE = "cross_reference"        # Link related concepts


class ConsolidationPriority(Enum):
    CRITICAL = "critical"      # Direct duplication, must merge
    HIGH = "high"              # Significant overlap
    MEDIUM = "medium"          # Some duplication
    LOW = "low"                # Minor cleanup


@dataclass
class ConsolidationItem:
    """A single consolidation opportunity."""
    name: str
    consolidation_type: ConsolidationType
    priority: ConsolidationPriority
    source_modules: list[str]
    description: str
    recommended_action: str
    estimated_loc_saved: int = 0
    applied: bool = False


@dataclass
class ConsolidationReport:
    """Full consolidation report."""
    items: list[ConsolidationItem] = field(default_factory=list)
    total_loc_saved: int = 0
    total_items_applied: int = 0

    @property
    def pending_items(self) -> list[ConsolidationItem]:
        return [i for i in self.items if not i.applied]

    @property
    def critical_items(self) -> list[ConsolidationItem]:
        return [i for i in self.items if i.priority == ConsolidationPriority.CRITICAL]


class RuntimeConsolidationEngine:
    """
    Identifies and executes runtime consolidation opportunities.
    Reduces conceptual count and removes duplication.
    """

    # Known consolidation opportunities from Phase 16 audit
    KNOWN_CONSOLIDATIONS: list[dict] = [
        {
            "name": "CalmDimension duplication",
            "type": ConsolidationType.MERGE_DUPLICATE,
            "priority": ConsolidationPriority.CRITICAL,
            "modules": ["coherence/vocabulary.py", "compression/operational_calm.py"],
            "description": "CalmDimension enum defined identically in 2 modules",
            "action": "Keep single definition in coherence/vocabulary.py, import from there",
            "loc_saved": 15,
        },
        {
            "name": "CalmLevel fragmentation",
            "type": ConsolidationType.COLLAPSE_OVERLAP,
            "priority": ConsolidationPriority.HIGH,
            "modules": ["compression/operational_calm.py", "ergonomics/calm_mode.py"],
            "description": "Two different CalmLevel enums with overlapping semantics",
            "action": "Unify under single CalmLevel with mapping from old values",
            "loc_saved": 30,
        },
        {
            "name": "PressureType split",
            "type": ConsolidationType.CROSS_REFERENCE,
            "priority": ConsolidationPriority.MEDIUM,
            "modules": ["ecosystem/identity.py", "trust/governance_pressure.py"],
            "description": "PressureType in identity (external) vs governance_pressure (internal) are complementary",
            "action": "Cross-reference: external pressures affect internal pressure readings",
            "loc_saved": 0,
        },
        {
            "name": "Duplicate priority models",
            "type": ConsolidationType.COLLAPSE_OVERLAP,
            "priority": ConsolidationPriority.HIGH,
            "modules": ["ergonomics/attention_management.py", "compression/interaction_minimalism.py"],
            "description": "AttentionPriority and InteractionPriority have identical values",
            "action": "Both should import from CanonicalPriority in coherence/vocabulary.py",
            "loc_saved": 25,
        },
        {
            "name": "Duplicate event type systems",
            "type": ConsolidationType.COLLAPSE_OVERLAP,
            "priority": ConsolidationPriority.HIGH,
            "modules": ["durability/observability.py", "ergonomics/noise_reduction.py",
                       "trust/transparency_contracts.py", "compression/interaction_minimalism.py"],
            "description": "4 separate event classification systems",
            "action": "All should use CanonicalEventType from coherence/vocabulary.py",
            "loc_saved": 60,
        },
        {
            "name": "Duplicate explanation models",
            "type": ConsolidationType.COLLAPSE_OVERLAP,
            "priority": ConsolidationPriority.MEDIUM,
            "modules": ["durability/explainability_layer.py", "trust/explainability_compression.py",
                       "compression/progressive_disclosure.py"],
            "description": "ExplanationField, ExplanationLevel, DisclosureLevel overlap",
            "action": "All should use CanonicalExplanationLevel from coherence/vocabulary.py",
            "loc_saved": 40,
        },
        {
            "name": "Duplicate state models",
            "type": ConsolidationType.CROSS_REFERENCE,
            "priority": ConsolidationPriority.MEDIUM,
            "modules": ["durability/state_lifecycle.py", "durability/context_gc.py"],
            "description": "StateTier and ContextType have overlapping lifecycle concerns",
            "action": "ContextType should reference StateTier for lifecycle management",
            "loc_saved": 10,
        },
        {
            "name": "Duplicate approval models",
            "type": ConsolidationType.COLLAPSE_OVERLAP,
            "priority": ConsolidationPriority.MEDIUM,
            "modules": ["ergonomics/approval_intelligence.py", "trust/governance_pressure.py"],
            "description": "Approval logic spread across ergonomics and trust",
            "action": "Centralize approval types in CanonicalApprovalRisk/Status",
            "loc_saved": 35,
        },
    ]

    def __init__(self) -> None:
        self._items: dict[str, ConsolidationItem] = {}
        self._register_known()

    def _register_known(self) -> None:
        """Register known consolidation opportunities."""
        for data in self.KNOWN_CONSOLIDATIONS:
            item = ConsolidationItem(
                name=data["name"],
                consolidation_type=data["type"],
                priority=data["priority"],
                source_modules=data["modules"],
                description=data["description"],
                recommended_action=data["action"],
                estimated_loc_saved=data.get("loc_saved", 0),
            )
            self._items[item.name] = item

    def generate_report(self) -> ConsolidationReport:
        """Generate full consolidation report."""
        items = list(self._items.values())
        total_saved = sum(i.estimated_loc_saved for i in items if not i.applied)
        return ConsolidationReport(
            items=items,
            total_loc_saved=total_saved,
            total_items_applied=sum(1 for i in items if i.applied),
        )

    def apply_consolidation(self, name: str) -> bool:
        """Mark a consolidation as applied."""
        item = self._items.get(name)
        if item:
            item.applied = True
            return True
        return False

    def get_item(self, name: str) -> Optional[ConsolidationItem]:
        """Get a consolidation item by name."""
        return self._items.get(name)

    @property
    def total_items(self) -> int:
        return len(self._items)

    @property
    def total_potential_savings(self) -> int:
        return sum(i.estimated_loc_saved for i in self._items.values())
