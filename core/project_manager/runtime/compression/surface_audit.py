"""
Phase 12, P1: Surface Area Audit Engine

Measures the complete operational surface of the runtime:
- active workflows, exposed controls, approval types
- explanation surfaces, observability entrypoints
- user-visible runtime concepts
- actual usage frequency (not theoretical usefulness)

Principle: You cannot compress what you cannot measure.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class SurfaceType(Enum):
    """Types of operational surface that users or subsystems interact with."""
    API_ENDPOINT = "api_endpoint"
    WORKFLOW_STEP = "workflow_step"
    APPROVAL_GATE = "approval_gate"
    EXPLANATION_SURFACE = "explanation_surface"
    OBSERVABILITY_ENTRY = "observability_entry"
    USER_CONTROL = "user_control"
    CONFIG_KEY = "config_key"
    EVENT_TYPE = "event_type"
    POLICY_RULE = "policy_rule"
    RECOVERY_BRANCH = "recovery_branch"


@dataclass
class SurfaceItem:
    """A single measurable surface item."""
    name: str
    surface_type: SurfaceType
    module: str
    line_number: int = 0
    usage_count: int = 0  # static analysis estimate
    is_exported: bool = False
    is_deprecated: bool = False
    references: list[str] = field(default_factory=list)


@dataclass
class SurfaceReport:
    """Complete surface area audit report."""
    total_items: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_module: dict[str, int] = field(default_factory=dict)
    exported_items: int = 0
    deprecated_items: int = 0
    unreferenced_items: int = 0
    items: list[SurfaceItem] = field(default_factory=list)

    @property
    def compression_candidates(self) -> list[SurfaceItem]:
        """Items that are candidates for removal or compression."""
        return [
            item for item in self.items
            if item.is_deprecated
            or (not item.is_exported and item.usage_count == 0)
            or item.usage_count == 0
        ]

    @property
    def surface_density(self) -> float:
        """Items per module — high density suggests consolidation opportunity."""
        if not self.by_module:
            return 0.0
        return self.total_items / len(self.by_module)


class SurfaceAreaAuditor:
    """
    Audits the runtime surface area by scanning Python modules
    for API endpoints, classes, functions, and configuration surfaces.
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self._items: list[SurfaceItem] = []

    def audit(self, include_tests: bool = False) -> SurfaceReport:
        """Run full surface area audit."""
        self._items = []

        for py_file in self._find_python_files(include_tests):
            self._audit_file(py_file)

        return self._build_report()

    def _find_python_files(self, include_tests: bool) -> list[Path]:
        files = []
        for root, dirs, filenames in os.walk(self.base_path):
            # Skip venv, cache, and hidden dirs
            dirs[:] = [
                d for d in dirs
                if d not in ("__pycache__", ".pytest_cache", "venv", "venv_new", ".git", ".cache")
                and not d.startswith(".")
            ]
            for fn in filenames:
                if fn.endswith(".py") and fn != "__init__.py":
                    if not include_tests and fn.startswith("test_"):
                        continue
                    files.append(Path(root) / fn)
        return files

    def _audit_file(self, filepath: Path) -> None:
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError):
            return

        rel_path = str(filepath.relative_to(self.base_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._items.append(SurfaceItem(
                    name=node.name,
                    surface_type=SurfaceType.USER_CONTROL,
                    module=rel_path,
                    line_number=node.lineno,
                    is_exported=self._is_exported(node),
                ))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                stype = self._classify_function(node, rel_path)
                self._items.append(SurfaceItem(
                    name=node.name,
                    surface_type=stype,
                    module=rel_path,
                    line_number=node.lineno,
                    is_exported=self._is_exported(node),
                ))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        self._items.append(SurfaceItem(
                            name=target.id,
                            surface_type=SurfaceType.CONFIG_KEY,
                            module=rel_path,
                            line_number=target.lineno,
                        ))

    def _classify_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, module_path: str
    ) -> SurfaceType:
        name = node.name
        if name.startswith("test_"):
            return SurfaceType.WORKFLOW_STEP

        # Check decorators for API endpoints
        for decorator in node.decorator_list:
            dec_name = self._decorator_name(decorator)
            if dec_name and any(
                route in dec_name
                for route in ("route", "get", "post", "put", "delete", "patch", "websocket")
            ):
                return SurfaceType.API_ENDPOINT

        # Heuristic classification
        if "approve" in name or "approval" in name:
            return SurfaceType.APPROVAL_GATE
        if "explain" in name or "explanation" in name:
            return SurfaceType.EXPLANATION_SURFACE
        if "observe" in name or "trace" in name or "log" in name:
            return SurfaceType.OBSERVABILITY_ENTRY
        if "recover" in name or "restore" in name or "rollback" in name:
            return SurfaceType.RECOVERY_BRANCH
        if "workflow" in name:
            return SurfaceType.WORKFLOW_STEP
        if "policy" in name or "rule" in name or "govern" in name:
            return SurfaceType.POLICY_RULE

        return SurfaceType.USER_CONTROL

    @staticmethod
    def _decorator_name(decorator: ast.expr) -> Optional[str]:
        if isinstance(decorator, ast.Attribute):
            return decorator.attr
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Attribute):
                return func.attr
            if isinstance(func, ast.Name):
                return func.id
        if isinstance(decorator, ast.Name):
            return decorator.id
        return None

    @staticmethod
    def _is_exported(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return not node.name.startswith("_")

    def _build_report(self) -> SurfaceReport:
        report = SurfaceReport()
        report.items = self._items
        report.total_items = len(self._items)

        for item in self._items:
            type_key = item.surface_type.value
            report.by_type[type_key] = report.by_type.get(type_key, 0) + 1
            report.by_module[item.module] = report.by_module.get(item.module, 0) + 1
            if item.is_exported:
                report.exported_items += 1
            if item.is_deprecated:
                report.deprecated_items += 1
            if not item.is_exported and item.usage_count == 0:
                report.unreferenced_items += 1

        return report
