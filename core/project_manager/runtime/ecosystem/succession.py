"""
Phase 15, P7: Architectural Succession Planning

Reduces tribal knowledge, enables maintainer rotation.
Preserves architectural rationale, subsystem intent, evolution history.

Principle: Project must survive maintainer turnover.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.project_manager.runtime.coherence.decision_traceability import (
    DecisionTraceabilityRegistry, ArchitecturalDecision, DecisionType,
)


@dataclass
class SubsystemKnowledge:
    """Knowledge profile for a subsystem."""
    name: str
    description: str
    primary_maintainer: str = ""
    secondary_maintainer: str = ""
    key_decisions: list[str] = field(default_factory=list)  # ADR IDs
    critical_invariants: list[str] = field(default_factory=list)
    common_pitfalls: list[str] = field(default_factory=list)
    onboarding_path: list[str] = field(default_factory=list)


@dataclass
class SuccessionReadiness:
    """Readiness assessment for maintainer succession."""
    subsystem: str
    knowledge_documented: bool = False
    secondary_available: bool = False
    decisions_traceable: bool = False
    invariants_testable: bool = False
    onboarding_exists: bool = False

    @property
    def is_ready(self) -> bool:
        return all([
            self.knowledge_documented,
            self.secondary_available,
            self.decisions_traceable,
            self.invariants_testable,
            self.onboarding_exists,
        ])

    @property
    def readiness_score(self) -> float:
        checks = [
            self.knowledge_documented,
            self.secondary_available,
            self.decisions_traceable,
            self.invariants_testable,
            self.onboarding_exists,
        ]
        return sum(1 for c in checks if c) / len(checks)


class ArchitecturalSuccessionPlanner:
    """
    Plans for maintainer succession and knowledge transfer.
    Ensures the project doesn't depend on a single "architecture brain".
    """

    def __init__(self) -> None:
        self._subsystems: dict[str, SubsystemKnowledge] = {}
        self._decision_registry = DecisionTraceabilityRegistry()
        self._register_subsystems()

    def _register_subsystems(self) -> None:
        """Register all runtime subsystems with their knowledge profiles."""

        self.register_subsystem(SubsystemKnowledge(
            name="durability",
            description="Runtime survivability: recovery, state lifecycle, chaos testing, GC",
            key_decisions=["ADR-001", "ADR-002"],
            critical_invariants=[
                "Recovery must be deterministic",
                "STRUCTURAL state must persist across sessions",
                "Safety checks cannot be bypassed",
            ],
            common_pitfalls=[
                "Forgetting to register recovery steps",
                "Collecting STRUCTURAL state in GC",
                "Non-deterministic recovery actions",
            ],
            onboarding_path=["state_management", "recovery_engine", "chaos_testing"],
        ))

        self.register_subsystem(SubsystemKnowledge(
            name="ergonomics",
            description="Human scaling: attention, calm mode, approval intelligence, time protection",
            key_decisions=["ADR-003", "ADR-006"],
            critical_invariants=[
                "CRITICAL priority must always be shown",
                "SILENT mode must not suppress safety events",
                "User time protection cannot be disabled by plugins",
            ],
            common_pitfalls=[
                "Over-suppressing notifications",
                "Breaking priority semantics",
                "Ignoring user time protection",
            ],
            onboarding_path=["execution_model", "governance_model", "trust_model"],
        ))

        self.register_subsystem(SubsystemKnowledge(
            name="trust",
            description="Predictability: visibility guarantees, personality, drift detection",
            key_decisions=["ADR-002", "ADR-005", "ADR-007"],
            critical_invariants=[
                "Visibility guarantees cannot be overridden by calm mode",
                "Trust drift detection must not psychoanalyze users",
                "Personality must remain consistent",
            ],
            common_pitfalls=[
                "Over-explaining (explanation overload)",
                "Under-explaining (trust erosion)",
                "Behavioral overreach",
            ],
            onboarding_path=["governance_model", "trust_model", "coherence_model"],
        ))

        self.register_subsystem(SubsystemKnowledge(
            name="compression",
            description="Minimalism: surface audit, dead system detection, do_less, interaction minimalism",
            key_decisions=["ADR-006", "ADR-008"],
            critical_invariants=[
                "Do Less must not suppress safety-critical actions",
                "Dead system detection must be conservative",
                "Compression must not hide control flow",
            ],
            common_pitfalls=[
                "Over-compressing (losing recoverability)",
                "Deleting recovery paths",
                "Hidden automation",
            ],
            onboarding_path=["compression_model", "coherence_model"],
        ))

        self.register_subsystem(SubsystemKnowledge(
            name="coherence",
            description="Consistency: canonical vocabulary, ontology drift, boundary enforcement",
            key_decisions=["ADR-004", "ADR-007"],
            critical_invariants=[
                "Canonical vocabulary must be used by all subsystems",
                "Boundary violations must be detected and reported",
                "Semantic drift must be tracked",
            ],
            common_pitfalls=[
                "Defining new priority models instead of using CanonicalPriority",
                "Ignoring boundary enforcement",
                "Silent semantic drift",
            ],
            onboarding_path=["coherence_model", "evolution_model"],
        ))

    def register_subsystem(self, knowledge: SubsystemKnowledge) -> None:
        """Register a subsystem knowledge profile."""
        self._subsystems[knowledge.name] = knowledge

    def get_subsystem(self, name: str) -> Optional[SubsystemKnowledge]:
        """Get knowledge profile for a subsystem."""
        return self._subsystems.get(name)

    def assess_succession_readiness(self, subsystem: str) -> SuccessionReadiness:
        """Assess how ready a subsystem is for maintainer succession."""
        knowledge = self._subsystems.get(subsystem)
        if not knowledge:
            return SuccessionReadiness(subsystem=subsystem)

        return SuccessionReadiness(
            subsystem=subsystem,
            knowledge_documented=bool(knowledge.key_decisions and knowledge.critical_invariants),
            secondary_available=bool(knowledge.secondary_maintainer),
            decisions_traceable=all(
                self._decision_registry.get(adr) is not None
                for adr in knowledge.key_decisions
            ),
            invariants_testable=bool(knowledge.critical_invariants),
            onboarding_exists=bool(knowledge.onboarding_path),
        )

    def get_all_readiness(self) -> dict[str, SuccessionReadiness]:
        """Get succession readiness for all subsystems."""
        return {
            name: self.assess_succession_readiness(name)
            for name in self._subsystems
        }

    def identify_knowledge_gaps(self) -> list[str]:
        """Identify subsystems with knowledge gaps."""
        gaps: list[str] = []
        for name, knowledge in self._subsystems.items():
            if not knowledge.primary_maintainer:
                gaps.append(f"{name}: no primary maintainer assigned")
            if not knowledge.secondary_maintainer:
                gaps.append(f"{name}: no secondary maintainer (bus factor = 1)")
            if not knowledge.key_decisions:
                gaps.append(f"{name}: no architectural decisions documented")
            if not knowledge.critical_invariants:
                gaps.append(f"{name}: no critical invariants defined")
        return gaps

    @property
    def total_subsystems(self) -> int:
        return len(self._subsystems)
