"""
Feature Development Mode (P4) — Phase 8

Main feature-development workflow:
  1. User describes a feature request in natural language
  2. PM understands affected modules (via project understanding)
  3. PM builds a workflow plan
  4. PM shows the plan and breaks it into stages
  5. PM executes through governed runtime

Key principle: NOT "autonomously rewrite the entire app".
PM assists, human approves, governed runtime executes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from core.project_manager.workspace.project_understanding import ProjectUnderstanding
from core.project_manager.workspace.task_traceability import TaskTraceability


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FeatureStage:
    """A single stage in a feature development plan."""
    stage_id: str
    name: str
    description: str
    affected_files: list[str] = field(default_factory=list)
    affected_modules: list[str] = field(default_factory=list)
    estimated_risk: str = "low"          # low | medium | high
    requires_approval: bool = False
    status: str = "pending"             # pending | in_progress | completed | failed
    dependencies: list[str] = field(default_factory=list)  # stage_ids this depends on

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "description": self.description,
            "affected_files": self.affected_files,
            "affected_modules": self.affected_modules,
            "estimated_risk": self.estimated_risk,
            "requires_approval": self.requires_approval,
            "status": self.status,
            "dependencies": self.dependencies,
        }


@dataclass
class FeaturePlan:
    """Complete feature development plan."""
    feature_id: str
    title: str
    description: str
    stages: list[FeatureStage] = field(default_factory=list)
    overall_risk: str = "low"
    total_files_affected: int = 0
    total_modules_affected: int = 0
    requires_human_approval: bool = True
    status: str = "draft"              # draft | approved | in_progress | completed | cancelled

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "title": self.title,
            "description": self.description,
            "stages": [s.to_dict() for s in self.stages],
            "overall_risk": self.overall_risk,
            "total_files_affected": self.total_files_affected,
            "total_modules_affected": self.total_modules_affected,
            "requires_human_approval": self.requires_human_approval,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Feature keyword patterns (deterministic matching)
# ---------------------------------------------------------------------------

# Maps keywords to likely affected module directories/paths
FEATURE_KEYWORD_MAP: dict[str, list[str]] = {
    # Auth
    "auth": ["auth", "login", "session", "middleware"],
    "login": ["auth", "login", "session", "views"],
    "logout": ["auth", "session", "views"],
    "register": ["auth", "views", "models"],
    "password": ["auth", "models", "views"],
    # CRUD
    "crud": ["models", "views", "controllers", "api"],
    "create": ["models", "views", "controllers"],
    "delete": ["models", "views", "controllers"],
    "update": ["models", "views", "controllers"],
    # API
    "api": ["api", "routes", "controllers", "views"],
    "endpoint": ["api", "routes", "controllers"],
    "rest": ["api", "routes", "serializers"],
    "graphql": ["graphql", "schema", "resolvers"],
    # UI
    "ui": ["templates", "static", "views", "components"],
    "page": ["templates", "views", "routes"],
    "form": ["forms", "templates", "views"],
    "button": ["templates", "static", "components"],
    "style": ["static", "css", "scss"],
    # Database
    "database": ["models", "migrations", "db"],
    "migration": ["migrations", "models"],
    "model": ["models", "migrations"],
    "schema": ["models", "migrations", "schema"],
    # Tasks / scheduling
    "task": ["tasks", "workers", "jobs", "scheduler"],
    "schedule": ["tasks", "scheduler", "cron"],
    "recurring": ["tasks", "scheduler", "models"],
    "background": ["tasks", "workers", "jobs"],
    # Notifications
    "notification": ["notifications", "email", "messages"],
    "email": ["email", "notifications", "mail"],
    "push": ["notifications", "push"],
    # Testing
    "test": ["tests", "testing"],
    "coverage": ["tests", ".coveragerc"],
    # Config
    "config": ["config", "settings", ".env"],
    "setting": ["config", "settings"],
}

# Risk keywords that elevate risk
HIGH_RISK_KEYWORDS = {"delete", "remove", "drop", "migration", "schema", "auth", "security", "password"}
MEDIUM_RISK_KEYWORDS = {"update", "modify", "change", "refactor", "api", "endpoint", "model"}


# ---------------------------------------------------------------------------
# Feature Developer
# ---------------------------------------------------------------------------

class FeatureDeveloper:
    """
    Analyzes feature requests and produces governed development plans.

    Usage:
        dev = FeatureDeveloper("/path/to/project")
        plan = dev.analyze_feature("Add recurring tasks to planner")
        print(dev.format_plan_for_display(plan))
    """

    def __init__(self, project_path: str) -> None:
        self.project_path = project_path
        self._understanding = ProjectUnderstanding()

    def analyze_feature(self, feature_description: str) -> FeaturePlan:
        """
        Analyze a feature request and produce a development plan.

        Args:
            feature_description: Natural language feature description.

        Returns:
            FeaturePlan with stages, affected modules, and risk assessment.
        """
        import uuid
        plan = FeaturePlan(
            feature_id=f"FEAT-{uuid.uuid4().hex[:8]}",
            title=feature_description,
            description=feature_description,
        )

        # Step 1: Understand the project
        snapshot = self._understanding.analyze(self.project_path)

        # Step 2: Identify affected modules from keywords
        affected_modules = self._identify_affected_modules(feature_description, snapshot)
        plan.total_modules_affected = len(affected_modules)

        # Step 3: Identify affected files
        affected_files = self._identify_affected_files(affected_modules, snapshot)
        plan.total_files_affected = len(affected_files)

        # Step 4: Assess risk
        plan.overall_risk = self._assess_risk(feature_description, affected_modules, snapshot)

        # Step 5: Build stages
        plan.stages = self._build_stages(feature_description, affected_modules, affected_files, snapshot)

        # Step 6: Determine if human approval is needed
        plan.requires_human_approval = (
            plan.overall_risk in ("medium", "high")
            or any(s.requires_approval for s in plan.stages)
        )

        return plan

    def _identify_affected_modules(
        self, description: str, snapshot: Any
    ) -> list[str]:
        """Identify which project modules are likely affected."""
        desc_lower = description.lower()
        matched_dirs: set[str] = set()

        for keyword, dirs in FEATURE_KEYWORD_MAP.items():
            if keyword in desc_lower:
                matched_dirs.update(dirs)

        # Filter to only directories that actually exist in the project
        existing_dirs = set(snapshot.root_directories)
        affected = sorted(matched_dirs & existing_dirs)

        # If no specific match, return all source directories
        if not affected:
            exclude = {"tests", "__pycache__", ".git", "node_modules", "venv", ".venv", "dist", "build"}
            affected = sorted(d for d in snapshot.root_directories if d not in exclude)

        return affected

    def _identify_affected_files(
        self, modules: list[str], snapshot: Any
    ) -> list[str]:
        """Identify files in affected modules."""
        files: list[str] = []
        import os
        for module in modules:
            module_path = os.path.join(self.project_path, module)
            if os.path.isdir(module_path):
                for root, dirs, filenames in os.walk(module_path):
                    for f in filenames:
                        if f.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java")):
                            files.append(os.path.relpath(os.path.join(root, f), self.project_path))
        return files

    def _assess_risk(self, description: str, modules: list[str], snapshot: Any) -> str:
        """Assess overall risk of the feature."""
        desc_lower = description.lower()

        # Check for high-risk keywords
        if any(kw in desc_lower for kw in HIGH_RISK_KEYWORDS):
            return "high"

        # Check for medium-risk keywords
        if any(kw in desc_lower for kw in MEDIUM_RISK_KEYWORDS):
            return "medium"

        # Many affected modules = higher risk
        if len(modules) > 3:
            return "medium"

        return "low"

    def _build_stages(
        self,
        description: str,
        modules: list[str],
        files: list[str],
        snapshot: Any,
    ) -> list[FeatureStage]:
        """Build development stages based on the feature analysis."""
        stages: list[FeatureStage] = []
        desc_lower = description.lower()

        # Stage 1: Analysis & Planning (always)
        stages.append(FeatureStage(
            stage_id="stage-1",
            name="Analysis & Planning",
            description="Analyze affected modules, review existing code, create detailed implementation plan",
            affected_modules=modules,
            estimated_risk="low",
            requires_approval=False,
        ))

        # Stage 2: Model/Schema changes (if applicable)
        if any(kw in desc_lower for kw in ["model", "database", "schema", "migration", "add", "create"]):
            model_modules = [m for m in modules if m in ("models", "migrations", "db", "schema")]
            if not model_modules:
                model_modules = modules[:1] if modules else []
            stages.append(FeatureStage(
                stage_id="stage-2",
                name="Data Layer",
                description="Update models, create migrations, update database schema",
                affected_modules=model_modules,
                estimated_risk="medium",
                requires_approval=True,
                dependencies=["stage-1"],
            ))

        # Stage 3: Business logic
        logic_modules = [m for m in modules if m in ("services", "logic", "controllers", "views", "api")]
        if not logic_modules:
            logic_modules = modules[:2] if len(modules) >= 2 else modules
        stages.append(FeatureStage(
            stage_id="stage-3",
            name="Business Logic",
            description="Implement core feature logic, update controllers/views/API handlers",
            affected_modules=logic_modules,
            estimated_risk="medium",
            requires_approval=True,
            dependencies=["stage-1"],
        ))

        # Stage 4: UI changes (if applicable)
        if any(kw in desc_lower for kw in ["ui", "page", "form", "button", "view", "template", "style"]):
            ui_modules = [m for m in modules if m in ("templates", "static", "views", "components")]
            if not ui_modules:
                ui_modules = modules[:1] if modules else []
            stages.append(FeatureStage(
                stage_id="stage-4",
                name="User Interface",
                description="Update templates, forms, styles, and frontend components",
                affected_modules=ui_modules,
                estimated_risk="low",
                requires_approval=False,
                dependencies=["stage-3"],
            ))

        # Stage 5: Tests
        stages.append(FeatureStage(
            stage_id="stage-tests",
            name="Tests & Validation",
            description="Write/update tests, run validation suite, verify feature works",
            affected_modules=["tests"] if "tests" in snapshot.root_directories else [],
            estimated_risk="low",
            requires_approval=False,
            dependencies=[s.stage_id for s in stages],
        ))

        return stages

    def format_plan_for_display(self, plan: FeaturePlan) -> str:
        """Format a FeaturePlan as a human-readable string."""
        lines: list[str] = []
        sep = "=" * 60

        lines.append(sep)
        lines.append("  FEATURE DEVELOPMENT PLAN")
        lines.append(sep)
        lines.append("")
        lines.append(f"  Feature:    {plan.title}")
        lines.append(f"  ID:         {plan.feature_id}")
        lines.append(f"  Risk:       {plan.overall_risk.upper()}")
        lines.append(f"  Modules:    {plan.total_modules_affected}")
        lines.append(f"  Files:      {plan.total_files_affected}")
        lines.append(f"  Approval:   {'Required' if plan.requires_human_approval else 'Not required'}")
        lines.append("")
        lines.append(f"  Stages ({len(plan.stages)}):")
        lines.append("  " + "-" * 40)

        for stage in plan.stages:
            risk_tag = f"[{stage.estimated_risk.upper()}]"
            appr_tag = " [NEEDS APPROVAL]" if stage.requires_approval else ""
            lines.append(f"    {stage.stage_id}: {stage.name} {risk_tag}{appr_tag}")
            lines.append(f"      {stage.description}")
            if stage.affected_modules:
                lines.append(f"      Modules: {', '.join(stage.affected_modules)}")
            if stage.dependencies:
                lines.append(f"      Depends on: {', '.join(stage.dependencies)}")
            lines.append("")

        lines.append(sep)
        return "\n".join(lines)
