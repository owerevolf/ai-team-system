"""
Phase 16, P7: Architectural Freeze Review

Determines what is "done enough" — what should transition from
endless experimentation to stable infrastructure.

Principle: Architecture must settle eventually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SettlementStatus(Enum):
    EXPERIMENTAL = "experimental"      # Still exploring
    STABILIZING = "stabilizing"        # Converging on design
    SETTLED = "settled"                # Design is stable
    FROZEN = "frozen"                  # Should not change


@dataclass
class SubsystemSettlement:
    """Settlement status of a subsystem."""
    name: str
    status: SettlementStatus
    description: str
    settled_concepts: list[str] = field(default_factory=list)
    still_experimental: list[str] = field(default_factory=list)
    recommendation: str = ""


class ArchitecturalFreezeReview:
    """
    Reviews which subsystems/concepts are "done enough" and should be frozen.
    Prevents endless experimentation.
    """

    SUBSYSTEM_SETTLEMENTS: dict[str, dict] = {
        "durability": {
            "status": SettlementStatus.SETTLED,
            "description": "Recovery, state lifecycle, GC are stable",
            "settled": ["state_lifecycle", "recovery_engine", "context_gc", "chaos_testing"],
            "experimental": ["large_repo_survival"],
            "recommendation": "Freeze state_lifecycle and recovery_engine. large_repo can still evolve.",
        },
        "ergonomics": {
            "status": SettlementStatus.SETTLED,
            "description": "Attention, calm mode, approval intelligence are stable",
            "settled": ["attention_management", "calm_mode", "approval_intelligence", "human_time_protection"],
            "experimental": ["intent_centric_ux"],
            "recommendation": "Freeze attention and calm mode. intent_centric can still evolve.",
        },
        "trust": {
            "status": SettlementStatus.STABILIZING,
            "description": "Visibility and personality are stable, drift detection still evolving",
            "settled": ["visibility_guarantees", "predictable_personality", "transparency_contracts"],
            "experimental": ["trust_drift_detection", "adaptation_inspector"],
            "recommendation": "Freeze visibility and personality. drift detection needs more data.",
        },
        "compression": {
            "status": SettlementStatus.SETTLED,
            "description": "Surface audit, do_less, interaction minimalism are stable",
            "settled": ["do_less", "interaction_minimalism", "operational_calm", "workflow_compression"],
            "experimental": ["progressive_disclosure"],
            "recommendation": "Freeze do_less and interaction_minimalism. disclosure can still evolve.",
        },
        "coherence": {
            "status": SettlementStatus.STABILIZING,
            "description": "Vocabulary is stable, drift detection still evolving",
            "settled": ["vocabulary", "boundary_enforcement"],
            "experimental": ["ontology_drift", "dependency_gravity"],
            "recommendation": "Freeze vocabulary. drift detection needs more data.",
        },
        "ecosystem": {
            "status": SettlementStatus.EXPERIMENTAL,
            "description": "Ecosystem concepts are still being explored",
            "settled": ["onboarding", "plugin_governance"],
            "experimental": ["fork_drift", "ecosystem_coherence", "succession"],
            "recommendation": "Freeze onboarding and plugin_governance. Others still experimental.",
        },
    }

    def __init__(self) -> None:
        self._subsystems: dict[str, SubsystemSettlement] = {}
        self._register_settlements()

    def _register_settlements(self) -> None:
        """Register subsystem settlements."""
        for name, data in self.SUBSYSTEM_SETTLEMENTS.items():
            self._subsystems[name] = SubsystemSettlement(
                name=name,
                status=data["status"],
                description=data["description"],
                settled_concepts=data.get("settled", []),
                still_experimental=data.get("experimental", []),
                recommendation=data.get("recommendation", ""),
            )

    def get_settlement(self, name: str) -> Optional[SubsystemSettlement]:
        """Get settlement status for a subsystem."""
        return self._subsystems.get(name)

    def get_settled_subsystems(self) -> list[SubsystemSettlement]:
        """Get all settled subsystems."""
        return [s for s in self._subsystems.values() if s.status == SettlementStatus.SETTLED]

    def get_experimental_subsystems(self) -> list[SubsystemSettlement]:
        """Get all experimental subsystems."""
        return [s for s in self._subsystems.values() if s.status == SettlementStatus.EXPERIMENTAL]

    def should_freeze(self, concept: str) -> tuple[bool, str]:
        """Check if a concept should be frozen."""
        for name, settlement in self._subsystems.items():
            if concept in settlement.settled_concepts:
                return True, f"'{concept}' in '{name}' is settled and should be frozen"
            if concept in settlement.still_experimental:
                return False, f"'{concept}' in '{name}' is still experimental"
        return False, f"'{concept}' not found in any subsystem"

    @property
    def total_subsystems(self) -> int:
        return len(self._subsystems)
