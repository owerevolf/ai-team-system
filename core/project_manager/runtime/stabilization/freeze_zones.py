"""
Phase 16, P2: Architecture Freeze Zones

Defines frozen semantics, stable contracts, immutable governance guarantees.
Anti-chaos layer for long-term project survival.

Principle: Some things should never change casually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FreezeLevel(Enum):
    FROZEN = "frozen"              # Never change without full architectural review
    STABLE = "stable"              # Change only with strong justification
    EVOLVING = "evolving"          # Can evolve with normal governance
    EXPERIMENTAL = "experimental"  # Can change freely


@dataclass
class FrozenConcept:
    """A concept that is frozen or stable."""
    name: str
    freeze_level: FreezeLevel
    description: str
    module: str
    invariants: list[str] = field(default_factory=list)
    change_requires: list[str] = field(default_factory=list)
    rationale: str = ""


class ArchitectureFreezeZones:
    """
    Manages frozen and stable architectural concepts.
    Prevents casual changes to critical runtime semantics.
    """

    # Core frozen concepts — NEVER casually redefine
    FROZEN_CONCEPTS: list[dict] = [
        {
            "name": "approval_semantics",
            "level": FreezeLevel.FROZEN,
            "description": "What requires approval and what can be auto-applied",
            "module": "ergonomics/approval_intelligence",
            "invariants": [
                "CRITICAL risk always requires human approval",
                "LOW risk can be auto-applied with audit trail",
                "Approval status must be deterministic given same context",
            ],
            "change_requires": ["architect", "safety_reviewer", "team_lead"],
            "rationale": "Approval semantics are core to trust. Changing them casually destroys user trust.",
        },
        {
            "name": "visibility_guarantees",
            "level": FreezeLevel.FROZEN,
            "description": "What must always be visible vs what can be suppressed",
            "module": "trust/visibility_guarantees",
            "invariants": [
                "CRITICAL_FAILURE events must always be visible",
                "Safety events cannot be suppressed by calm mode",
                "Suppressed information must be recoverable on request",
            ],
            "change_requires": ["architect", "safety_reviewer"],
            "rationale": "Visibility guarantees are core to trust. Weakening them is a safety issue.",
        },
        {
            "name": "recovery_semantics",
            "level": FreezeLevel.FROZEN,
            "description": "How recovery works: deterministic, replayable, auditable",
            "module": "durability/recovery_engine",
            "invariants": [
                "Recovery must be deterministic given same failure",
                "All recovery actions must be auditable",
                "Recovery cannot be suppressed by do_less or calm mode",
            ],
            "change_requires": ["architect", "safety_reviewer"],
            "rationale": "Recovery is the last line of defense. Changing it casually is dangerous.",
        },
        {
            "name": "audit_integrity",
            "level": FreezeLevel.FROZEN,
            "description": "Audit trail must be complete and tamper-evident",
            "module": "trust/audit_visible_automation",
            "invariants": [
                "All automated actions must have audit trail",
                "Audit logs cannot be silently deleted",
                "Audit entries must include timestamp, actor, action, outcome",
            ],
            "change_requires": ["architect", "safety_reviewer", "team_lead"],
            "rationale": "Audit integrity is non-negotiable for trust.",
        },
        {
            "name": "plugin_authority_boundaries",
            "level": FreezeLevel.FROZEN,
            "description": "What plugins can and cannot do",
            "module": "durability/plugin_boundaries",
            "invariants": [
                "Plugins cannot bypass approvals",
                "Plugins cannot modify PM core",
                "Plugins cannot suppress audit trails",
                "Plugins must operate within capability contracts",
            ],
            "change_requires": ["architect", "safety_reviewer"],
            "rationale": "Plugin boundaries prevent shadow runtime.",
        },
        {
            "name": "canonical_vocabulary",
            "level": FreezeLevel.STABLE,
            "description": "Shared concept definitions (priority, event, explanation, state, approval, visibility)",
            "module": "coherence/vocabulary",
            "invariants": [
                "All subsystems must use canonical definitions",
                "New concepts must be added to canonical vocabulary",
                "Redefining canonical concepts requires architectural review",
            ],
            "change_requires": ["architect"],
            "rationale": "Canonical vocabulary prevents semantic drift.",
        },
        {
            "name": "state_lifecycle",
            "level": FreezeLevel.STABLE,
            "description": "State tier definitions and transitions",
            "module": "durability/state_lifecycle",
            "invariants": [
                "EPHEMERAL → SESSION → OPERATIONAL → STRUCTURAL is one-way",
                "STRUCTURAL state must persist across sessions",
                "GC must never collect STRUCTURAL state",
            ],
            "change_requires": ["architect"],
            "rationale": "State lifecycle is core to runtime correctness.",
        },
        {
            "name": "do_less_philosophy",
            "level": FreezeLevel.STABLE,
            "description": "Runtime defaults to inaction, restraint as architecture",
            "module": "compression/do_less",
            "invariants": [
                "CRITICAL priority bypasses do_less",
                "Safety actions cannot be suppressed by do_less",
                "Do_less must not hide control flow",
            ],
            "change_requires": ["architect"],
            "rationale": "Do less is core to user trust and cognitive sustainability.",
        },
    ]

    def __init__(self) -> None:
        self._concepts: dict[str, FrozenConcept] = {}
        self._register_concepts()

    def _register_concepts(self) -> None:
        """Register all frozen concepts."""
        for data in self.FROZEN_CONCEPTS:
            concept = FrozenConcept(
                name=data["name"],
                freeze_level=data["level"],
                description=data["description"],
                module=data["module"],
                invariants=data.get("invariants", []),
                change_requires=data.get("change_requires", []),
                rationale=data.get("rationale", ""),
            )
            self._concepts[concept.name] = concept

    def get_concept(self, name: str) -> Optional[FrozenConcept]:
        """Get a frozen concept by name."""
        return self._concepts.get(name)

    def check_change_allowed(self, concept_name: str, approvers: list[str]) -> tuple[bool, str]:
        """Check if a change to a frozen concept is allowed."""
        concept = self._concepts.get(concept_name)
        if not concept:
            return True, f"Concept '{concept_name}' is not frozen"

        if concept.freeze_level == FreezeLevel.EVOLVING:
            return True, "Concept is evolving, normal governance applies"

        if concept.freeze_level == FreezeLevel.EXPERIMENTAL:
            return True, "Concept is experimental, changes allowed"

        # Check if all required approvers are present
        required = set(concept.change_requires)
        provided = set(approvers)
        missing = required - provided

        if missing:
            return False, (
                f"Change to '{concept_name}' requires approval from: {', '.join(missing)}. "
                f"Rationale: {concept.rationale}"
            )

        return True, f"Change to '{concept_name}' approved with required reviewers"

    def get_frozen_concepts(self) -> list[FrozenConcept]:
        """Get all frozen concepts."""
        return [c for c in self._concepts.values() if c.freeze_level == FreezeLevel.FROZEN]

    def get_stable_concepts(self) -> list[FrozenConcept]:
        """Get all stable concepts."""
        return [c for c in self._concepts.values() if c.freeze_level == FreezeLevel.STABLE]

    @property
    def total_frozen(self) -> int:
        return sum(1 for c in self._concepts.values() if c.freeze_level == FreezeLevel.FROZEN)

    @property
    def total_stable(self) -> int:
        return sum(1 for c in self._concepts.values() if c.freeze_level == FreezeLevel.STABLE)
