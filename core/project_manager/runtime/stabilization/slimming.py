"""
Phase 16, P6: Runtime Slimming Initiative

Continuous slimming pressure:
- dead utility collapse
- duplicated logic removal
- abstraction pruning
- helper consolidation

Goal: bounded runtime growth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SlimmingType(Enum):
    DEAD_UTILITY = "dead_utility"          # Unused utility functions
    DUPLICATED_LOGIC = "duplicated_logic"  # Same logic in multiple places
    ABSTRACTION_PRUNE = "abstraction_prune"  # Unnecessary abstraction layer
    HELPER_CONSOLIDATE = "helper_consolidate"  # Duplicate helpers
    DEPENDENCY_MINIMIZE = "dependency_minimize"  # Unnecessary dependencies


@dataclass
class SlimmingItem:
    """A single slimming opportunity."""
    name: str
    slimming_type: SlimmingType
    module: str
    description: str
    estimated_loc_saved: int
    safe_to_remove: bool = False
    applied: bool = False


@dataclass
class SlimmingReport:
    """Full slimming report."""
    items: list[SlimmingItem] = field(default_factory=list)
    total_loc_saved: int = 0
    current_loc: int = 0

    @property
    def potential_savings(self) -> int:
        return sum(i.estimated_loc_saved for i in self.items if not i.applied)

    @property
    def safe_removals(self) -> list[SlimmingItem]:
        return [i for i in self.items if i.safe_to_remove and not i.applied]


class RuntimeSlimmingInitiative:
    """
    Identifies and tracks runtime slimming opportunities.
    Keeps runtime growth bounded.
    """

    # Known slimming opportunities from Phase 16 audit
    KNOWN_SLIMMING: list[dict] = [
        {
            "name": "duplicate_calm_dimension",
            "type": SlimmingType.DUPLICATED_LOGIC,
            "module": "coherence/vocabulary.py + compression/operational_calm.py",
            "description": "CalmDimension enum defined identically in 2 modules",
            "loc_saved": 15,
            "safe": True,
        },
        {
            "name": "duplicate_calm_level",
            "type": SlimmingType.ABSTRACTION_PRUNE,
            "module": "compression/operational_calm.py + ergonomics/calm_mode.py",
            "description": "Two CalmLevel enums with overlapping semantics",
            "loc_saved": 30,
            "safe": True,
        },
        {
            "name": "duplicate_priority_enums",
            "type": SlimmingType.DUPLICATED_LOGIC,
            "module": "ergonomics/attention_management.py + compression/interaction_minimalism.py",
            "description": "AttentionPriority and InteractionPriority have identical values",
            "loc_saved": 25,
            "safe": True,
        },
        {
            "name": "duplicate_event_enums",
            "type": SlimmingType.DUPLICATED_LOGIC,
            "module": "durability/observability.py + ergonomics/noise_reduction.py + trust/transparency_contracts.py",
            "description": "4 separate event classification systems",
            "loc_saved": 60,
            "safe": True,
        },
        {
            "name": "duplicate_explanation_enums",
            "type": SlimmingType.DUPLICATED_LOGIC,
            "module": "durability/explainability_layer.py + trust/explainability_compression.py + compression/progressive_disclosure.py",
            "description": "3 separate explanation depth models",
            "loc_saved": 40,
            "safe": True,
        },
        {
            "name": "duplicate_approval_logic",
            "type": SlimmingType.DUPLICATED_LOGIC,
            "module": "ergonomics/approval_intelligence.py + trust/governance_pressure.py",
            "description": "Approval logic spread across 2 modules",
            "loc_saved": 35,
            "safe": True,
        },
        {
            "name": "duplicate_visibility_enums",
            "type": SlimmingType.DUPLICATED_LOGIC,
            "module": "trust/transparency_contracts.py + trust/visibility_guarantees.py + compression/interaction_minimalism.py",
            "description": "VisibilityAction, GuaranteeLevel, InteractionPriority overlap",
            "loc_saved": 45,
            "safe": True,
        },
    ]

    def __init__(self, current_loc: int = 14715) -> None:
        self._items: dict[str, SlimmingItem] = {}
        self._current_loc = current_loc
        self._register_items()

    def _register_items(self) -> None:
        """Register known slimming opportunities."""
        for data in self.KNOWN_SLIMMING:
            item = SlimmingItem(
                name=data["name"],
                slimming_type=data["type"],
                module=data["module"],
                description=data["description"],
                estimated_loc_saved=data["loc_saved"],
                safe_to_remove=data.get("safe", False),
            )
            self._items[item.name] = item

    def generate_report(self) -> SlimmingReport:
        """Generate slimming report."""
        items = list(self._items.values())
        total_saved = sum(i.estimated_loc_saved for i in items if not i.applied)
        return SlimmingReport(
            items=items,
            total_loc_saved=total_saved,
            current_loc=self._current_loc,
        )

    def apply_slimming(self, name: str) -> bool:
        """Apply a slimming item."""
        item = self._items.get(name)
        if item and item.safe_to_remove:
            item.applied = True
            self._current_loc -= item.estimated_loc_saved
            return True
        return False

    @property
    def total_items(self) -> int:
        return len(self._items)

    @property
    def total_potential_savings(self) -> int:
        return sum(i.estimated_loc_saved for i in self._items.values())
