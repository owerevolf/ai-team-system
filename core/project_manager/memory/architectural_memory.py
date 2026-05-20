"""
architectural_memory.py — Persistent Architecture Understanding.

Stores:
- subsystem roles
- dependency graph summaries
- integration contracts
- architectural decisions
- frozen semantics
- dangerous coupling areas
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class ArchitecturalDecision:
    """An architectural decision record (ADR)."""
    decision_id: str = ""
    title: str = ""
    context: str = ""
    decision: str = ""
    consequences: List[str] = field(default_factory=list)
    affected_subsystems: List[str] = field(default_factory=list)
    date: str = ""
    is_active: bool = True


@dataclass
class IntegrationContract:
    """Integration contract between subsystems."""
    contract_id: str = ""
    subsystem_a: str = ""
    subsystem_b: str = ""
    interface: str = ""
    protocol: str = ""  # REST, function call, event, shared db
    stability: str = "stable"  # stable, evolving, fragile
    notes: str = ""


@dataclass
class DangerousCoupling:
    """A known dangerous coupling."""
    area_a: str = ""
    area_b: str = ""
    risk: str = ""
    mitigation: str = ""
    severity: str = "medium"  # low, medium, high, critical


class ArchitecturalMemory:
    """
    Persistent architecture understanding.
    Stores the architectural decisions and constraints that must be preserved.
    """

    def __init__(self):
        self._decisions: Dict[str, ArchitecturalDecision] = {}
        self._contracts: Dict[str, IntegrationContract] = {}
        self._dangerous_couplings: List[DangerousCoupling] = []
        self._frozen_semantics: Dict[str, str] = {}  # symbol -> semantic meaning
        self._lock = threading.Lock()
        self._last_updated = datetime.utcnow().isoformat() + "Z"

    def add_decision(self, title: str, context: str, decision: str,
                     consequences: Optional[List[str]] = None,
                     affected_subsystems: Optional[List[str]] = None) -> ArchitecturalDecision:
        """Add an architectural decision."""
        with self._lock:
            import uuid
            adr = ArchitecturalDecision(
                decision_id=str(uuid.uuid4())[:8],
                title=title, context=context, decision=decision,
                consequences=consequences or [],
                affected_subsystems=affected_subsystems or [],
                date=datetime.utcnow().isoformat() + "Z",
            )
            self._decisions[adr.decision_id] = adr
            self._touch()
            return adr

    def get_decision(self, decision_id: str) -> Optional[ArchitecturalDecision]:
        """Get a decision by ID."""
        return self._decisions.get(decision_id)

    def get_decisions_for_subsystem(self, subsystem: str) -> List[ArchitecturalDecision]:
        """Get all decisions affecting a subsystem."""
        return [
            d for d in self._decisions.values()
            if subsystem in d.affected_subsystems and d.is_active
        ]

    def get_all_decisions(self) -> List[ArchitecturalDecision]:
        """Get all active decisions."""
        return [d for d in self._decisions.values() if d.is_active]

    def add_contract(self, subsystem_a: str, subsystem_b: str,
                     interface: str, protocol: str = "function call",
                     stability: str = "stable", notes: str = "") -> IntegrationContract:
        """Add an integration contract."""
        with self._lock:
            import uuid
            contract = IntegrationContract(
                contract_id=str(uuid.uuid4())[:8],
                subsystem_a=subsystem_a, subsystem_b=subsystem_b,
                interface=interface, protocol=protocol,
                stability=stability, notes=notes,
            )
            self._contracts[contract.contract_id] = contract
            self._touch()
            return contract

    def get_contracts_for_subsystem(self, subsystem: str) -> List[IntegrationContract]:
        """Get all contracts involving a subsystem."""
        return [
            c for c in self._contracts.values()
            if c.subsystem_a == subsystem or c.subsystem_b == subsystem
        ]

    def add_dangerous_coupling(self, area_a: str, area_b: str,
                                risk: str, mitigation: str = "",
                                severity: str = "medium") -> None:
        """Add a dangerous coupling."""
        with self._lock:
            self._dangerous_couplings.append(DangerousCoupling(
                area_a=area_a, area_b=area_b, risk=risk,
                mitigation=mitigation, severity=severity,
            ))
            self._touch()

    def get_dangerous_couplings(self, severity: str = "") -> List[DangerousCoupling]:
        """Get dangerous couplings, optionally filtered by severity."""
        if severity:
            return [c for c in self._dangerous_couplings if c.severity == severity]
        return list(self._dangerous_couplings)

    def freeze_semantics(self, symbol: str, meaning: str) -> None:
        """Freeze the semantic meaning of a symbol."""
        with self._lock:
            self._frozen_semantics[symbol] = meaning
            self._touch()

    def get_frozen_semantics(self, symbol: str) -> str:
        """Get frozen semantics for a symbol."""
        return self._frozen_semantics.get(symbol, "")

    def is_semantics_frozen(self, symbol: str) -> bool:
        """Check if semantics are frozen for a symbol."""
        return symbol in self._frozen_semantics

    def get_architecture_context(self) -> str:
        """Get compressed architecture context for LLM."""
        lines = ["# Architectural Memory", ""]

        # Active decisions
        decisions = self.get_all_decisions()
        if decisions:
            lines.append("## Architectural Decisions")
            for d in decisions[:10]:
                lines.append(f"- {d.title}: {d.decision[:100]}")
            lines.append("")

        # Integration contracts
        fragile_contracts = [c for c in self._contracts.values()
                             if c.stability == "fragile"]
        if fragile_contracts:
            lines.append("## Fragile Integration Contracts")
            for c in fragile_contracts:
                lines.append(f"- {c.subsystem_a} <-> {c.subsystem_b}: {c.interface}")
            lines.append("")

        # Dangerous couplings
        critical = [c for c in self._dangerous_couplings
                    if c.severity in ("high", "critical")]
        if critical:
            lines.append("## Dangerous Couplings")
            for c in critical:
                lines.append(f"- {c.area_a} <-> {c.area_b}: {c.risk}")
            lines.append("")

        # Frozen semantics
        if self._frozen_semantics:
            lines.append("## Frozen Semantics")
            for sym, meaning in list(self._frozen_semantics.items())[:10]:
                lines.append(f"- {sym}: {meaning}")
            lines.append("")

        return "\n".join(lines)

    def _touch(self) -> None:
        self._last_updated = datetime.utcnow().isoformat() + "Z"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "decisions": len(self._decisions),
            "active_decisions": sum(1 for d in self._decisions.values() if d.is_active),
            "contracts": len(self._contracts),
            "fragile_contracts": sum(1 for c in self._contracts.values() if c.stability == "fragile"),
            "dangerous_couplings": len(self._dangerous_couplings),
            "frozen_semantics": len(self._frozen_semantics),
            "last_updated": self._last_updated,
        }
