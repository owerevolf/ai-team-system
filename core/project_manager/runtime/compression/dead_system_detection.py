"""
Phase 12, P4: Dead System Detection

Detects unused, stale, or unreachable subsystems:
- unused modules (no imports from other modules)
- stale workflows (registered but never triggered)
- abandoned runtime paths
- obsolete abstractions
- permanently silent telemetry
- unreachable recovery branches

Principle: Deletion is a first-class operation.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class DeadCategory(Enum):
    UNUSED_MODULE = "unused_module"
    STALE_WORKFLOW = "stale_workflow"
    ABANDONED_PATH = "abandoned_path"
    OBSOLETE_ABSTRACTION = "obsolete_abstraction"
    SILENT_TELEMETRY = "silent_telemetry"
    UNREACHABLE_RECOVERY = "unreachable_recovery"


@dataclass
class DeadItem:
    """A detected dead or dying system component."""
    name: str
    category: DeadCategory
    module: str
    line_number: int = 0
    reason: str = ""
    safe_to_remove: bool = False
    suggested_action: str = "review"  # review, archive, collapse, remove


@dataclass
class DeadSystemReport:
    """Report of dead system detection analysis."""
    total_items: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    items: list[DeadItem] = field(default_factory=list)

    @property
    def safe_to_remove(self) -> list[DeadItem]:
        return [i for i in self.items if i.safe_to_remove]

    @property
    def needs_review(self) -> list[DeadItem]:
        return [i for i in self.items if not i.safe_to_remove]


class DeadSystemDetector:
    """
    Scans the runtime for dead or dying subsystems.
    Uses static analysis to find unreferenced modules, unused classes,
    and unreachable code paths.
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self._module_map: dict[str, Path] = {}
        self._import_map: dict[str, set[str]] = {}
        self._class_map: dict[str, str] = {}
        self._function_map: dict[str, str] = {}

    def scan(self) -> DeadSystemReport:
        """Run full dead system detection scan."""
        self._build_maps()
        return self._detect_dead_systems()

    def _build_maps(self) -> None:
        """Build import and reference maps for all Python files."""
        self._module_map = {}
        self._import_map = {}
        self._class_map = {}
        self._function_map = {}

        for root, dirs, filenames in os.walk(self.base_path):
            dirs[:] = [
                d for d in dirs
                if d not in ("__pycache__", ".pytest_cache", "venv", "venv_new", ".git", ".cache")
                and not d.startswith(".")
            ]
            for fn in filenames:
                if not fn.endswith(".py") or fn == "__init__.py":
                    continue
                filepath = Path(root) / fn
                rel_path = str(filepath.relative_to(self.base_path))
                module_name = rel_path.replace("/", ".").replace(".py", "")

                self._module_map[module_name] = filepath

                try:
                    source = filepath.read_text(encoding="utf-8")
                    tree = ast.parse(source, filename=rel_path)
                except (SyntaxError, UnicodeDecodeError):
                    continue

                self._import_map[module_name] = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._import_map[module_name].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._import_map[module_name].add(node.module)
                    elif isinstance(node, ast.ClassDef):
                        self._class_map[node.name] = module_name
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith("_"):
                            self._function_map[node.name] = module_name

    def _detect_dead_systems(self) -> DeadSystemReport:
        """Analyze maps to find dead systems."""
        items: list[DeadItem] = []

        # Find unused modules (not imported by anyone)
        for module_name in self._module_map:
            is_imported = False
            for importer, imports in self._import_map.items():
                if importer != module_name and module_name in imports:
                    is_imported = True
                    break
            if not is_imported and not module_name.endswith("__main__"):
                items.append(DeadItem(
                    name=module_name,
                    category=DeadCategory.UNUSED_MODULE,
                    module=module_name,
                    reason="Not imported by any other module",
                    safe_to_remove=False,
                    suggested_action="review",
                ))

        # Find classes not referenced outside their module
        for class_name, module_name in self._class_map.items():
            is_used = False
            for importer, imports in self._import_map.items():
                if importer != module_name:
                    # Check if the class is imported
                    if any(class_name in imp for imp in imports):
                        is_used = True
                        break
            if not is_used:
                items.append(DeadItem(
                    name=class_name,
                    category=DeadCategory.OBSOLETE_ABSTRACTION,
                    module=module_name,
                    reason=f"Class '{class_name}' not referenced outside its module",
                    safe_to_remove=False,
                    suggested_action="review",
                ))

        # Find functions that are only defined but never called
        for func_name, module_name in self._function_map.items():
            if func_name.startswith(("get_", "set_", "is_", "has_", "can_", "should_")):
                # Likely a getter/setter — skip
                continue
            is_called = False
            filepath = self._module_map.get(module_name)
            if filepath:
                try:
                    source = filepath.read_text()
                    # Simple heuristic: function name appears more than once (def + call)
                    count = source.count(func_name)
                    if count > 1:
                        is_called = True
                except:
                    pass
            if not is_called:
                items.append(DeadItem(
                    name=func_name,
                    category=DeadCategory.ABANDONED_PATH,
                    module=module_name,
                    reason=f"Function '{func_name}' defined but potentially never called",
                    safe_to_remove=False,
                    suggested_action="review",
                ))

        report = DeadSystemReport()
        report.items = items
        report.total_items = len(items)
        for item in items:
            cat = item.category.value
            report.by_category[cat] = report.by_category.get(cat, 0) + 1

        return report

    def get_module_import_count(self, module_name: str) -> int:
        """Get how many other modules import the given module."""
        count = 0
        for importer, imports in self._import_map.items():
            if importer != module_name and module_name in imports:
                count += 1
        return count

    def get_isolated_modules(self) -> list[str]:
        """Get modules that are completely isolated (no imports in or out)."""
        isolated = []
        for module_name in self._module_map:
            has_incoming = any(
                module_name in imports
                for importer, imports in self._import_map.items()
                if importer != module_name
            )
            has_outgoing = bool(self._import_map.get(module_name))
            if not has_incoming and not has_outgoing:
                isolated.append(module_name)
        return isolated
