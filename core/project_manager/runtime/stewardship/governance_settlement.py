"""
Phase 18, P3: Governance Settlement Review

Reviews governance to find minimal sufficient set.
Removes ceremonial and redundant governance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GovernanceEssentiality(Enum):
    ESSENTIAL = "essential"
    IMPORTANT = "important"
    CEREMONIAL = "ceremonial"
    REDUNDANT = "redundant"


@dataclass
class GovernanceItem:
    name: str
    essentiality: GovernanceEssentiality
    module: str
    description: str
    protects: str
    can_remove: bool = False


class GovernanceSettlementReview:
    ITEMS: list[dict] = [
        {
            "name": "CRITICAL risk approval",
            "essentiality": GovernanceEssentiality.ESSENTIAL,
            "module": "ergonomics/approval_intelligence",
            "description": "CRITICAL risk changes require human approval",
            "protects": "Prevents irreversible damage",
            "can_remove": False,
        },
        {
            "name": "LOW risk confirmation dialog",
            "essentiality": GovernanceEssentiality.CEREMONIAL,
            "module": "ergonomics/approval_intelligence",
            "description": "LOW risk changes show confirmation dialog",
            "protects": "Nothing — contributors click through",
            "can_remove": True,
        },
        {
            "name": "Plugin capability enforcement",
            "essentiality": GovernanceEssentiality.ESSENTIAL,
            "module": "durability/plugin_boundaries",
            "description": "Plugins cannot bypass approvals or modify core",
            "protects": "Prevents shadow runtime",
            "can_remove": False,
        },
        {
            "name": "Audit trail for automation",
            "essentiality": GovernanceEssentiality.ESSENTIAL,
            "module": "trust/audit_visible_automation",
            "description": "All automated actions must have audit trail",
            "protects": "Trust and accountability",
            "can_remove": False,
        },
        {
            "name": "Plugin registration 5-step approval",
            "essentiality": GovernanceEssentiality.REDUNDANT,
            "module": "ecosystem/plugin_governance",
            "description": "Plugin registration requires 5 approval steps",
            "protects": "Nothing — contributors bypass with scripts",
            "can_remove": True,
        },
        {
            "name": "Context validation on read + GC",
            "essentiality": GovernanceEssentiality.REDUNDANT,
            "module": "durability/context_gc",
            "description": "Context validated both on read and during GC",
            "protects": "Minimal — double validation",
            "can_remove": True,
        },
    ]

    def __init__(self) -> None:
        self._items: dict[str, GovernanceItem] = {}
        for data in self.ITEMS:
            self._items[data["name"]] = GovernanceItem(
                name=data["name"], essentiality=data["essentiality"],
                module=data["module"], description=data["description"],
                protects=data["protects"], can_remove=data.get("can_remove", False),
            )

    def get_removable(self) -> list[GovernanceItem]:
        return [i for i in self._items.values() if i.can_remove]

    def get_essential(self) -> list[GovernanceItem]:
        return [i for i in self._items.values() if i.essentiality == GovernanceEssentiality.ESSENTIAL]

    @property
    def total_items(self) -> int:
        return len(self._items)
