"""
Educational Mode Preservation (P5) — Phase 8

Preserves and enhances the educational nature of the AI Team System.
Provides tutorial flows, beginner explanations, guided workflows,
and learning difficulty levels.

Key principle: PM must NOT kill the educational nature of the project.
Every operation can be a learning opportunity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TutorialStep:
    """A single step in a tutorial flow."""
    step_id: str
    title: str
    explanation: str          # What and why (educational)
    instruction: str          # What the user/agent should do
    difficulty: str = "beginner"  # beginner | intermediate | advanced
    hints: list[str] = field(default_factory=list)
    verification: str = ""    # How to verify this step succeeded
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "explanation": self.explanation,
            "instruction": self.instruction,
            "difficulty": self.difficulty,
            "hints": self.hints,
            "verification": self.verification,
            "completed": self.completed,
        }


@dataclass
class TutorialFlow:
    """A complete tutorial flow for a specific task."""
    flow_id: str
    title: str
    description: str
    difficulty: str = "beginner"
    steps: list[TutorialStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "steps": [s.to_dict() for s in self.steps],
            "tags": self.tags,
        }


@dataclass
class Explanation:
    """A beginner-friendly explanation of a concept or operation."""
    concept: str
    simple_explanation: str      # ELI5 style
    technical_explanation: str   # More detailed
    example: str = ""
    related_concepts: list[str] = field(default_factory=list)
    difficulty: str = "beginner"

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "simple_explanation": self.simple_explanation,
            "technical_explanation": self.technical_explanation,
            "example": self.example,
            "related_concepts": self.related_concepts,
            "difficulty": self.difficulty,
        }


# ---------------------------------------------------------------------------
# Built-in tutorial flows
# ---------------------------------------------------------------------------

BUILTIN_TUTORIALS: dict[str, TutorialFlow] = {
    "first-project-import": TutorialFlow(
        flow_id="first-project-import",
        title="Import Your First Project",
        description="Learn how to import a project and understand its structure",
        difficulty="beginner",
        tags=["import", "basics", "getting-started"],
        steps=[
            TutorialStep(
                step_id="s1",
                title="Choose a project to import",
                explanation="The PM can work with any code project. You can import from a local folder, GitHub, or a zip file.",
                instruction="Pick a small project you want to explore. A simple Python or JavaScript project works best.",
                hints=["Start with a project that has less than 20 files", "Make sure you have read access to the files"],
                verification="Project path is set and accessible",
            ),
            TutorialStep(
                step_id="s2",
                title="Import the project",
                explanation="When you import a project, the PM reads all files, identifies the tech stack, and builds an understanding of the architecture.",
                instruction="Use the 'Import Project' button in the workspace or type the project path.",
                hints=["The PM will show you what it found: language, frameworks, entry points"],
                verification="Project appears in the workspace with a health dashboard",
            ),
            TutorialStep(
                step_id="s3",
                title="Explore the project understanding",
                explanation="The PM creates a 'project understanding snapshot' — a structured summary of what the project uses and how it's organized.",
                instruction="Look at the project overview page. Check the detected language, frameworks, and entry points.",
                hints=["If something looks wrong, you can manually adjust the understanding"],
                verification="You can see the project's tech stack and architecture style",
            ),
        ],
    ),
    "first-feature": TutorialFlow(
        flow_id="first-feature",
        title="Add Your First Feature",
        description="Learn how to add a new feature with PM guidance",
        difficulty="beginner",
        tags=["feature", "development", "workflow"],
        steps=[
            TutorialStep(
                step_id="s1",
                title="Describe what you want to build",
                explanation="The PM reads your feature description and figures out which parts of the project need to change.",
                instruction="Type a simple feature request, like 'Add a health check endpoint' or 'Add user profile page'.",
                hints=["Be specific about what you want", "Mention the technology if you know it (e.g., 'REST API endpoint')"],
                verification="PM shows a plan with affected modules and stages",
            ),
            TutorialStep(
                step_id="s2",
                title="Review the plan",
                explanation="The PM breaks the feature into stages. Each stage has a risk level. High-risk stages need your approval.",
                instruction="Read through the plan. Check which files will be modified and what the risk level is.",
                hints=["Look for stages marked [NEEDS APPROVAL]", "Check the affected modules list"],
                verification="You understand what each stage will do",
            ),
            TutorialStep(
                step_id="s3",
                title="Approve and execute",
                explanation="Once you approve, the PM executes each stage through the governed runtime. You can see progress in real-time.",
                instruction="Click 'Approve Plan' to start execution. Watch the progress panel.",
                hints=["You can pause or rollback at any time", "Check the diff preview before each stage"],
                verification="Feature is implemented and tests pass",
            ),
        ],
    ),
    "first-repair": TutorialFlow(
        flow_id="first-repair",
        title="Repair a Broken Project",
        description="Learn how to fix common project issues",
        difficulty="intermediate",
        tags=["repair", "debugging", "maintenance"],
        steps=[
            TutorialStep(
                step_id="s1",
                title="Import the broken project",
                explanation="The PM will scan the project and identify issues: broken imports, missing dependencies, deprecated patterns.",
                instruction="Import a project that has some issues. The PM will show a health dashboard with warnings.",
                hints=["Look for red/yellow indicators on the health dashboard", "Check the 'Issues' section"],
                verification="PM shows a list of detected issues",
            ),
            TutorialStep(
                step_id="s2",
                title="Review the repair plan",
                explanation="For each issue, the PM creates a repair step with an impact assessment. You decide which fixes to apply.",
                instruction="Review each repair step. Approve the ones you want to apply.",
                hints=["Start with low-risk fixes first", "Read the impact description for each step"],
                verification="You have a list of approved repair steps",
            ),
            TutorialStep(
                step_id="s3",
                title="Execute repairs with rollback",
                explanation="The PM creates a sandbox checkpoint before each repair. If something goes wrong, you can rollback.",
                instruction="Click 'Execute Repairs'. The PM will create a checkpoint, apply fixes, and verify.",
                hints=["Always keep the checkpoint until you're sure the fix works", "You can rollback individual steps"],
                verification="All approved repairs are applied and project health improved",
            ),
        ],
    ),
}

# ---------------------------------------------------------------------------
# Built-in explanations
# ---------------------------------------------------------------------------

BUILTIN_EXPLANATIONS: dict[str, Explanation] = {
    "what-is-pm": Explanation(
        concept="What is the Project Manager (PM)?",
        simple_explanation=(
            "The PM is like a very careful assistant that helps you work on code projects. "
            "It reads your project, understands its structure, and helps you make changes safely. "
            "It never does anything without showing you the plan first."
        ),
        technical_explanation=(
            "The PM is a deterministic engineering control layer that provides project indexing, "
            "dependency analysis, validation, governed runtime execution, and audit logging. "
            "It operates on explicit rules, not AI inference."
        ),
        example="When you say 'add a login feature', the PM finds the auth module, checks dependencies, and creates a step-by-step plan.",
        related_concepts=["governed-runtime", "sandbox", "checkpoint"],
    ),
    "what-is-sandbox": Explanation(
        concept="What is a sandbox?",
        simple_explanation=(
            "A sandbox is a safe playground. Before the PM makes any changes, it creates a 'checkpoint' "
            "— like saving your game. If something goes wrong, you can go back to the checkpoint."
        ),
        technical_explanation=(
            "The sandbox uses git to create isolated execution environments. Each checkpoint is a git commit. "
            "Rollback is a git reset --hard to the checkpoint hash. Protected zones prevent modification of build artifacts."
        ),
        example="Before fixing imports, the PM creates a checkpoint. If the fix breaks something, click 'Rollback' to undo.",
        related_concepts=["checkpoint", "rollback", "protected-zones"],
    ),
    "what-is-governed-runtime": Explanation(
        concept="What is the governed runtime?",
        simple_explanation=(
            "The governed runtime is like a set of traffic rules for the PM. It makes sure the PM "
            "doesn't do anything dangerous without asking you first. Every action is checked against safety rules."
        ),
        technical_explanation=(
            "The governed runtime enforces approval workflows, autonomy limits, risk thresholds, "
            "and audit logging. It prevents silent architecture rewrites, self-modification of governance, "
            "and bypassing of approvals."
        ),
        example="If the PM wants to delete a file, the governed runtime checks if deletion requires approval in the current mode.",
        related_concepts=["autonomy-limits", "approval-workflow", "audit-log"],
    ),
    "what-is-traceability": Explanation(
        concept="What is task-to-code traceability?",
        simple_explanation=(
            "Traceability means you can always see which task changed which file and why. "
            "It's like a history book for your project — every change is recorded with context."
        ),
        technical_explanation=(
            "The traceability system maintains an append-only audit log of task starts, file changes, "
            "and task completions. Each entry includes task ID, file path, change type, affected symbols, and timestamp."
        ),
        example="You can ask 'Which task modified auth.py last week?' and see the full history.",
        related_concepts=["audit-log", "task-management", "file-history"],
    ),
}


# ---------------------------------------------------------------------------
# Educational Mode Manager
# ---------------------------------------------------------------------------

class EducationalMode:
    """
    Manages educational features: tutorials, explanations, guided workflows.

    Usage:
        edu = EducationalMode()
        tutorial = edu.get_tutorial("first-project-import")
        explanation = edu.explain("what-is-pm")
    """

    def __init__(self) -> None:
        self._tutorials: dict[str, TutorialFlow] = dict(BUILTIN_TUTORIALS)
        self._explanations: dict[str, Explanation] = dict(BUILTIN_EXPLANATIONS)

    # -- Tutorials -----------------------------------------------------------

    def get_tutorial(self, flow_id: str) -> Optional[TutorialFlow]:
        """Get a tutorial flow by ID."""
        return self._tutorials.get(flow_id)

    def list_tutorials(self, difficulty: Optional[str] = None) -> list[dict[str, Any]]:
        """List available tutorials, optionally filtered by difficulty."""
        tutorials = list(self._tutorials.values())
        if difficulty:
            tutorials = [t for t in tutorials if t.difficulty == difficulty]
        return [
            {
                "flow_id": t.flow_id,
                "title": t.title,
                "description": t.description,
                "difficulty": t.difficulty,
                "step_count": len(t.steps),
                "tags": t.tags,
            }
            for t in tutorials
        ]

    def get_step(self, flow_id: str, step_id: str) -> Optional[TutorialStep]:
        """Get a specific step from a tutorial flow."""
        flow = self._tutorials.get(flow_id)
        if flow:
            for step in flow.steps:
                if step.step_id == step_id:
                    return step
        return None

    def complete_step(self, flow_id: str, step_id: str) -> bool:
        """Mark a tutorial step as completed."""
        flow = self._tutorials.get(flow_id)
        if flow:
            for step in flow.steps:
                if step.step_id == step_id:
                    step.completed = True
                    return True
        return False

    def get_progress(self, flow_id: str) -> dict[str, Any]:
        """Get completion progress for a tutorial flow."""
        flow = self._tutorials.get(flow_id)
        if not flow:
            return {"flow_id": flow_id, "total": 0, "completed": 0, "percent": 0}

        total = len(flow.steps)
        completed = sum(1 for s in flow.steps if s.completed)
        percent = round(completed / total * 100) if total > 0 else 0

        return {
            "flow_id": flow_id,
            "title": flow.title,
            "total": total,
            "completed": completed,
            "percent": percent,
        }

    # -- Explanations ---------------------------------------------------------

    def explain(self, concept_id: str, detail_level: str = "simple") -> Optional[dict[str, Any]]:
        """
        Get an explanation for a concept.

        Args:
            concept_id: The concept identifier.
            detail_level: 'simple' (ELI5), 'technical', or 'full'.

        Returns:
            Explanation dict or None if concept not found.
        """
        exp = self._explanations.get(concept_id)
        if not exp:
            return None

        result = exp.to_dict()
        if detail_level == "simple":
            result.pop("technical_explanation", None)
        elif detail_level == "technical":
            result.pop("simple_explanation", None)

        return result

    def list_explanations(self) -> list[dict[str, str]]:
        """List all available explanations."""
        return [
            {
                "concept_id": k,
                "concept": v.concept,
                "difficulty": v.difficulty,
            }
            for k, v in self._explanations.items()
        ]

    def search_explanations(self, query: str) -> list[dict[str, Any]]:
        """Search explanations by keyword."""
        query_lower = query.lower()
        results = []
        for k, v in self._explanations.items():
            if (query_lower in v.concept.lower()
                    or query_lower in v.simple_explanation.lower()
                    or any(query_lower in r.lower() for r in v.related_concepts)):
                results.append(v.to_dict())
        return results

    # -- Guided workflow integration ------------------------------------------

    def get_guided_workflow(self, workflow_type: str) -> Optional[dict[str, Any]]:
        """
        Get a guided workflow template for common operations.

        Args:
            workflow_type: One of 'import', 'feature', 'repair', 'test', 'deploy'.

        Returns:
            Guided workflow dict with steps and educational content.
        """
        workflows = {
            "import": {
                "type": "import",
                "title": "Import a Project",
                "description": "Safely import and analyze a project",
                "tutorial_id": "first-project-import",
                "steps": [
                    {"id": "import-1", "action": "select_source", "explanation": "Choose where your project is located"},
                    {"id": "import-2", "action": "analyze", "explanation": "PM scans the project structure"},
                    {"id": "import-3", "action": "review", "explanation": "Review the project understanding snapshot"},
                ],
            },
            "feature": {
                "type": "feature",
                "title": "Add a Feature",
                "description": "Plan and implement a new feature",
                "tutorial_id": "first-feature",
                "steps": [
                    {"id": "feat-1", "action": "describe", "explanation": "Describe what you want to build"},
                    {"id": "feat-2", "action": "plan", "explanation": "PM creates a development plan"},
                    {"id": "feat-3", "action": "approve", "explanation": "Review and approve the plan"},
                    {"id": "feat-4", "action": "execute", "explanation": "Execute through governed runtime"},
                ],
            },
            "repair": {
                "type": "repair",
                "title": "Repair a Project",
                "description": "Fix issues in a broken project",
                "tutorial_id": "first-repair",
                "steps": [
                    {"id": "rep-1", "action": "scan", "explanation": "PM scans for issues"},
                    {"id": "rep-2", "action": "plan", "explanation": "Review the repair plan"},
                    {"id": "rep-3", "action": "execute", "explanation": "Execute repairs with rollback"},
                ],
            },
        }
        return workflows.get(workflow_type)
