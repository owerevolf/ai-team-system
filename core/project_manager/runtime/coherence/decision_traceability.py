"""
Phase 13, P8: Architectural Decision Traceability

Preserves why architectural decisions were made, not just what was built.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DecisionType(Enum):
    BOUNDARY = "boundary"
    ABSTRACTION = "abstraction"
    TRADEOFF = "tradeoff"
    CONSTRAINT = "constraint"
    PHILOSOPHY = "philosophy"
    LESSON = "lesson"


class DecisionScope(Enum):
    SYSTEM = "system"
    SUBSYSTEM = "subsystem"
    MODULE = "module"
    INTERFACE = "interface"


@dataclass
class ArchitecturalDecision:
    id: str
    title: str
    decision_type: DecisionType
    scope: DecisionScope
    description: str
    context: str
    decision_text: str
    rationale: str
    alternatives: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)
    related_decisions: list[str] = field(default_factory=list)
    phase: str = ""
    last_validated: str = ""


class DecisionTraceabilityRegistry:
    def __init__(self) -> None:
        self._decisions: dict[str, ArchitecturalDecision] = {}
        self._register_core_decisions()

    def _register_core_decisions(self) -> None:
        self.register(ArchitecturalDecision(
            id="ADR-001", title="Deterministic over AI",
            decision_type=DecisionType.PHILOSOPHY, scope=DecisionScope.SYSTEM,
            description="Core principle: deterministic behavior preferred over AI",
            context="AI systems are inherently non-deterministic. Predictability is more valuable.",
            decision_text="All core runtime behavior is deterministic. AI only for augmentation.",
            rationale="Non-deterministic core makes debugging impossible and breaks user trust.",
            alternatives=["AI-driven runtime adaptation", "ML-based workflow optimization"],
            tradeoffs=["Less 'intelligent' behavior", "More predictable debugging"],
            consequences=["Runtime is fully reproducible", "Bugs are deterministic"],
            phase="Phase 1",
        ))
        self.register(ArchitecturalDecision(
            id="ADR-002", title="Safety over Autonomy",
            decision_type=DecisionType.PHILOSOPHY, scope=DecisionScope.SYSTEM,
            description="Safety constraints always override autonomous behavior",
            context="Autonomous systems can make dangerous decisions.",
            decision_text="Safety checks are mandatory and cannot be bypassed.",
            rationale="Safety violations are irreversible. Automation must never compromise safety.",
            alternatives=["Adaptive safety", "User-configurable safety levels"],
            tradeoffs=["Less flexible automation", "Predictable safety"],
            consequences=["No autonomous action can violate safety"],
            phase="Phase 3",
        ))
        self.register(ArchitecturalDecision(
            id="ADR-003", title="Coordination over Complexity",
            decision_type=DecisionType.PHILOSOPHY, scope=DecisionScope.SYSTEM,
            description="Prefer simple coordination over complex autonomous behavior",
            context="Complex autonomous systems are hard to debug and maintain.",
            decision_text="Runtime uses simple, explicit protocols for coordination.",
            rationale="Emergent behavior is unpredictable. Explicit protocols are debuggable.",
            alternatives=["Emergent coordination", "Blackboard architecture"],
            tradeoffs=["Less 'intelligent' coordination", "Easier reasoning"],
            phase="Phase 4",
        ))
        self.register(ArchitecturalDecision(
            id="ADR-004", title="Subpackage Architecture for Runtime",
            decision_type=DecisionType.BOUNDARY, scope=DecisionScope.SUBSYSTEM,
            description="Runtime organized into subpackages by concern",
            context="After Phase 4, runtime had mixed concerns.",
            decision_text="Subpackages: durability, ergonomics, trust, optimization, compression, coherence.",
            rationale="Clear separation of concerns prevents semantic drift and boundary violations.",
            alternatives=["Flat module structure", "Feature-based organization"],
            tradeoffs=["Explicit imports needed", "Clearer boundaries"],
            related_decisions=["ADR-005", "ADR-006"],
            phase="Phase 9-13",
        ))
        self.register(ArchitecturalDecision(
            id="ADR-005", title="Transparency Contracts",
            decision_type=DecisionType.ABSTRACTION, scope=DecisionScope.SUBSYSTEM,
            description="Adaptive behavior governed by explicit contracts",
            context="Adaptive systems can behave unpredictably.",
            decision_text="Transparency contracts define mandatory visibility rules.",
            rationale="Users need guarantees about what the system will and won't do.",
            alternatives=["Adaptive transparency", "Fully configurable transparency"],
            tradeoffs=["Less flexible adaptation", "Stronger user trust"],
            related_decisions=["ADR-002"],
            phase="Phase 11",
        ))
        self.register(ArchitecturalDecision(
            id="ADR-006", title="Do Less as Architecture",
            decision_type=DecisionType.PHILOSOPHY, scope=DecisionScope.SYSTEM,
            description="Restraint is a first-class architectural principle",
            context="After 11 phases, main danger became over-intervention.",
            decision_text="Runtime defaults to inaction. Every action must justify execution.",
            rationale="User's attention is the most expensive resource. Noise destroys trust.",
            alternatives=["Proactive runtime", "AI-suggested actions"],
            tradeoffs=["Less 'helpful'", "Lower cognitive load"],
            related_decisions=["ADR-001", "ADR-002"],
            phase="Phase 12",
        ))
        self.register(ArchitecturalDecision(
            id="ADR-007", title="Canonical Vocabulary",
            decision_type=DecisionType.ABSTRACTION, scope=DecisionScope.SYSTEM,
            description="Shared concepts must have shared meaning",
            context="3+ priority models, 4+ event systems, 3 explanation models existed.",
            decision_text="Single canonical definition for each core concept.",
            rationale="Semantic fragmentation causes confusion, bugs, and maintenance burden.",
            alternatives=["Subsystem-owned semantics", "Documentation-only alignment"],
            tradeoffs=["Less subsystem flexibility", "Stronger consistency"],
            related_decisions=["ADR-004"],
            phase="Phase 13",
        ))
        self.register(ArchitecturalDecision(
            id="ADR-008", title="Deletion as First-Class Operation",
            decision_type=DecisionType.PHILOSOPHY, scope=DecisionScope.SYSTEM,
            description="Removing subsystems is as important as adding them",
            context="Dead code and obsolete abstractions accumulate indefinitely.",
            decision_text="Dead system detection runs continuously with governed deletion.",
            rationale="Systems that only grow become unmaintainable.",
            alternatives=["Manual cleanup", "Deprecation-only policy"],
            tradeoffs=["Risk of deleting something important", "Cleaner codebase"],
            related_decisions=["ADR-006"],
            phase="Phase 12",
        ))

    def register(self, decision: ArchitecturalDecision) -> None:
        self._decisions[decision.id] = decision

    def get(self, decision_id: str) -> Optional[ArchitecturalDecision]:
        return self._decisions.get(decision_id)

    def find_by_type(self, decision_type: DecisionType) -> list[ArchitecturalDecision]:
        return [d for d in self._decisions.values() if d.decision_type == decision_type]

    def find_by_scope(self, scope: DecisionScope) -> list[ArchitecturalDecision]:
        return [d for d in self._decisions.values() if d.scope == scope]

    def find_by_phase(self, phase: str) -> list[ArchitecturalDecision]:
        return [d for d in self._decisions.values() if d.phase == phase]

    def get_related(self, decision_id: str) -> list[ArchitecturalDecision]:
        decision = self._decisions.get(decision_id)
        if not decision:
            return []
        return [self._decisions[rid] for rid in decision.related_decisions if rid in self._decisions]

    @property
    def total_decisions(self) -> int:
        return len(self._decisions)

    @property
    def all_decisions(self) -> list[ArchitecturalDecision]:
        return list(self._decisions.values())
