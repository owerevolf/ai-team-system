"""
P10 — Simplicity Preservation Layer (Phase 11)

Every subsystem must justify its existence. Complexity budget system:
operational cost, cognitive cost, maintenance cost, observability cost.

Key principle: after 11 phases, the main risk is architectural obesity.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class CostType(Enum):
    OPERATIONAL = "operational"     # Runtime overhead
    COGNITIVE = "cognitive"         # User understanding cost
    MAINTENANCE = "maintenance"     # Code complexity
    OBSERVABILITY = "observability" # Debugging/diagnostic cost


class ComplexityTier(Enum):
    ESSENTIAL = "essential"         # Core runtime, cannot be removed
    IMPORTANT = "important"         # Significant value, high removal cost
    SUPPLEMENTARY = "supplementary" # Nice to have, moderate removal cost
    EXPENDABLE = "expendable"       # Low value, easy to remove


@dataclass
class SubsystemCost:
    """Cost assessment of a subsystem."""
    name: str
    tier: ComplexityTier
    operational_cost: float = 0.0   # 0-10
    cognitive_cost: float = 0.0     # 0-10
    maintenance_cost: float = 0.0   # 0-10
    observability_cost: float = 0.0 # 0-10
    purpose: str = ""
    usage_count: int = 0
    last_used: float = 0.0
    dependencies: list[str] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return self.operational_cost + self.cognitive_cost + self.maintenance_cost + self.observability_cost

    @property
    def cost_per_value(self) -> float:
        """Cost relative to tier value. Lower is better."""
        tier_value = {
            ComplexityTier.ESSENTIAL: 10.0,
            ComplexityTier.IMPORTANT: 7.0,
            ComplexityTier.SUPPLEMENTARY: 4.0,
            ComplexityTier.EXPENDABLE: 1.0,
        }
        value = tier_value.get(self.tier, 1.0)
        return self.total_cost / value if value > 0 else float('inf')

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier.value,
            "operational_cost": self.operational_cost,
            "cognitive_cost": self.cognitive_cost,
            "maintenance_cost": self.maintenance_cost,
            "observability_cost": self.observability_cost,
            "total_cost": self.total_cost,
            "cost_per_value": round(self.cost_per_value, 2),
            "purpose": self.purpose,
            "usage_count": self.usage_count,
            "dependencies": self.dependencies,
        }


@dataclass
class ComplexityBudget:
    """Complexity budget limits."""
    max_total_cost: float = 200.0
    max_operational: float = 60.0
    max_cognitive: float = 50.0
    max_maintenance: float = 50.0
    max_observability: float = 40.0
    max_subsystems: int = 50

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_total_cost": self.max_total_cost,
            "max_operational": self.max_operational,
            "max_cognitive": self.max_cognitive,
            "max_maintenance": self.max_maintenance,
            "max_observability": self.max_observability,
            "max_subsystems": self.max_subsystems,
        }


class SimplicityPreservation:
    """
    Evaluates and preserves simplicity. Complexity budget system.

    Usage:
        simp = SimplicityPreservation()
        simp.register_subsystem("my_module", ComplexityTier.IMPORTANT,
                                operational_cost=2, cognitive_cost=3,
                                purpose="Handles X")
        report = simp.get_complexity_report()
        candidates = simp.get_removal_candidates()
    """

    def __init__(self, budget: Optional[ComplexityBudget] = None) -> None:
        self._budget = budget or ComplexityBudget()
        self._subsystems: dict[str, SubsystemCost] = {}

    def register_subsystem(self, name: str, tier: ComplexityTier,
                           operational_cost: float = 0, cognitive_cost: float = 0,
                           maintenance_cost: float = 0, observability_cost: float = 0,
                           purpose: str = "", dependencies: Optional[list[str]] = None) -> SubsystemCost:
        """Register a subsystem for complexity tracking."""
        cost = SubsystemCost(
            name=name,
            tier=tier,
            operational_cost=operational_cost,
            cognitive_cost=cognitive_cost,
            maintenance_cost=maintenance_cost,
            observability_cost=observability_cost,
            purpose=purpose,
            dependencies=dependencies or [],
        )
        self._subsystems[name] = cost
        return cost

    def record_usage(self, name: str) -> None:
        """Record that a subsystem was used."""
        ss = self._subsystems.get(name)
        if ss:
            ss.usage_count += 1
            ss.last_used = time.time()

    def get_complexity_report(self) -> dict[str, Any]:
        """Get full complexity report."""
        total_cost = 0.0
        total_op = 0.0
        total_cog = 0.0
        total_maint = 0.0
        total_obs = 0.0
        by_tier: dict[str, int] = {}

        for ss in self._subsystems.values():
            total_cost += ss.total_cost
            total_op += ss.operational_cost
            total_cog += ss.cognitive_cost
            total_maint += ss.maintenance_cost
            total_obs += ss.observability_cost
            t = ss.tier.value
            by_tier[t] = by_tier.get(t, 0) + 1

        return {
            "total_subsystems": len(self._subsystems),
            "total_cost": round(total_cost, 1),
            "budget": self._budget.to_dict(),
            "by_tier": by_tier,
            "cost_breakdown": {
                "operational": round(total_op, 1),
                "cognitive": round(total_cog, 1),
                "maintenance": round(total_maint, 1),
                "observability": round(total_obs, 1),
            },
            "budget_status": {
                "total": "OK" if total_cost <= self._budget.max_total_cost else "OVER",
                "operational": "OK" if total_op <= self._budget.max_operational else "OVER",
                "cognitive": "OK" if total_cog <= self._budget.max_cognitive else "OVER",
                "maintenance": "OK" if total_maint <= self._budget.max_maintenance else "OVER",
                "observability": "OK" if total_obs <= self._budget.max_observability else "OVER",
                "subsystems": "OK" if len(self._subsystems) <= self._budget.max_subsystems else "OVER",
            },
            "is_healthy": total_cost <= self._budget.max_total_cost,
        }

    def get_removal_candidates(self) -> list[dict[str, Any]]:
        """Get subsystems that are candidates for removal."""
        candidates = []
        for name, ss in self._subsystems.items():
            if ss.tier == ComplexityTier.EXPENDABLE:
                candidates.append({
                    "name": name,
                    "reason": "Expendable tier",
                    "cost": ss.total_cost,
                    "cost_per_value": round(ss.cost_per_value, 2),
                })
            elif ss.tier == ComplexityTier.SUPPLEMENTARY and ss.usage_count == 0:
                candidates.append({
                    "name": name,
                    "reason": "Supplementary and never used",
                    "cost": ss.total_cost,
                    "cost_per_value": round(ss.cost_per_value, 2),
                })
            elif ss.cost_per_value > 3.0:
                candidates.append({
                    "name": name,
                    "reason": f"High cost-per-value ratio ({ss.cost_per_value:.1f})",
                    "cost": ss.total_cost,
                    "cost_per_value": round(ss.cost_per_value, 2),
                })
        candidates.sort(key=lambda c: c["cost_per_value"], reverse=True)
        return candidates

    def get_subsystem_cost(self, name: str) -> Optional[SubsystemCost]:
        """Get cost info for a specific subsystem."""
        return self._subsystems.get(name)

    def get_all_subsystems(self) -> list[dict[str, Any]]:
        """Get all subsystems sorted by cost-per-value."""
        return sorted(
            [ss.to_dict() for ss in self._subsystems.values()],
            key=lambda s: s["cost_per_value"],
            reverse=True,
        )
