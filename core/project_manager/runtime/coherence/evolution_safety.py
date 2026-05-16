"""
Phase 13, P6: Evolution Safety Rules

Classifies architecture changes by risk level:
- SAFE: isolated simplification, dead code removal
- REVIEW_REQUIRED: new runtime surface, new governance semantics
- HIGH_RISK: hidden automation, cross-layer abstractions, semantic redefinition

Principle: Runtime must protect itself from bad evolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChangeRisk(Enum):
    SAFE = "safe"
    REVIEW_REQUIRED = "review_required"
    HIGH_RISK = "high_risk"


class ChangeCategory(Enum):
    # SAFE changes
    DEAD_CODE_REMOVAL = "dead_code_removal"
    ISOLATED_SIMPLIFICATION = "isolated_simplification"
    TEST_ADDITION = "test_addition"
    DOCUMENTATION_UPDATE = "documentation_update"
    TYPE_ANNOTATION = "type_annotation"

    # REVIEW_REQUIRED changes
    NEW_RUNTIME_SURFACE = "new_runtime_surface"
    NEW_GOVERNANCE_SEMANTICS = "new_governance_semantics"
    NEW_ADAPTATION_AUTHORITY = "new_adaptation_authority"
    BOUNDARY_CHANGE = "boundary_change"
    NEW_CROSS_SUBSYSTEM_IMPORT = "new_cross_subsystem_import"

    # HIGH_RISK changes
    HIDDEN_AUTOMATION = "hidden_automation"
    CROSS_LAYER_ABSTRACTION = "cross_layer_abstraction"
    SEMANTIC_REDEFINITION = "semantic_redefinition"
    RUNTIME_AUTHORITY_EXPANSION = "runtime_authority_expansion"
    PRIORITY_SEMANTIC_CHANGE = "priority_semantic_change"
    VISIBILITY_SEMANTIC_CHANGE = "visibility_semantic_change"
    STATE_LIFECYCLE_CHANGE = "state_lifecycle_change"


# Map categories to risk levels
CATEGORY_RISK: dict[ChangeCategory, ChangeRisk] = {
    # SAFE
    ChangeCategory.DEAD_CODE_REMOVAL: ChangeRisk.SAFE,
    ChangeCategory.ISOLATED_SIMPLIFICATION: ChangeRisk.SAFE,
    ChangeCategory.TEST_ADDITION: ChangeRisk.SAFE,
    ChangeCategory.DOCUMENTATION_UPDATE: ChangeRisk.SAFE,
    ChangeCategory.TYPE_ANNOTATION: ChangeRisk.SAFE,

    # REVIEW_REQUIRED
    ChangeCategory.NEW_RUNTIME_SURFACE: ChangeRisk.REVIEW_REQUIRED,
    ChangeCategory.NEW_GOVERNANCE_SEMANTICS: ChangeRisk.REVIEW_REQUIRED,
    ChangeCategory.NEW_ADAPTATION_AUTHORITY: ChangeRisk.REVIEW_REQUIRED,
    ChangeCategory.BOUNDARY_CHANGE: ChangeRisk.REVIEW_REQUIRED,
    ChangeCategory.NEW_CROSS_SUBSYSTEM_IMPORT: ChangeRisk.REVIEW_REQUIRED,

    # HIGH_RISK
    ChangeCategory.HIDDEN_AUTOMATION: ChangeRisk.HIGH_RISK,
    ChangeCategory.CROSS_LAYER_ABSTRACTION: ChangeRisk.HIGH_RISK,
    ChangeCategory.SEMANTIC_REDEFINITION: ChangeRisk.HIGH_RISK,
    ChangeCategory.RUNTIME_AUTHORITY_EXPANSION: ChangeRisk.HIGH_RISK,
    ChangeCategory.PRIORITY_SEMANTIC_CHANGE: ChangeRisk.HIGH_RISK,
    ChangeCategory.VISIBILITY_SEMANTIC_CHANGE: ChangeRisk.HIGH_RISK,
    ChangeCategory.STATE_LIFECYCLE_CHANGE: ChangeRisk.HIGH_RISK,
}


@dataclass
class ChangeClassification:
    """Classification of a proposed architecture change."""
    category: ChangeCategory
    risk: ChangeRisk
    description: str
    requires_approval_from: list[str] = field(default_factory=list)
    safety_checks: list[str] = field(default_factory=list)


@dataclass
class EvolutionSafetyReport:
    """Report of evolution safety analysis."""
    classifications: list[ChangeClassification] = field(default_factory=list)

    @property
    def safe_changes(self) -> list[ChangeClassification]:
        return [c for c in self.classifications if c.risk == ChangeRisk.SAFE]

    @property
    def review_required(self) -> list[ChangeClassification]:
        return [c for c in self.classifications if c.risk == ChangeRisk.REVIEW_REQUIRED]

    @property
    def high_risk(self) -> list[ChangeClassification]:
        return [c for c in self.classifications if c.risk == ChangeRisk.HIGH_RISK]


class EvolutionSafetyRules:
    """
    Classifies architecture changes by risk level.
    Provides safety checks and approval requirements for each category.
    """

    def __init__(self) -> None:
        self._classifications: dict[ChangeCategory, ChangeClassification] = {}
        self._register_classifications()

    def _register_classifications(self) -> None:
        """Register all change classifications."""
        for category, risk in CATEGORY_RISK.items():
            self._classifications[category] = ChangeClassification(
                category=category,
                risk=risk,
                description=self._get_description(category),
                requires_approval_from=self._get_approvers(category, risk),
                safety_checks=self._get_safety_checks(category),
            )

    def classify(self, category: ChangeCategory) -> ChangeClassification:
        """Classify a change by category."""
        return self._classifications.get(
            category,
            ChangeClassification(
                category=category,
                risk=ChangeRisk.REVIEW_REQUIRED,
                description=f"Unknown change category: {category.value}",
                requires_approval_from=["architect"],
            ),
        )

    def assess_change(
        self,
        category: ChangeCategory,
        target_module: str,
        description: str = "",
    ) -> ChangeClassification:
        """Assess a specific proposed change."""
        base = self.classify(category)
        return ChangeClassification(
            category=base.category,
            risk=base.risk,
            description=f"{base.description} (target: {target_module})",
            requires_approval_from=base.requires_approval_from,
            safety_checks=base.safety_checks,
        )

    def _get_description(self, category: ChangeCategory) -> str:
        descriptions = {
            ChangeCategory.DEAD_CODE_REMOVAL: "Remove unused code with no dependencies",
            ChangeCategory.ISOLATED_SIMPLIFICATION: "Simplify code within a single module",
            ChangeCategory.TEST_ADDITION: "Add tests for existing functionality",
            ChangeCategory.DOCUMENTATION_UPDATE: "Update documentation only",
            ChangeCategory.TYPE_ANNOTATION: "Add type annotations",
            ChangeCategory.NEW_RUNTIME_SURFACE: "Add new API endpoint, control, or user-visible concept",
            ChangeCategory.NEW_GOVERNANCE_SEMANTICS: "Introduce new governance rules or policy types",
            ChangeCategory.NEW_ADAPTATION_AUTHORITY: "Give runtime new authority to auto-adapt behavior",
            ChangeCategory.BOUNDARY_CHANGE: "Modify architectural boundaries between subsystems",
            ChangeCategory.NEW_CROSS_SUBSYSTEM_IMPORT: "Add import across subsystem boundaries",
            ChangeCategory.HIDDEN_AUTOMATION: "Add automation that operates without explicit user consent",
            ChangeCategory.CROSS_LAYER_ABSTRACTION: "Create abstraction that spans runtime/web_ui/core layers",
            ChangeCategory.SEMANTIC_REDEFINITION: "Change the meaning of an existing concept",
            ChangeCategory.RUNTIME_AUTHORITY_EXPANSION: "Expand runtime's authority over user decisions",
            ChangeCategory.PRIORITY_SEMANTIC_CHANGE: "Change what priority levels mean or how they're handled",
            ChangeCategory.VISIBILITY_SEMANTIC_CHANGE: "Change visibility/suppression semantics",
            ChangeCategory.STATE_LIFECYCLE_CHANGE: "Change state tier definitions or transitions",
        }
        return descriptions.get(category, f"Change: {category.value}")

    def _get_approvers(self, category: ChangeCategory, risk: ChangeRisk) -> list[str]:
        if risk == ChangeRisk.SAFE:
            return []
        elif risk == ChangeRisk.REVIEW_REQUIRED:
            return ["module_owner", "architect"]
        else:  # HIGH_RISK
            return ["architect", "team_lead", "safety_reviewer"]

    def _get_safety_checks(self, category: ChangeCategory) -> list[str]:
        checks: dict[ChangeCategory, list[str]] = {
            ChangeCategory.DEAD_CODE_REMOVAL: [
                "Verify no incoming dependencies",
                "Verify not a recovery path or emergency system",
                "Run full test suite after removal",
            ],
            ChangeCategory.NEW_RUNTIME_SURFACE: [
                "Check surface area budget",
                "Verify consistent with canonical vocabulary",
                "Add interaction minimalism policy",
            ],
            ChangeCategory.NEW_GOVERNANCE_SEMANTICS: [
                "Check for overlap with existing governance",
                "Verify governance entropy budget",
                "Validate against transparency contracts",
            ],
            ChangeCategory.HIDDEN_AUTOMATION: [
                "Require explicit user opt-in",
                "Add audit trail",
                "Provide override mechanism",
                "Verify against do_less philosophy",
            ],
            ChangeCategory.SEMANTIC_REDEFINITION: [
                "Check all modules using the old semantics",
                "Provide migration path",
                "Update canonical vocabulary",
                "Verify no contract violations",
            ],
        }
        return checks.get(category, ["Run full test suite", "Review architectural coherence"])
