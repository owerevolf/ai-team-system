"""
Workflow Pipelines — reusable, deterministic workflow definitions.

Workflows:
- feature: full development cycle
- bugfix: targeted fix with validation
- refactor: safe refactoring with architecture checks

Each pipeline is a sequence of deterministic steps.
No AI-generated workflow logic.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


class WorkflowStepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    description: str
    required: bool = True
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    error: str = ""
    result: Any = None


@dataclass
class WorkflowDefinition:
    """A workflow template."""
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)

    def get_required_steps(self) -> List[WorkflowStep]:
        return [s for s in self.steps if s.required]

    def get_optional_steps(self) -> List[WorkflowStep]:
        return [s for s in self.steps if not s.required]


class WorkflowPipelines:
    """
    Predefined workflow pipelines.

    Each pipeline is a fixed sequence of steps.
    Steps are deterministic and observable.
    """

    @classmethod
    def feature_workflow(cls) -> WorkflowDefinition:
        """Full feature development workflow."""
        return WorkflowDefinition(
            name="feature",
            description="Full feature development with validation and approval",
            steps=[
                WorkflowStep(
                    name="context_retrieval",
                    description="Gather relevant context from PM",
                    required=True,
                ),
                WorkflowStep(
                    name="execution",
                    description="Agent implements the feature",
                    required=True,
                ),
                WorkflowStep(
                    name="validation",
                    description="Run validation pipeline on changes",
                    required=True,
                ),
                WorkflowStep(
                    name="impact_analysis",
                    description="Analyze impact of changes",
                    required=True,
                ),
                WorkflowStep(
                    name="test_selection",
                    description="Find and run relevant tests",
                    required=True,
                ),
                WorkflowStep(
                    name="risk_assessment",
                    description="Assess risk of changes",
                    required=True,
                ),
                WorkflowStep(
                    name="approval_gate",
                    description="Wait for human approval if required",
                    required=True,
                ),
                WorkflowStep(
                    name="snapshot",
                    description="Create post-change snapshot",
                    required=False,
                ),
                WorkflowStep(
                    name="merge",
                    description="Merge changes to main workspace",
                    required=True,
                ),
                WorkflowStep(
                    name="commit",
                    description="Git commit with change summary",
                    required=False,
                ),
            ],
        )

    @classmethod
    def bugfix_workflow(cls) -> WorkflowDefinition:
        """Targeted bugfix workflow."""
        return WorkflowDefinition(
            name="bugfix",
            description="Targeted bugfix with validation",
            steps=[
                WorkflowStep(
                    name="context_retrieval",
                    description="Gather context around the bug",
                    required=True,
                ),
                WorkflowStep(
                    name="impact_analysis",
                    description="Analyze what's affected by the bug",
                    required=True,
                ),
                WorkflowStep(
                    name="execution",
                    description="Agent implements the fix",
                    required=True,
                ),
                WorkflowStep(
                    name="validation",
                    description="Validate the fix",
                    required=True,
                ),
                WorkflowStep(
                    name="targeted_tests",
                    description="Run tests specifically related to the fix",
                    required=True,
                ),
                WorkflowStep(
                    name="approval_gate",
                    description="Approval for medium+ risk changes",
                    required=True,
                ),
                WorkflowStep(
                    name="merge",
                    description="Merge fix to main workspace",
                    required=True,
                ),
            ],
        )

    @classmethod
    def refactor_workflow(cls) -> WorkflowDefinition:
        """Safe refactoring workflow."""
        return WorkflowDefinition(
            name="refactor",
            description="Safe refactoring with architecture checks",
            steps=[
                WorkflowStep(
                    name="context_retrieval",
                    description="Gather full context of code to refactor",
                    required=True,
                ),
                WorkflowStep(
                    name="architecture_check",
                    description="Verify refactoring won't violate architecture rules",
                    required=True,
                ),
                WorkflowStep(
                    name="impact_analysis",
                    description="Full impact analysis of refactoring",
                    required=True,
                ),
                WorkflowStep(
                    name="risk_assessment",
                    description="Assess refactoring risk",
                    required=True,
                ),
                WorkflowStep(
                    name="approval_gate",
                    description="Human approval required for all refactors",
                    required=True,
                ),
                WorkflowStep(
                    name="execution",
                    description="Agent performs refactoring",
                    required=True,
                ),
                WorkflowStep(
                    name="validation",
                    description="Full validation pipeline",
                    required=True,
                ),
                WorkflowStep(
                    name="test_selection",
                    description="Run all affected tests",
                    required=True,
                ),
                WorkflowStep(
                    name="merge",
                    description="Merge refactored code",
                    required=True,
                ),
            ],
        )

    @classmethod
    def get_workflow(cls, name: str) -> Optional[WorkflowDefinition]:
        """Get a workflow by name."""
        workflows = {
            'feature': cls.feature_workflow,
            'bugfix': cls.bugfix_workflow,
            'refactor': cls.refactor_workflow,
        }
        factory = workflows.get(name)
        return factory() if factory else None

    @classmethod
    def list_workflows(cls) -> List[str]:
        """List available workflow names."""
        return ['feature', 'bugfix', 'refactor']
