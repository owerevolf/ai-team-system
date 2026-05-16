"""
P6 — Cognitive Load Protection (Phase 9)

Prevents governance from becoming bureaucracy.
Adaptive detail levels based on user mode.

Key principle: hide noise, show signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class DetailLevel(Enum):
    BEGINNER = "beginner"    # Guided explanations, simplified recovery
    ADVANCED = "advanced"    # Raw traces, graph details
    EXPERT = "expert"        # Direct runtime control, low-level debugging


@dataclass
class DisplayFilter:
    """Filters what the user sees based on detail level."""
    show_approvals: bool = True
    show_traces: bool = False
    show_graphs: bool = False
    show_validation_internals: bool = False
    show_governance_details: bool = False
    show_raw_errors: bool = False
    show_recovery_options: bool = True
    show_educational_overlays: bool = True
    max_items_per_panel: int = 10
    group_similar: bool = True
    compress_workflows: bool = True

    @classmethod
    def for_level(cls, level: DetailLevel) -> "DisplayFilter":
        if level == DetailLevel.BEGINNER:
            return cls(
                show_approvals=True, show_traces=False, show_graphs=False,
                show_validation_internals=False, show_governance_details=False,
                show_raw_errors=False, show_recovery_options=True,
                show_educational_overlays=True, max_items_per_panel=5,
                group_similar=True, compress_workflows=True,
            )
        elif level == DetailLevel.ADVANCED:
            return cls(
                show_approvals=True, show_traces=True, show_graphs=True,
                show_validation_internals=True, show_governance_details=False,
                show_raw_errors=True, show_recovery_options=True,
                show_educational_overlays=False, max_items_per_panel=20,
                group_similar=True, compress_workflows=False,
            )
        else:  # EXPERT
            return cls(
                show_approvals=True, show_traces=True, show_graphs=True,
                show_validation_internals=True, show_governance_details=True,
                show_raw_errors=True, show_recovery_options=True,
                show_educational_overlays=False, max_items_per_panel=50,
                group_similar=False, compress_workflows=False,
            )


class CognitiveLoadProtector:
    """
    Protects users from information overload.

    Usage:
        protector = CognitiveLoadProtector(DetailLevel.BEGINNER)
        filtered = protector.filter_approvals(all_approvals)
        filtered = protector.filter_timeline(all_events)
    """

    def __init__(self, detail_level: DetailLevel = DetailLevel.BEGINNER) -> None:
        self.detail_level = detail_level
        self._filter = DisplayFilter.for_level(detail_level)

    def set_level(self, level: DetailLevel) -> None:
        """Change the detail level."""
        self.detail_level = level
        self._filter = DisplayFilter.for_level(level)

    def filter_items(
        self,
        items: list[dict[str, Any]],
        item_type: str = "generic",
    ) -> list[dict[str, Any]]:
        """Filter a list of items based on current detail level."""
        max_items = self._filter.max_items_per_panel

        if self._filter.group_similar:
            items = self._group_similar(items)

        if len(items) > max_items:
            # Keep most important items
            items = items[:max_items]

        return items

    def _group_similar(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Group similar items to reduce noise."""
        if not items:
            return items
        # Simple grouping: if > 3 items of same type, group them
        by_type: dict[str, list] = {}
        for item in items:
            t = item.get("type", "unknown")
            by_type.setdefault(t, []).append(item)

        result = []
        for t, group in by_type.items():
            if len(group) > 3:
                result.append({
                    "type": t,
                    "grouped": True,
                    "count": len(group),
                    "items": group[:3],  # Show first 3 as examples
                })
            else:
                result.extend(group)
        return result

    def should_show(self, element: str) -> bool:
        """Check if a UI element should be shown at current detail level."""
        mapping = {
            "approvals": self._filter.show_approvals,
            "traces": self._filter.show_traces,
            "graphs": self._filter.show_graphs,
            "validation_internals": self._filter.show_validation_internals,
            "governance_details": self._filter.show_governance_details,
            "raw_errors": self._filter.show_raw_errors,
            "recovery_options": self._filter.show_recovery_options,
            "educational_overlays": self._filter.show_educational_overlays,
        }
        return mapping.get(element, True)

    def get_filter(self) -> dict[str, Any]:
        """Get current filter configuration."""
        return {
            "detail_level": self.detail_level.value,
            "max_items_per_panel": self._filter.max_items_per_panel,
            "group_similar": self._filter.group_similar,
            "compress_workflows": self._filter.compress_workflows,
            "visible_elements": [k for k, v in {
                "approvals": self._filter.show_approvals,
                "traces": self._filter.show_traces,
                "graphs": self._filter.show_graphs,
                "validation_internals": self._filter.show_validation_internals,
                "governance_details": self._filter.show_governance_details,
                "raw_errors": self._filter.show_raw_errors,
                "recovery_options": self._filter.show_recovery_options,
                "educational_overlays": self._filter.show_educational_overlays,
            }.items() if v],
        }
