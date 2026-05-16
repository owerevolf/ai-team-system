"""
Phase 13, P2: Cross-Subsystem Contract Validation

Validates compatibility of contracts between subsystems:
- trust expectations vs ergonomics filtering
- governance guarantees vs compression
- recovery semantics vs GC
- visibility guarantees vs calm mode

Principle: Each subsystem may be individually correct,
but the system must be globally consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ContractType(Enum):
    VISIBILITY = "visibility"          # What must be visible vs what can be suppressed
    APPROVAL = "approval"              # What requires approval vs what can be auto-applied
    STATE = "state"                    # State lifecycle expectations
    RECOVERY = "recovery"              # Recovery semantics
    EXPLANATION = "explanation"        # Explanation depth requirements
    PRIORITY = "priority"              # Priority handling
    GOVERNANCE = "governance"          # Governance scope boundaries


class ContractStatus(Enum):
    COMPATIBLE = "compatible"
    WARNING = "warning"                # Potential inconsistency
    CONFLICT = "conflict"              # Direct contradiction
    UNDEFINED = "undefined"            # Contract not specified


@dataclass
class ContractRequirement:
    """A single contract requirement from one subsystem."""
    source: str                         # Subsystem name
    contract_type: ContractType
    description: str
    mandatory: bool = True              # If True, cannot be overridden
    condition: str = ""                 # When this requirement applies


@dataclass
class ContractValidation:
    """Result of validating a pair of contracts."""
    subsystem_a: str
    subsystem_b: str
    contract_type: ContractType
    status: ContractStatus
    details: str = ""
    resolution: str = ""                # How to resolve if conflict


@dataclass
class ContractReport:
    """Full contract validation report."""
    validations: list[ContractValidation] = field(default_factory=list)
    conflicts: list[ContractValidation] = field(default_factory=list)
    warnings: list[ContractValidation] = field(default_factory=list)

    @property
    def is_consistent(self) -> bool:
        return len(self.conflicts) == 0

    @property
    def total_checks(self) -> int:
        return len(self.validations)


class CrossSubsystemContractValidator:
    """
    Validates cross-subsystem contract compatibility.
    Detects conflicts where one subsystem's guarantees
    contradict another subsystem's behavior.
    """

    def __init__(self) -> None:
        self._requirements: list[ContractRequirement] = []
        self._register_known_contracts()

    def _register_known_contracts(self) -> None:
        """Register all known cross-subsystem contracts."""

        # Visibility contracts
        self.add_requirement(ContractRequirement(
            source="trust/visibility_guarantees",
            contract_type=ContractType.VISIBILITY,
            description="CRITICAL_FAILURE events must always be visible (ALWAYS guarantee)",
            mandatory=True,
        ))
        self.add_requirement(ContractRequirement(
            source="trust/transparency_contracts",
            contract_type=ContractType.VISIBILITY,
            description="INTEGRITY_FAILURE and DATA_LOSS_RISK must be SHOW or SUMMARIZE",
            mandatory=True,
        ))
        self.add_requirement(ContractRequirement(
            source="ergonomics/calm_mode",
            contract_type=ContractType.VISIBILITY,
            description="SILENT calm mode suppresses all non-error output",
            mandatory=False,
            condition="When user enables SILENT calm mode",
        ))
        self.add_requirement(ContractRequirement(
            source="compression/interaction_minimalism",
            contract_type=ContractType.VISIBILITY,
            description="SILENT priority interactions are never shown",
            mandatory=False,
        ))

        # Approval contracts
        self.add_requirement(ContractRequirement(
            source="ergonomics/approval_intelligence",
            contract_type=ContractType.APPROVAL,
            description="LOW risk approvals can be auto-applied",
            mandatory=False,
        ))
        self.add_requirement(ContractRequirement(
            source="trust/governance_pressure",
            contract_type=ContractType.APPROVAL,
            description="High governance pressure should increase approval requirements",
            mandatory=False,
            condition="When governance pressure is HIGH or CRITICAL",
        ))

        # State contracts
        self.add_requirement(ContractRequirement(
            source="durability/state_lifecycle",
            contract_type=ContractType.STATE,
            description="STRUCTURAL state must persist across sessions",
            mandatory=True,
        ))
        self.add_requirement(ContractRequirement(
            source="durability/context_gc",
            contract_type=ContractType.STATE,
            description="STALE context should be garbage collected",
            mandatory=False,
            condition="When context is STALE and not STRUCTURAL",
        ))

        # Recovery contracts
        self.add_requirement(ContractRequirement(
            source="durability/recovery_engine",
            contract_type=ContractType.RECOVERY,
            description="Recovery must be deterministic and replayable",
            mandatory=True,
        ))
        self.add_requirement(ContractRequirement(
            source="compression/do_less",
            contract_type=ContractType.RECOVERY,
            description="Do Less engine may suppress LOW-value recovery actions",
            mandatory=False,
        ))

        # Explanation contracts
        self.add_requirement(ContractRequirement(
            source="durability/explainability_layer",
            contract_type=ContractType.EXPLANATION,
            description="All decisions must have at least WHY explanation",
            mandatory=True,
        ))
        self.add_requirement(ContractRequirement(
            source="trust/explainability_compression",
            contract_type=ContractType.EXPLANATION,
            description="Explanations should be compressed by default",
            mandatory=False,
        ))
        self.add_requirement(ContractRequirement(
            source="compression/progressive_disclosure",
            contract_type=ContractType.EXPLANATION,
            description="Default disclosure is MINIMAL, expand on demand",
            mandatory=False,
        ))

        # Priority contracts
        self.add_requirement(ContractRequirement(
            source="ergonomics/attention_management",
            contract_type=ContractType.PRIORITY,
            description="CRITICAL priority must interrupt current workflow",
            mandatory=True,
        ))
        self.add_requirement(ContractRequirement(
            source="compression/do_less",
            contract_type=ContractType.PRIORITY,
            description="Do Less engine blocks interruptions by default",
            mandatory=False,
        ))

    def add_requirement(self, requirement: ContractRequirement) -> None:
        """Register a contract requirement."""
        self._requirements.append(requirement)

    def validate_all(self) -> ContractReport:
        """Run all cross-subsystem contract validations."""
        report = ContractReport()

        # Check each pair of requirements for the same contract type
        by_type: dict[ContractType, list[ContractRequirement]] = {}
        for req in self._requirements:
            by_type.setdefault(req.contract_type, []).append(req)

        for contract_type, reqs in by_type.items():
            for i, req_a in enumerate(reqs):
                for req_b in reqs[i + 1:]:
                    if req_a.source != req_b.source:
                        validation = self._check_pair(req_a, req_b, contract_type)
                        report.validations.append(validation)
                        if validation.status == ContractStatus.CONFLICT:
                            report.conflicts.append(validation)
                        elif validation.status == ContractStatus.WARNING:
                            report.warnings.append(validation)

        return report

    def _check_pair(
        self,
        req_a: ContractRequirement,
        req_b: ContractRequirement,
        contract_type: ContractType,
    ) -> ContractValidation:
        """Check compatibility of two contract requirements."""

        # Visibility conflicts
        if contract_type == ContractType.VISIBILITY:
            return self._check_visibility_conflict(req_a, req_b)

        # Approval conflicts
        if contract_type == ContractType.APPROVAL:
            return self._check_approval_conflict(req_a, req_b)

        # State conflicts
        if contract_type == ContractType.STATE:
            return self._check_state_conflict(req_a, req_b)

        # Recovery conflicts
        if contract_type == ContractType.RECOVERY:
            return self._check_recovery_conflict(req_a, req_b)

        # Explanation conflicts
        if contract_type == ContractType.EXPLANATION:
            return self._check_explanation_conflict(req_a, req_b)

        # Priority conflicts
        if contract_type == ContractType.PRIORITY:
            return self._check_priority_conflict(req_a, req_b)

        return ContractValidation(
            subsystem_a=req_a.source,
            subsystem_b=req_b.source,
            contract_type=contract_type,
            status=ContractStatus.UNDEFINED,
            details="No validation rule for this contract type",
        )

    def _check_visibility_conflict(
        self, req_a: ContractRequirement, req_b: ContractRequirement
    ) -> ContractValidation:
        """Check visibility contract conflicts."""
        # trust/visibility_guarantees says CRITICAL must always show
        # ergonomics/calm_mode SILENT suppresses everything
        if ("visibility_guarantees" in req_a.source and "calm_mode" in req_b.source) or \
           ("visibility_guarantees" in req_b.source and "calm_mode" in req_a.source):
            mandatory_a = req_a.mandatory
            mandatory_b = req_b.mandatory
            if mandatory_a and not mandatory_b:
                return ContractValidation(
                    subsystem_a=req_a.source,
                    subsystem_b=req_b.source,
                    contract_type=ContractType.VISIBILITY,
                    status=ContractStatus.WARNING,
                    details="Mandatory visibility guarantee vs optional calm mode suppression",
                    resolution="Calm mode must respect mandatory visibility guarantees — "
                                "CRITICAL events bypass SILENT mode",
                )
            elif mandatory_a and mandatory_b:
                return ContractValidation(
                    subsystem_a=req_a.source,
                    subsystem_b=req_b.source,
                    contract_type=ContractType.VISIBILITY,
                    status=ContractStatus.CONFLICT,
                    details="Both subsystems mandate conflicting visibility behavior",
                    resolution="Define priority: safety-critical visibility always wins over calm mode",
                )

        # interaction_minimalism SILENT vs trust visibility guarantees
        if ("interaction_minimalism" in req_a.source and "visibility_guarantees" in req_b.source) or \
           ("interaction_minimalism" in req_b.source and "visibility_guarantees" in req_a.source):
            return ContractValidation(
                subsystem_a=req_a.source,
                subsystem_b=req_b.source,
                contract_type=ContractType.VISIBILITY,
                status=ContractStatus.WARNING,
                details="Interaction minimalism may suppress what visibility guarantees require",
                resolution="Visibility guarantees must override interaction minimalism for CRITICAL events",
            )

        return ContractValidation(
            subsystem_a=req_a.source,
            subsystem_b=req_b.source,
            contract_type=ContractType.VISIBILITY,
            status=ContractStatus.COMPATIBLE,
        )

    def _check_approval_conflict(
        self, req_a: ContractRequirement, req_b: ContractRequirement
    ) -> ContractValidation:
        """Check approval contract conflicts."""
        # approval_intelligence auto-applies LOW risk
        # governance_pressure increases requirements under pressure
        if ("approval_intelligence" in req_a.source and "governance_pressure" in req_b.source) or \
           ("approval_intelligence" in req_b.source and "governance_pressure" in req_a.source):
            return ContractValidation(
                subsystem_a=req_a.source,
                subsystem_b=req_b.source,
                contract_type=ContractType.APPROVAL,
                status=ContractStatus.WARNING,
                details="Auto-apply may conflict with increased requirements under pressure",
                resolution="Governance pressure should raise effective risk level — "
                            "LOW becomes MEDIUM under HIGH pressure",
            )

        return ContractValidation(
            subsystem_a=req_a.source,
            subsystem_b=req_b.source,
            contract_type=ContractType.APPROVAL,
            status=ContractStatus.COMPATIBLE,
        )

    def _check_state_conflict(
        self, req_a: ContractRequirement, req_b: ContractRequirement
    ) -> ContractValidation:
        """Check state lifecycle conflicts."""
        # state_lifecycle says STRUCTURAL persists
        # context_gc may collect STALE context
        if ("state_lifecycle" in req_a.source and "context_gc" in req_b.source) or \
           ("state_lifecycle" in req_b.source and "context_gc" in req_a.source):
            return ContractValidation(
                subsystem_a=req_a.source,
                subsystem_b=req_b.source,
                contract_type=ContractType.STATE,
                status=ContractStatus.WARNING,
                details="GC may collect state that lifecycle says should persist",
                resolution="GC must check state tier before collection — "
                            "STRUCTURAL state is never auto-collected",
            )

        return ContractValidation(
            subsystem_a=req_a.source,
            subsystem_b=req_b.source,
            contract_type=ContractType.STATE,
            status=ContractStatus.COMPATIBLE,
        )

    def _check_recovery_conflict(
        self, req_a: ContractRequirement, req_b: ContractRequirement
    ) -> ContractValidation:
        """Check recovery semantics conflicts."""
        # recovery_engine requires deterministic replay
        # do_less may suppress LOW-value recovery
        if ("recovery_engine" in req_a.source and "do_less" in req_b.source) or \
           ("recovery_engine" in req_b.source and "do_less" in req_a.source):
            return ContractValidation(
                subsystem_a=req_a.source,
                subsystem_b=req_b.source,
                contract_type=ContractType.RECOVERY,
                status=ContractStatus.WARNING,
                details="Do Less may suppress recovery actions that engine considers necessary",
                resolution="Recovery actions must have minimum MEDIUM value — "
                            "Do Less should not suppress recovery",
            )

        return ContractValidation(
            subsystem_a=req_a.source,
            subsystem_b=req_b.source,
            contract_type=ContractType.RECOVERY,
            status=ContractStatus.COMPATIBLE,
        )

    def _check_explanation_conflict(
        self, req_a: ContractRequirement, req_b: ContractRequirement
    ) -> ContractValidation:
        """Check explanation depth conflicts."""
        # explainability_layer requires WHY for all decisions
        # progressive_disclosure defaults to MINIMAL
        # explainability_compression compresses by default
        sources = {req_a.source, req_b.source}
        if "explainability_layer" in sources and "progressive_disclosure" in sources:
            return ContractValidation(
                subsystem_a=req_a.source,
                subsystem_b=req_b.source,
                contract_type=ContractType.EXPLANATION,
                status=ContractStatus.WARNING,
                details="Explainability requires WHY, but disclosure defaults to MINIMAL (what only)",
                resolution="MINIMAL level must include at least action type — "
                            "WHY is available at SUMMARY level which is one expand away",
            )

        if "explainability_layer" in sources and "explainability_compression" in sources:
            return ContractValidation(
                subsystem_a=req_a.source,
                subsystem_b=req_b.source,
                contract_type=ContractType.EXPLANATION,
                status=ContractStatus.COMPATIBLE,
                details="Compression reduces verbosity but preserves semantic content",
            )

        return ContractValidation(
            subsystem_a=req_a.source,
            subsystem_b=req_b.source,
            contract_type=ContractType.EXPLANATION,
            status=ContractStatus.COMPATIBLE,
        )

    def _check_priority_conflict(
        self, req_a: ContractRequirement, req_b: ContractRequirement
    ) -> ContractValidation:
        """Check priority handling conflicts."""
        # attention_management says CRITICAL must interrupt
        # do_less blocks interruptions by default
        if ("attention_management" in req_a.source and "do_less" in req_b.source) or \
           ("attention_management" in req_b.source and "do_less" in req_a.source):
            return ContractValidation(
                subsystem_a=req_a.source,
                subsystem_b=req_b.source,
                contract_type=ContractType.PRIORITY,
                status=ContractStatus.WARNING,
                details="Attention management requires CRITICAL to interrupt, Do Less blocks interruptions",
                resolution="CRITICAL priority must bypass Do Less restraint — "
                            "safety-critical interruptions are always allowed",
            )

        return ContractValidation(
            subsystem_a=req_a.source,
            subsystem_b=req_b.source,
            contract_type=ContractType.PRIORITY,
            status=ContractStatus.COMPATIBLE,
        )

    def get_requirements_for(self, contract_type: ContractType) -> list[ContractRequirement]:
        """Get all requirements for a specific contract type."""
        return [r for r in self._requirements if r.contract_type == contract_type]

    def get_requirements_from(self, source: str) -> list[ContractRequirement]:
        """Get all requirements from a specific subsystem."""
        return [r for r in self._requirements if r.source == source]
