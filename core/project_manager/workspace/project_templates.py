"""
Real Project Templates (P12) — Phase 8

Starter workflows for common project types and operations.
Each template defines a sequence of steps with educational guidance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TemplateStep:
    """A single step in a project template."""
    step_id: str
    name: str
    description: str
    action_type: str          # analyze | modify | create | test | verify
    target_pattern: str = ""  # File pattern this step applies to
    estimated_risk: str = "low"
    requires_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "action_type": self.action_type,
            "target_pattern": self.target_pattern,
            "estimated_risk": self.estimated_risk,
            "requires_approval": self.requires_approval,
        }


@dataclass
class ProjectTemplate:
    """A reusable project workflow template."""
    template_id: str
    name: str
    description: str
    category: str             # repair | migration | setup | cleanup | test | refactor
    tags: list[str] = field(default_factory=list)
    steps: list[TemplateStep] = field(default_factory=list)
    applicable_languages: list[str] = field(default_factory=lambda: ["any"])
    estimated_duration: str = ""  # e.g., "5-10 minutes"

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "steps": [s.to_dict() for s in self.steps],
            "applicable_languages": self.applicable_languages,
            "estimated_duration": self.estimated_duration,
        }


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES: dict[str, ProjectTemplate] = {
    "react-app-repair": ProjectTemplate(
        template_id="react-app-repair",
        name="React App Repair",
        description="Fix common issues in a React application: broken imports, missing deps, outdated patterns",
        category="repair",
        tags=["react", "javascript", "frontend", "repair"],
        applicable_languages=["javascript", "typescript"],
        estimated_duration="10-20 minutes",
        steps=[
            TemplateStep("s1", "Scan project structure", "Analyze the React project structure and identify issues", "analyze", estimated_risk="low", requires_approval=False),
            TemplateStep("s2", "Fix broken imports", "Find and fix broken import statements", "modify", "*.{js,jsx,ts,tsx}", estimated_risk="medium"),
            TemplateStep("s3", "Update dependencies", "Check package.json for missing or outdated dependencies", "modify", "package.json", estimated_risk="medium"),
            TemplateStep("s4", "Fix deprecated patterns", "Replace deprecated React patterns (class components, old hooks)", "modify", "*.{js,jsx,ts,tsx}", estimated_risk="medium"),
            TemplateStep("s5", "Run tests", "Run the test suite to verify everything works", "test", estimated_risk="low", requires_approval=False),
        ],
    ),
    "fastapi-migration": ProjectTemplate(
        template_id="fastapi-migration",
        name="FastAPI Migration",
        description="Migrate a Flask/Django project to FastAPI patterns",
        category="migration",
        tags=["fastapi", "python", "api", "migration"],
        applicable_languages=["python"],
        estimated_duration="30-60 minutes",
        steps=[
            TemplateStep("s1", "Analyze current API", "Map existing endpoints and data models", "analyze", "*.py", estimated_risk="low", requires_approval=False),
            TemplateStep("s2", "Create Pydantic models", "Generate Pydantic models from existing data structures", "create", "models.py", estimated_risk="medium"),
            TemplateStep("s3", "Convert routes", "Convert Flask/Django routes to FastAPI endpoints", "modify", "*.py", estimated_risk="high"),
            TemplateStep("s4", "Add validation", "Add request/response validation with Pydantic", "modify", "*.py", estimated_risk="medium"),
            TemplateStep("s5", "Update tests", "Update tests to use FastAPI TestClient", "modify", "tests/", estimated_risk="medium"),
            TemplateStep("s6", "Verify", "Run full test suite and verify API compatibility", "verify", estimated_risk="low", requires_approval=False),
        ],
    ),
    "dependency-update": ProjectTemplate(
        template_id="dependency-update",
        name="Dependency Update",
        description="Safely update project dependencies with compatibility checking",
        category="maintenance",
        tags=["dependencies", "update", "maintenance"],
        applicable_languages=["any"],
        estimated_duration="15-30 minutes",
        steps=[
            TemplateStep("s1", "Audit current dependencies", "List all current dependencies and their versions", "analyze", estimated_risk="low", requires_approval=False),
            TemplateStep("s2", "Check for updates", "Check which packages have newer versions available", "analyze", estimated_risk="low", requires_approval=False),
            TemplateStep("s3", "Update dependencies", "Update dependency files (requirements.txt, package.json, etc.)", "modify", estimated_risk="medium"),
            TemplateStep("s4", "Install and test", "Install updated dependencies and run tests", "test", estimated_risk="medium"),
            TemplateStep("s5", "Fix breaking changes", "Fix any breaking changes from dependency updates", "modify", estimated_risk="high"),
        ],
    ),
    "test-generation": ProjectTemplate(
        template_id="test-generation",
        name="Test Generation",
        description="Generate tests for untested code",
        category="test",
        tags=["testing", "quality", "coverage"],
        applicable_languages=["any"],
        estimated_duration="20-40 minutes",
        steps=[
            TemplateStep("s1", "Find untested code", "Identify functions and classes without test coverage", "analyze", estimated_risk="low", requires_approval=False),
            TemplateStep("s2", "Generate test stubs", "Create test file structure for untested modules", "create", "tests/", estimated_risk="low"),
            TemplateStep("s3", "Write unit tests", "Write unit tests for core functions", "create", "tests/", estimated_risk="medium"),
            TemplateStep("s4", "Write integration tests", "Write integration tests for API endpoints", "create", "tests/", estimated_risk="medium"),
            TemplateStep("s5", "Run and verify", "Run the full test suite and check coverage", "verify", estimated_risk="low", requires_approval=False),
        ],
    ),
    "typescript-conversion": ProjectTemplate(
        template_id="typescript-conversion",
        name="TypeScript Conversion",
        description="Convert a JavaScript project to TypeScript",
        category="migration",
        tags=["typescript", "javascript", "migration", "types"],
        applicable_languages=["javascript"],
        estimated_duration="45-90 minutes",
        steps=[
            TemplateStep("s1", "Setup TypeScript", "Add tsconfig.json and TypeScript dependencies", "create", "tsconfig.json", estimated_risk="low"),
            TemplateStep("s2", "Rename files", "Rename .js files to .ts (or .tsx for React)", "modify", "*.js", estimated_risk="medium"),
            TemplateStep("s3", "Add type annotations", "Add type annotations to function parameters and returns", "modify", "*.ts", estimated_risk="medium"),
            TemplateStep("s4", "Fix type errors", "Fix all TypeScript compiler errors", "modify", "*.ts", estimated_risk="medium"),
            TemplateStep("s5", "Update build config", "Update build configuration for TypeScript", "modify", estimated_risk="medium"),
            TemplateStep("s6", "Verify", "Run type check and test suite", "verify", estimated_risk="low", requires_approval=False),
        ],
    ),
    "api-refactor": ProjectTemplate(
        template_id="api-refactor",
        name="API Refactor",
        description="Refactor an API for consistency and best practices",
        category="refactor",
        tags=["api", "refactor", "rest", "best-practices"],
        applicable_languages=["any"],
        estimated_duration="30-60 minutes",
        steps=[
            TemplateStep("s1", "Analyze API structure", "Map all endpoints, request/response formats", "analyze", estimated_risk="low", requires_approval=False),
            TemplateStep("s2", "Standardize responses", "Ensure all endpoints return consistent response format", "modify", estimated_risk="medium"),
            TemplateStep("s3", "Add error handling", "Add proper error handling and status codes", "modify", estimated_risk="medium"),
            TemplateStep("s4", "Add validation", "Add input validation for all endpoints", "modify", estimated_risk="medium"),
            TemplateStep("s5", "Update documentation", "Update API documentation to match changes", "modify", estimated_risk="low"),
            TemplateStep("s6", "Verify", "Run integration tests to verify API behavior", "verify", estimated_risk="low", requires_approval=False),
        ],
    ),
    "electron-cleanup": ProjectTemplate(
        template_id="electron-cleanup",
        name="Electron Cleanup",
        description="Clean up and modernize an Electron application",
        category="cleanup",
        tags=["electron", "desktop", "cleanup", "modernize"],
        applicable_languages=["javascript", "typescript"],
        estimated_duration="20-40 minutes",
        steps=[
            TemplateStep("s1", "Audit dependencies", "Check for outdated Electron and npm dependencies", "analyze", estimated_risk="low", requires_approval=False),
            TemplateStep("s2", "Update Electron", "Update to latest stable Electron version", "modify", "package.json", estimated_risk="high"),
            TemplateStep("s3", "Fix security issues", "Fix common Electron security issues (nodeIntegration, contextIsolation)", "modify", estimated_risk="high"),
            TemplateStep("s4", "Clean unused files", "Remove unused files and dead code", "modify", estimated_risk="medium"),
            TemplateStep("s5", "Verify", "Build and test the application", "verify", estimated_risk="low", requires_approval=False),
        ],
    ),
}


class TemplateManager:
    """
    Manages project workflow templates.

    Usage:
        tm = TemplateManager()
        templates = tm.list_templates(category="repair")
        template = tm.get_template("react-app-repair")
    """

    def __init__(self) -> None:
        self._templates: dict[str, ProjectTemplate] = dict(BUILTIN_TEMPLATES)

    def get_template(self, template_id: str) -> Optional[ProjectTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List available templates with optional filtering."""
        results = list(self._templates.values())

        if category:
            results = [t for t in results if t.category == category]
        if language:
            results = [t for t in results if "any" in t.applicable_languages or language in t.applicable_languages]
        if tag:
            results = [t for t in results if tag in t.tags]

        return [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "tags": t.tags,
                "step_count": len(t.steps),
                "applicable_languages": t.applicable_languages,
                "estimated_duration": t.estimated_duration,
            }
            for t in results
        ]

    def get_categories(self) -> list[str]:
        """Get all available template categories."""
        return sorted(set(t.category for t in self._templates.values()))

    def get_tags(self) -> list[str]:
        """Get all available template tags."""
        tags: set[str] = set()
        for t in self._templates.values():
            tags.update(t.tags)
        return sorted(tags)
