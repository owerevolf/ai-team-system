"""
Phase 18, P2: API & Semantic Settlement

Long-term stable contracts for core semantics.
Stability levels: EXPERIMENTAL → EVOLVING → STABLE → FROZEN
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StabilityLevel(Enum):
    EXPERIMENTAL = "experimental"
    EVOLVING = "evolving"
    STABLE = "stable"
    FROZEN = "frozen"


@dataclass
class SemanticContract:
    name: str
    stability: StabilityLevel
    description: str
    module: str
    invariants: list[str] = field(default_factory=list)
    change_requires: list[str] = field(default_factory=list)


class APISemanticSettlement:
    CONTRACTS: dict[str, dict] = {
        "approval_semantics": {
            "stability": StabilityLevel.FROZEN,
            "description": "What requires approval vs auto-apply",
            "module": "ergonomics/approval_intelligence",
            "invariants": ["CRITICAL always requires human approval", "LOW can auto-apply with audit"],
            "change_requires": ["architect", "safety_reviewer", "team_lead"],
        },
        "visibility_guarantees": {
            "stability": StabilityLevel.FROZEN,
            "description": "What must always be visible",
            "module": "trust/visibility_guarantees",
            "invariants": ["CRITICAL_FAILURE always visible", "Safety events cannot be suppressed"],
            "change_requires": ["architect", "safety_reviewer"],
        },
        "recovery_contracts": {
            "stability": StabilityLevel.FROZEN,
            "description": "Recovery must be deterministic and auditable",
            "module": "durability/recovery_engine",
            "invariants": ["Recovery is deterministic", "All recovery actions auditable"],
            "change_requires": ["architect", "safety_reviewer"],
        },
        "plugin_capabilities": {
            "stability": StabilityLevel.STABLE,
            "description": "What plugins can and cannot do",
            "module": "durability/plugin_boundaries",
            "invariants": ["Plugins cannot bypass approvals", "Plugins cannot modify PM core"],
            "change_requires": ["architect"],
        },
        "canonical_vocabulary": {
            "stability": StabilityLevel.STABLE,
            "description": "Shared concept definitions",
            "module": "coherence/vocabulary",
            "invariants": ["All subsystems use canonical definitions"],
            "change_requires": ["architect"],
        },
        "audit_format": {
            "stability": StabilityLevel.FROZEN,
            "description": "Audit trail format and integrity",
            "module": "trust/audit_visible_automation",
            "invariants": ["All automated actions audited", "Audit logs cannot be deleted"],
            "change_requires": ["architect", "safety_reviewer"],
        },
    }

    def __init__(self) -> None:
        self._contracts: dict[str, SemanticContract] = {}
        for name, data in self.CONTRACTS.items():
            self._contracts[name] = SemanticContract(
                name=name, stability=data["stability"], description=data["description"],
                module=data["module"], invariants=data.get("invariants", []),
                change_requires=data.get("change_requires", []),
            )

    def get_contract(self, name: str) -> Optional[SemanticContract]:
        return self._contracts.get(name)

    def check_change_allowed(self, contract: str, approvers: list[str]) -> tuple[bool, str]:
        c = self._contracts.get(contract)
        if not c:
            return True, f"Contract '{contract}' not found"
        if c.stability in (StabilityLevel.EXPERIMENTAL, StabilityLevel.EVOLVING):
            return True, f"{c.stability.value} — changes allowed"
        missing = set(c.change_requires) - set(approvers)
        if missing:
            return False, f"Requires: {', '.join(missing)}"
        return True, "Approved"

    @property
    def total_contracts(self) -> int:
        return len(self._contracts)
