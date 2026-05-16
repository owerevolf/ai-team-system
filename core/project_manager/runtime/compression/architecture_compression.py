"""
Phase 12, P9: Architecture Compression Initiative

Finds subsystem overlap and consolidation opportunities:
- duplicate state models
- parallel observability logic
- overlapping governance layers
- repeated adaptation mechanisms

Principle: Merge or collapse — avoid internal federated bureaucracy.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class OverlapType(Enum):
    DUPLICATE_STATE = "duplicate_state"
    PARALLEL_OBSERVABILITY = "parallel_observability"
    OVERLAPPING_GOVERNANCE = "overlapping_governance"
    REPEATED_ADAPTATION = "repeated_adaptation"
    SIMILAR_NAMING = "similar_naming"
    SHARED_CONCEPT = "shared_concept"


class CompressionAction(Enum):
    MERGE = "merge"          # Merge into single module
    COLLAPSE = "collapse"    # Collapse into parent module
    UNIFY = "unify"          # Unify interfaces, keep separate
    KEEP = "keep"            # Keep as-is — justified separation


@dataclass
class OverlapFinding:
    """A detected overlap between subsystems."""
    name: str
    overlap_type: OverlapType
    modules: list[str]
    description: str
    recommended_action: CompressionAction
    estimated_lines_saved: int = 0
    risk: str = "low"  # low, medium, high


@dataclass
class CompressionPlan:
    """Plan for architecture compression."""
    findings: list[OverlapFinding] = field(default_factory=list)
    total_lines_saved: int = 0
    modules_affected: set[str] = field(default_factory=set)

    @property
    def merge_candidates(self) -> list[OverlapFinding]:
        return [f for f in self.findings if f.recommended_action == CompressionAction.MERGE]

    @property
    def collapse_candidates(self) -> list[OverlapFinding]:
        return [f for f in self.findings if f.recommended_action == CompressionAction.COLLAPSE]

    @property
    def unify_candidates(self) -> list[OverlapFinding]:
        return [f for f in self.findings if f.recommended_action == CompressionAction.UNIFY]


class ArchitectureCompressor:
    """
    Analyzes runtime architecture for overlap and compression opportunities.
    Scans modules for similar classes, functions, and patterns.
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self._module_classes: dict[str, list[tuple[str, int]]] = {}
        self._module_functions: dict[str, list[tuple[str, int]]] = {}
        self._module_imports: dict[str, list[str]] = {}

    def analyze(self) -> CompressionPlan:
        """Run full architecture compression analysis."""
        self._scan_modules()
        return self._find_overlaps()

    def _scan_modules(self) -> None:
        """Scan all modules for classes, functions, and imports."""
        self._module_classes = {}
        self._module_functions = {}
        self._module_imports = {}

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

                try:
                    source = filepath.read_text(encoding="utf-8")
                    tree = ast.parse(source, filename=rel_path)
                except (SyntaxError, UnicodeDecodeError):
                    continue

                classes: list[tuple[str, int]] = []
                functions: list[tuple[str, int]] = []
                imports: list[str] = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                        classes.append((node.name, node.lineno))
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith("_"):
                            functions.append((node.name, node.lineno))
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            imports.extend(a.name for a in node.names)
                        elif node.module:
                            imports.append(node.module)

                self._module_classes[rel_path] = classes
                self._module_functions[rel_path] = functions
                self._module_imports[rel_path] = imports

    def _find_overlaps(self) -> CompressionPlan:
        """Find overlaps between modules."""
        findings: list[OverlapFinding] = []
        modules_affected: set[str] = set()

        # Find similar class names across modules
        class_name_map: dict[str, list[str]] = {}
        for module, classes in self._module_classes.items():
            for class_name, _ in classes:
                class_name_map.setdefault(class_name, []).append(module)

        for class_name, modules in class_name_map.items():
            if len(modules) > 1:
                findings.append(OverlapFinding(
                    name=f"Duplicate class: {class_name}",
                    overlap_type=OverlapType.DUPLICATE_STATE,
                    modules=modules,
                    description=f"Class '{class_name}' defined in {len(modules)} modules",
                    recommended_action=CompressionAction.MERGE,
                    estimated_lines_saved=self._estimate_class_lines(modules, class_name),
                ))
                modules_affected.update(modules)

        # Find similar function signatures across modules
        function_name_map: dict[str, list[str]] = {}
        for module, functions in self._module_functions.items():
            for func_name, _ in functions:
                function_name_map.setdefault(func_name, []).append(module)

        for func_name, modules in function_name_map.items():
            if len(modules) > 1 and not func_name.startswith(("get_", "set_", "is_", "has_")):
                findings.append(OverlapFinding(
                    name=f"Duplicate function: {func_name}",
                    overlap_type=OverlapType.SHARED_CONCEPT,
                    modules=modules,
                    description=f"Function '{func_name}' defined in {len(modules)} modules",
                    recommended_action=CompressionAction.UNIFY,
                    estimated_lines_saved=0,
                ))
                modules_affected.update(modules)

        # Detect conceptual overlap by module naming patterns
        findings.extend(self._detect_conceptual_overlap())

        total_saved = sum(f.estimated_lines_saved for f in findings)

        return CompressionPlan(
            findings=findings,
            total_lines_saved=total_saved,
            modules_affected=modules_affected,
        )

    def _detect_conceptual_overlap(self) -> list[OverlapFinding]:
        """Detect conceptual overlap based on module names and class patterns."""
        findings: list[OverlapFinding] = []

        # Known conceptual overlap patterns
        overlap_patterns = [
            (
                ["explainability", "explanation"],
                OverlapType.PARALLEL_OBSERVABILITY,
                "Explainability/explanation logic spread across modules",
            ),
            (
                ["observability", "visibility", "audit"],
                OverlapType.PARALLEL_OBSERVABILITY,
                "Observability/visibility/audit logic overlap",
            ),
            (
                ["simplification", "simplicity", "compression"],
                OverlapType.SHARED_CONCEPT,
                "Simplification/compression logic overlap",
            ),
            (
                ["cognitive", "attention", "human_time"],
                OverlapType.REPEATED_ADAPTATION,
                "Cognitive load / attention / human time protection overlap",
            ),
            (
                ["noise", "calm", "quiet"],
                OverlapType.REPEATED_ADAPTATION,
                "Noise reduction / calm mode overlap",
            ),
            (
                ["approval", "governance", "trust"],
                OverlapType.OVERLAPPING_GOVERNANCE,
                "Approval/governance/trust boundary overlap",
            ),
        ]

        all_classes_flat: dict[str, str] = {}
        for module, classes in self._module_classes.items():
            for class_name, _ in classes:
                all_classes_flat[class_name] = module

        for keywords, overlap_type, description in overlap_patterns:
            matching_modules: set[str] = set()
            for class_name, module in all_classes_flat.items():
                for keyword in keywords:
                    if keyword in class_name.lower():
                        matching_modules.add(module)
                        break

            if len(matching_modules) > 1:
                findings.append(OverlapFinding(
                    name=f"Conceptual overlap: {', '.join(keywords)}",
                    overlap_type=overlap_type,
                    modules=sorted(matching_modules),
                    description=description,
                    recommended_action=CompressionAction.COLLAPSE,
                    estimated_lines_saved=len(matching_modules) * 50,  # rough estimate
                ))

        return findings

    def _estimate_class_lines(self, modules: list[str], class_name: str) -> int:
        """Estimate lines that could be saved by merging duplicate classes."""
        total_lines = 0
        for module in modules[1:]:  # Keep first, merge rest
            filepath = self.base_path / module
            if filepath.exists():
                try:
                    source = filepath.read_text()
                    # Rough estimate: find class and count lines until next class
                    in_class = False
                    class_lines = 0
                    for line in source.split("\n"):
                        if f"class {class_name}" in line:
                            in_class = True
                            class_lines = 0
                        elif in_class and line.strip().startswith("class "):
                            break
                        if in_class:
                            class_lines += 1
                    total_lines += class_lines
                except:
                    pass
        return total_lines

    def get_module_cohesion(self, module_path: str) -> float:
        """
        Measure module cohesion — ratio of internal to external imports.
        High cohesion = module is self-contained.
        Low cohesion = module is tightly coupled to others.
        """
        imports = self._module_imports.get(module_path, [])
        if not imports:
            return 1.0

        internal = sum(1 for imp in imports if imp.startswith("core.project_manager"))
        return internal / len(imports)
