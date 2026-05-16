"""
Phase 18, P1: Subsystem Retirement Framework

Controlled subsystem retirement:
- archive subsystem
- deprecate workflow
- merge runtime responsibility
- remove ceremonial logic

Retirement must be: reversible, observable, governance-aware.

Principle: Deletion is normalized maintenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RetirementStatus(Enum):
    ACTIVE = "active"              # Fully operational
    DEPRECATED = "deprecated"      # Still works, but marked for removal
    ARCHIVED = "archived"          # Code preserved, not active
    MERGED = "merged"              # Merged into another module
    REMOVED = "removed"            # Deleted


class RetirementReason(Enum):
    OBSOLETE = "obsolete"          # No longer needed
    OVERLAPPING = "overlapping"    # Duplicates another subsystem
    CEREMONIAL = "ceremonial"      # Adds no value
    EXPENSIVE = "expensive"        # Too costly for its value
    MERGED = "merged"              # Merged into another subsystem


@dataclass
class RetirementCandidate:
    """A candidate for retirement."""
    module: str
    status: RetirementStatus
    reason: RetirementReason
    description: str
    replacement: str = ""          # What replaces this
    safe_to_retire: bool = False
    loc_saved: int = 0
    dependencies: list[str] = field(default_factory=list)


@dataclass
class RetirementReport:
    """Full retirement report."""
    candidates: list[RetirementCandidate] = field(default_factory=list)
    total_loc_saved: int = 0

    @property
    def safe_to_retire(self) -> list[RetirementCandidate]:
        return [c for c in self.candidates if c.safe_to_retire]

    @property
    def deprecated(self) -> list[RetirementCandidate]:
        return [c for c in self.candidates if c.status == RetirementStatus.DEPRECATED]


class SubsystemRetirementFramework:
    """
    Manages controlled subsystem retirement.
    Makes deletion a first-class, reversible operation.
    """

    # Known retirement candidates from Phase 18 audit
    CANDIDATES: list[dict] = [
        {
            "module": "stabilization/slimming.py",
            "status": RetirementStatus.ACTIVE,
            "reason": RetirementReason.OVERLAPPING,
            "description": "Overlaps with stabilization/consolidation.py — merge into one",
            "replacement": "stabilization/consolidation.py",
            "safe": True,
            "loc_saved": 200,
            "deps": [],
        },
        {
            "module": "reality/long_run_sessions.py",
            "status": RetirementStatus.ACTIVE,
            "reason": RetirementReason.OVERLAPPING,
            "description": "Overlaps with stabilization/hardening.py — merge into one",
            "replacement": "stabilization/hardening.py",
            "safe": True,
            "loc_saved": 250,
            "deps": [],
        },
        {
            "module": "reality/plugin_stress.py",
            "status": RetirementStatus.ACTIVE,
            "reason": RetirementReason.OVERLAPPING,
            "description": "Overlaps with ecosystem/plugin_governance.py — merge",
            "replacement": "ecosystem/plugin_governance.py",
            "safe": True,
            "loc_saved": 150,
            "deps": [],
        },
        {
            "module": "reality/repo_diversity.py",
            "status": RetirementStatus.ACTIVE,
            "reason": RetirementReason.OVERLAPPING,
            "description": "Overlaps with durability/large_repo.py — merge",
            "replacement": "durability/large_repo.py",
            "safe": True,
            "loc_saved": 180,
            "deps": [],
        },
        {
            "module": "reality/remaining.py",
            "status": RetirementStatus.ACTIVE,
            "reason": RetirementReason.CEREMONIAL,
            "description": "Contains P5-P10 that could be distributed to existing modules",
            "replacement": "distributed to existing modules",
            "safe": False,  # Needs careful review
            "loc_saved": 800,
            "deps": [],
        },
    ]

    def __init__(self) -> None:
        self._candidates: dict[str, RetirementCandidate] = {}
        self._register_candidates()

    def _register_candidates(self) -> None:
        """Register retirement candidates."""
        for data in self.CANDIDATES:
            candidate = RetirementCandidate(
                module=data["module"],
                status=data["status"],
                reason=data["reason"],
                description=data["description"],
                replacement=data.get("replacement", ""),
                safe_to_retire=data.get("safe", False),
                loc_saved=data.get("loc_saved", 0),
                dependencies=data.get("deps", []),
            )
            self._candidates[candidate.module] = candidate

    def generate_report(self) -> RetirementReport:
        """Generate retirement report."""
        candidates = list(self._candidates.values())
        total_saved = sum(c.loc_saved for c in candidates if c.safe_to_retire)
        return RetirementReport(candidates=candidates, total_loc_saved=total_saved)

    def get_candidate(self, module: str) -> Optional[RetirementCandidate]:
        """Get a retirement candidate by module."""
        return self._candidates.get(module)

    def mark_deprecated(self, module: str) -> bool:
        """Mark a module as deprecated."""
        candidate = self._candidates.get(module)
        if candidate and candidate.safe_to_retire:
            candidate.status = RetirementStatus.DEPRECATED
            return True
        return False

    def mark_merged(self, module: str, target: str) -> bool:
        """Mark a module as merged into another."""
        candidate = self._candidates.get(module)
        if candidate and candidate.safe_to_retire:
            candidate.status = RetirementStatus.MERGED
            candidate.replacement = target
            return True
        return False

    @property
    def total_candidates(self) -> int:
        return len(self._candidates)

    @property
    def total_safe_savings(self) -> int:
        return sum(c.loc_saved for c in self._candidates.values() if c.safe_to_retire)
