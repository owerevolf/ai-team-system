"""
P11 — Workflow Templates.

Reusable engineering workflow templates.
NOT dynamic AI-generated workflows — explicit, deterministic templates.

Template types:
- feature development
- bugfix
- migration
- dependency upgrade
- test generation
- refactor
- API evolution
- performance optimization
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TemplateType(Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    MIGRATION = "migration"
    DEPENDENCY_UPGRADE = "dependency_upgrade"
    TEST_GENERATION = "test_generation"
    REFACTOR = "refactor"
    API_EVOLUTION = "api_evolution"
    PERFORMANCE = "performance"
    CLEANUP = "cleanup"
    SECURITY_FIX = "security_fix"


@dataclass
class TemplateStep:
    """A single step in a workflow template."""
    name: str
    description: str
    required: bool = True
    approval_required: bool = False
    rollback_enabled: bool = True
    timeout_seconds: int = 300
    retry_count: int = 0


@dataclass
class WorkflowTemplate:
    """A reusable workflow template."""
    name: str
    template_type: TemplateType
    description: str
    steps: List[TemplateStep] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"

    def get_required_steps(self) -> List[TemplateStep]:
        return [s for s in self.steps if s.required]

    def get_approval_steps(self) -> List[TemplateStep]:
        return [s for s in self.steps if s.approval_required]


class WorkflowTemplateRegistry:
    """
    Registry of reusable workflow templates.
    All templates are explicit and deterministic.
    """

    def __init__(self):
        self._templates: Dict[str, WorkflowTemplate] = {}
        self._build_default_templates()

    def _build_default_templates(self) -> None:
        """Build default workflow templates."""
        templates = [
            WorkflowTemplate(
                name="feature",
                template_type=TemplateType.FEATURE,
                description="Full feature development with validation and approval",
                steps=[
                    TemplateStep("context_retrieval", "Gather relevant context", required=True),
                    TemplateStep("impact_analysis", "Analyze impact of changes", required=True),
                    TemplateStep("execution", "Implement the feature", required=True),
                    TemplateStep("validation", "Run validation pipeline", required=True),
                    TemplateStep("test_generation", "Generate tests for new code", required=False),
                    TemplateStep("approval_gate", "Human approval if required", required=True),
                    TemplateStep("merge", "Merge changes", required=True),
                    TemplateStep("commit", "Git commit", required=False),
                ],
                tags=["development", "full-cycle"],
            ),
            WorkflowTemplate(
                name="bugfix",
                template_type=TemplateType.BUGFIX,
                description="Targeted bugfix with validation",
                steps=[
                    TemplateStep("context_retrieval", "Gather context around the bug", required=True),
                    TemplateStep("root_cause_analysis", "Identify root cause", required=True),
                    TemplateStep("execution", "Implement the fix", required=True),
                    TemplateStep("validation", "Validate the fix", required=True),
                    TemplateStep("targeted_tests", "Run related tests", required=True),
                    TemplateStep("approval_gate", "Approval for medium+ risk", required=True),
                    TemplateStep("merge", "Merge fix", required=True),
                ],
                tags=["fix", "targeted"],
            ),
            WorkflowTemplate(
                name="refactor",
                template_type=TemplateType.REFACTOR,
                description="Safe refactoring with architecture checks",
                steps=[
                    TemplateStep("context_retrieval", "Gather full context", required=True),
                    TemplateStep("architecture_check", "Verify no arch violations", required=True),
                    TemplateStep("impact_analysis", "Full impact analysis", required=True),
                    TemplateStep("approval_gate", "Human approval required", required=True, approval_required=True),
                    TemplateStep("execution", "Perform refactoring", required=True),
                    TemplateStep("validation", "Full validation", required=True),
                    TemplateStep("test_selection", "Run all affected tests", required=True),
                    TemplateStep("merge", "Merge refactored code", required=True),
                ],
                tags=["refactor", "architecture"],
            ),
            WorkflowTemplate(
                name="migration",
                template_type=TemplateType.MIGRATION,
                description="Code migration with safety checks",
                steps=[
                    TemplateStep("context_retrieval", "Understand current state", required=True),
                    TemplateStep("migration_plan", "Plan migration steps", required=True),
                    TemplateStep("approval_gate", "Approval required", required=True, approval_required=True),
                    TemplateStep("pre_migration_snapshot", "Create pre-migration snapshot", required=True),
                    TemplateStep("execution", "Execute migration", required=True),
                    TemplateStep("validation", "Validate migrated code", required=True),
                    TemplateStep("rollback_check", "Verify rollback capability", required=True),
                    TemplateStep("merge", "Merge migration", required=True),
                ],
                tags=["migration", "high-risk"],
            ),
            WorkflowTemplate(
                name="dependency_upgrade",
                template_type=TemplateType.DEPENDENCY_UPGRADE,
                description="Dependency upgrade with compatibility checks",
                steps=[
                    TemplateStep("context_retrieval", "Check current dependencies", required=True),
                    TemplateStep("compatibility_check", "Check compatibility", required=True),
                    TemplateStep("impact_analysis", "Analyze upgrade impact", required=True),
                    TemplateStep("approval_gate", "Approval for major upgrades", required=True),
                    TemplateStep("execution", "Upgrade dependency", required=True),
                    TemplateStep("validation", "Full validation", required=True),
                    TemplateStep("test_selection", "Run all tests", required=True),
                    TemplateStep("merge", "Merge upgrade", required=True),
                ],
                tags=["dependency", "upgrade"],
            ),
            WorkflowTemplate(
                name="test_generation",
                template_type=TemplateType.TEST_GENERATION,
                description="Generate tests for existing code",
                steps=[
                    TemplateStep("context_retrieval", "Analyze code to test", required=True),
                    TemplateStep("coverage_analysis", "Check current coverage", required=True),
                    TemplateStep("execution", "Generate tests", required=True),
                    TemplateStep("validation", "Run generated tests", required=True),
                    TemplateStep("approval_gate", "Review generated tests", required=False),
                    TemplateStep("merge", "Merge tests", required=True),
                ],
                tags=["test", "generation"],
            ),
            WorkflowTemplate(
                name="api_evolution",
                template_type=TemplateType.API_EVOLUTION,
                description="API evolution with backward compatibility",
                steps=[
                    TemplateStep("context_retrieval", "Understand current API", required=True),
                    TemplateStep("compatibility_check", "Check backward compatibility", required=True),
                    TemplateStep("impact_analysis", "Analyze API consumers", required=True),
                    TemplateStep("approval_gate", "Approval required", required=True, approval_required=True),
                    TemplateStep("execution", "Implement API changes", required=True),
                    TemplateStep("validation", "Validate API contracts", required=True),
                    TemplateStep("test_selection", "Run API tests", required=True),
                    TemplateStep("merge", "Merge API changes", required=True),
                ],
                tags=["api", "evolution"],
            ),
            WorkflowTemplate(
                name="performance",
                template_type=TemplateType.PERFORMANCE,
                description="Performance optimization with benchmarks",
                steps=[
                    TemplateStep("context_retrieval", "Profile current performance", required=True),
                    TemplateStep("bottleneck_analysis", "Identify bottlenecks", required=True),
                    TemplateStep("execution", "Implement optimization", required=True),
                    TemplateStep("benchmark", "Run benchmarks", required=True),
                    TemplateStep("validation", "Validate no regressions", required=True),
                    TemplateStep("approval_gate", "Approval for significant changes", required=True),
                    TemplateStep("merge", "Merge optimization", required=True),
                ],
                tags=["performance", "optimization"],
            ),
        ]

        for t in templates:
            self._templates[t.name] = t

    def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        """Get a template by name."""
        return self._templates.get(name)

    def list_templates(self, tag: str = None) -> List[WorkflowTemplate]:
        """List templates, optionally filtered by tag."""
        templates = list(self._templates.values())
        if tag:
            templates = [t for t in templates if tag in t.tags]
        return templates

    def register_template(self, template: WorkflowTemplate) -> None:
        """Register a custom template."""
        self._templates[template.name] = template

    def get_template_names(self) -> List[str]:
        """Get all template names."""
        return list(self._templates.keys())
