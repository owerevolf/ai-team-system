"""
Phase 12, P3: Governance Simplification

Detects governance entropy:
- overlapping rules
- unused policies
- contradictory approvals
- redundant validations
- dead governance paths

Principle: Sometimes removing governance is more correct than adding it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GovernanceType(Enum):
    APPROVAL_RULE = "approval_rule"
    VALIDATION_RULE = "validation_rule"
    POLICY = "policy"
    CONSTRAINT = "constraint"
    THRESHOLD = "threshold"


class GovernanceHealth(Enum):
    ACTIVE = "active"
    OVERLAPPING = "overlapping"
    UNUSED = "unused"
    CONTRADICTORY = "contradictory"
    REDUNDANT = "redundant"
    DEAD = "dead"


@dataclass
class GovernanceItem:
    """A single governance rule, policy, or constraint."""
    name: str
    governance_type: GovernanceType
    module: str
    description: str = ""
    health: GovernanceHealth = GovernanceHealth.ACTIVE
    overlaps_with: list[str] = field(default_factory=list)
    contradicts_with: list[str] = field(default_factory=list)
    usage_estimate: int = 0  # 0 = unknown/untracked
    is_enforced: bool = True  # False = advisory only


@dataclass
class GovernanceSimplificationReport:
    """Report of governance simplification analysis."""
    total_items: int = 0
    active_items: int = 0
    overlapping_items: list[GovernanceItem] = field(default_factory=list)
    unused_items: list[GovernanceItem] = field(default_factory=list)
    contradictory_pairs: list[tuple[str, str]] = field(default_factory=list)
    redundant_items: list[GovernanceItem] = field(default_factory=list)
    dead_items: list[GovernanceItem] = field(default_factory=list)
    advisory_not_enforced: list[GovernanceItem] = field(default_factory=list)

    @property
    def removable_count(self) -> int:
        return (
            len(self.unused_items)
            + len(self.redundant_items)
            + len(self.dead_items)
        )

    @property
    def governance_density(self) -> float:
        """Governance items per module — high density suggests over-governance."""
        modules: set[str] = set()
        for item in self.overlapping_items + self.unused_items + self.redundant_items + self.dead_items:
            modules.add(item.module)
        if not modules:
            return 0.0
        return self.removable_count / len(modules)


class GovernanceSimplifier:
    """
    Analyzes governance rules and identifies simplification opportunities.
    Detects entropy: accumulation, contradiction, and dead weight.
    """

    def __init__(self) -> None:
        self._items: dict[str, GovernanceItem] = {}

    def register(self, item: GovernanceItem) -> None:
        """Register a governance item for analysis."""
        self._items[item.name] = item

    def mark_overlap(self, item_a: str, item_b: str) -> None:
        """Mark two governance items as overlapping."""
        if item_a in self._items and item_b in self._items:
            self._items[item_a].overlaps_with.append(item_b)
            self._items[item_b].overlaps_with.append(item_a)
            self._items[item_a].health = GovernanceHealth.OVERLAPPING
            self._items[item_b].health = GovernanceHealth.OVERLAPPING

    def mark_contradiction(self, item_a: str, item_b: str) -> None:
        """Mark two governance items as contradictory."""
        if item_a in self._items and item_b in self._items:
            self._items[item_a].contradicts_with.append(item_b)
            self._items[item_b].contradicts_with.append(item_a)
            self._items[item_a].health = GovernanceHealth.CONTRADICTORY
            self._items[item_b].health = GovernanceHealth.CONTRADICTORY

    def mark_unused(self, item_name: str) -> None:
        """Mark a governance item as unused."""
        if item_name in self._items:
            self._items[item_name].health = GovernanceHealth.UNUSED
            self._items[item_name].usage_estimate = 0

    def mark_dead(self, item_name: str) -> None:
        """Mark a governance item as dead (permanently unreachable)."""
        if item_name in self._items:
            self._items[item_name].health = GovernanceHealth.DEAD

    def analyze(self) -> GovernanceSimplificationReport:
        """Run full governance simplification analysis."""
        report = GovernanceSimplificationReport()
        report.total_items = len(self._items)

        for item in self._items.values():
            if item.health == GovernanceHealth.ACTIVE:
                report.active_items += 1
            elif item.health == GovernanceHealth.OVERLAPPING:
                report.overlapping_items.append(item)
            elif item.health == GovernanceHealth.UNUSED:
                report.unused_items.append(item)
            elif item.health == GovernanceHealth.REDUNDANT:
                report.redundant_items.append(item)
            elif item.health == GovernanceHealth.DEAD:
                report.dead_items.append(item)

            if item.health == GovernanceHealth.CONTRADICTORY:
                for other_name in item.contradicts_with:
                    pair: tuple[str, str] = (item.name, other_name) if item.name < other_name else (other_name, item.name)
                    if pair not in report.contradictory_pairs:
                        report.contradictory_pairs.append(pair)

            if not item.is_enforced:
                report.advisory_not_enforced.append(item)

        return report

    def find_similar_names(self, threshold: float = 0.7) -> list[tuple[str, str, float]]:
        """
        Find governance items with similar names — potential duplicates.
        Uses simple Jaccard similarity on name tokens.
        """
        from itertools import combinations

        results: list[tuple[str, str, float]] = []
        names = list(self._items.keys())

        for a, b in combinations(names, 2):
            tokens_a = set(a.lower().replace("_", " ").split())
            tokens_b = set(b.lower().replace("_", " ").split())
            if not tokens_a or not tokens_b:
                continue
            intersection = tokens_a & tokens_b
            union = tokens_a | tokens_b
            similarity = len(intersection) / len(union)
            if similarity >= threshold:
                results.append((a, b, similarity))

        return sorted(results, key=lambda x: -x[2])
