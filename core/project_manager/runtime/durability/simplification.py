"""
P10 — Runtime Simplification Initiative (Phase 9)

Meta-subsystem: every subsystem must justify its existence.

If a subsystem can't answer:
  - Why is it needed?
  - How do you debug it?
  - How do you repair it?
  - How does it degrade?

Then it's dangerous and should be simplified or removed.

Integrates with existing governance/simplification.py — extends it
with runtime-level simplification decisions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class SubsystemRisk(Enum):
    LOW = "low"           # Simple, well-understood, easy to debug
    MEDIUM = "medium"     # Some complexity, documented
    HIGH = "high"         # Complex, needs attention
    DANGEROUS = "dangerous"  # Unclear purpose or unmaintainable


@dataclass
class SubsystemHealth:
    """Health assessment of a subsystem."""
    name: str
    purpose: str = ""
    debuggable: bool = True
    repairable: bool = True
    has_documentation: bool = True
    usage_count: int = 0
    last_used: float = 0.0
    error_count: int = 0
    risk_level: SubsystemRisk = SubsystemRisk.LOW
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "debuggable": self.debuggable,
            "repairable": self.repairable,
            "has_documentation": self.has_documentation,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
            "error_count": self.error_count,
            "risk_level": self.risk_level.value,
            "recommendations": self.recommendations,
        }


class RuntimeSimplification:
    """
    Evaluates and simplifies runtime subsystems.

    Usage:
        simpl = RuntimeSimplification()
        simpl.register_subsystem("my_module", purpose="Handles X", usage_count=5)
        report = simpl.evaluate_all()
        simpl.run_simplification()
    """

    def __init__(self) -> None:
        self._subsystems: dict[str, SubsystemHealth] = {}

    def register_subsystem(
        self,
        name: str,
        purpose: str = "",
        debuggable: bool = True,
        repairable: bool = True,
        has_documentation: bool = True,
    ) -> SubsystemHealth:
        """Register a subsystem for evaluation."""
        health = SubsystemHealth(
            name=name,
            purpose=purpose,
            debuggable=debuggable,
            repairable=repairable,
            has_documentation=has_documentation,
        )
        self._subsystems[name] = health
        return health

    def record_usage(self, name: str) -> None:
        """Record that a subsystem was used."""
        ss = self._subsystems.get(name)
        if ss:
            ss.usage_count += 1
            ss.last_used = time.time()

    def record_error(self, name: str) -> None:
        """Record an error in a subsystem."""
        ss = self._subsystems.get(name)
        if ss:
            ss.error_count += 1

    def evaluate(self, name: str) -> SubsystemHealth:
        """Evaluate a single subsystem."""
        ss = self._subsystems.get(name)
        if not ss:
            return SubsystemHealth(name=name, risk_level=SubsystemRisk.DANGEROUS)

        ss.recommendations = []

        # Check purpose
        if not ss.purpose:
            ss.recommendations.append("No purpose documented — why does this exist?")
            ss.risk_level = SubsystemRisk.HIGH

        # Check debuggability
        if not ss.debuggable:
            ss.recommendations.append("Not debuggable — how do you diagnose issues?")
            ss.risk_level = SubsystemRisk.DANGEROUS

        # Check repairability
        if not ss.repairable:
            ss.recommendations.append("Not repairable — what happens when it breaks?")
            ss.risk_level = SubsystemRisk.DANGEROUS

        # Check documentation
        if not ss.has_documentation:
            ss.recommendations.append("No documentation — how do you use it?")
            if ss.risk_level == SubsystemRisk.LOW:
                ss.risk_level = SubsystemRisk.MEDIUM

        # Check usage
        if ss.usage_count == 0:
            ss.recommendations.append("Never used — can it be removed?")
            if ss.risk_level == SubsystemRisk.LOW:
                ss.risk_level = SubsystemRisk.MEDIUM

        # Check error rate
        if ss.error_count > 10:
            ss.recommendations.append(f"High error count ({ss.error_count}) — needs attention")
            if ss.risk_level.value in ("low", "medium"):
                ss.risk_level = SubsystemRisk.HIGH

        # Check staleness (not used in 90 days)
        if ss.last_used > 0 and (time.time() - ss.last_used) > 7776000:
            ss.recommendations.append("Not used in 90+ days — can it be archived?")
            if ss.risk_level == SubsystemRisk.LOW:
                ss.risk_level = SubsystemRisk.MEDIUM

        if not ss.recommendations:
            ss.recommendations.append("Healthy — no action needed")

        return ss

    def evaluate_all(self) -> dict[str, Any]:
        """Evaluate all registered subsystems."""
        results = {}
        for name in self._subsystems:
            results[name] = self.evaluate(name).to_dict()

        total = len(results)
        by_risk: dict[str, int] = {}
        for r in results.values():
            risk = r["risk_level"]
            by_risk[risk] = by_risk.get(risk, 0) + 1

        return {
            "total_subsystems": total,
            "by_risk": by_risk,
            "subsystems": results,
        }

    def get_removable_candidates(self) -> list[dict[str, Any]]:
        """Get subsystems that are candidates for removal."""
        candidates = []
        for name, ss in self._subsystems.items():
            eval_ss = self.evaluate(name)
            if eval_ss.risk_level in (SubsystemRisk.HIGH, SubsystemRisk.DANGEROUS):
                if ss.usage_count == 0 or not ss.purpose:
                    candidates.append({
                        "name": name,
                        "reason": "Never used or no documented purpose",
                        "risk": eval_ss.risk_level.value,
                        "recommendations": eval_ss.recommendations,
                    })
        return candidates

    def get_simplification_report(self) -> dict[str, Any]:
        """Get a full simplification report."""
        evaluation = self.evaluate_all()
        removable = self.get_removable_candidates()

        return {
            "evaluation": evaluation,
            "removable_candidates": removable,
            "total_recommendations": sum(
                len(r.get("recommendations", []))
                for r in evaluation.get("subsystems", {}).values()
            ),
        }
