"""
Phase 13, P5: Dependency Gravity Analysis

Identifies modules that become dangerously central:
- dependency gravity (how many modules depend on this)
- responsibility concentration
- orchestration overload
- architectural chokepoints

Principle: No single module should become a bottleneck for the entire system.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class GravityLevel(Enum):
    LOW = "low"            # Few dependencies — healthy
    MODERATE = "moderate"  # Some dependencies — monitor
    HIGH = "high"          # Many dependencies — candidate for decomposition
    CRITICAL = "critical"  # Too many dependencies — must decompose


@dataclass
class ModuleGravity:
    """Dependency gravity metrics for a single module."""
    module_path: str
    lines_of_code: int
    incoming_dependencies: int    # How many modules import this
    outgoing_dependencies: int    # How many modules this imports
    responsibility_score: float   # Combined metric
    gravity_level: GravityLevel
    recommendations: list[str] = field(default_factory=list)


@dataclass
class GravityReport:
    """Full dependency gravity analysis report."""
    modules: list[ModuleGravity] = field(default_factory=list)

    @property
    def critical_modules(self) -> list[ModuleGravity]:
        return [m for m in self.modules if m.gravity_level == GravityLevel.CRITICAL]

    @property
    def high_gravity_modules(self) -> list[ModuleGravity]:
        return [m for m in self.modules if m.gravity_level == GravityLevel.HIGH]

    @property
    def top_chokepoints(self) -> list[ModuleGravity]:
        """Top 5 modules by incoming dependency count."""
        return sorted(self.modules, key=lambda m: -m.incoming_dependencies)[:5]


class DependencyGravityAnalyzer:
    """
    Analyzes dependency gravity across runtime modules.
    Identifies architectural chokepoints and concentration risks.
    """

    # Thresholds for gravity levels
    HIGH_INCOMING_THRESHOLD = 5
    CRITICAL_INCOMING_THRESHOLD = 10
    HIGH_LINES_THRESHOLD = 400
    CRITICAL_LINES_THRESHOLD = 800

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)
        self._import_map: dict[str, list[str]] = {}
        self._module_lines: dict[str, int] = {}

    def analyze(self) -> GravityReport:
        """Run full dependency gravity analysis."""
        self._scan_modules()
        return self._compute_gravity()

    def _scan_modules(self) -> None:
        """Scan all modules for imports and line counts."""
        self._import_map = {}
        self._module_lines = {}

        for root, dirs, filenames in os.walk(self.base_path):
            dirs[:] = [
                d for d in dirs
                if d not in ("__pycache__", ".pytest_cache", "venv", "venv_new", ".git")
                and not d.startswith(".")
            ]
            for fn in filenames:
                if not fn.endswith(".py") or fn == "__init__.py":
                    continue
                filepath = Path(root) / fn
                rel_path = str(filepath.relative_to(self.base_path))

                try:
                    source = filepath.read_text(encoding="utf-8")
                    self._module_lines[rel_path] = source.count('\n')
                    tree = ast.parse(source, filename=rel_path)
                except:
                    continue

                imports: list[str] = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)

                self._import_map[rel_path] = imports

    def _compute_gravity(self) -> GravityReport:
        """Compute gravity metrics for all modules."""
        # Count incoming dependencies
        incoming_counts: dict[str, int] = {}
        for module_path, imports in self._import_map.items():
            for imported in imports:
                # Normalize import to module path
                normalized = self._normalize_import(imported)
                if normalized:
                    incoming_counts[normalized] = incoming_counts.get(normalized, 0) + 1

        modules: list[ModuleGravity] = []
        for module_path in self._import_map:
            incoming = incoming_counts.get(module_path, 0)
            outgoing = len(self._import_map.get(module_path, []))
            lines = self._module_lines.get(module_path, 0)

            # Responsibility score: combination of size and centrality
            responsibility = (incoming * 2) + (lines / 100) + (outgoing * 0.5)

            # Determine gravity level
            if incoming >= self.CRITICAL_INCOMING_THRESHOLD or lines >= self.CRITICAL_LINES_THRESHOLD:
                level = GravityLevel.CRITICAL
            elif incoming >= self.HIGH_INCOMING_THRESHOLD or lines >= self.HIGH_LINES_THRESHOLD:
                level = GravityLevel.HIGH
            elif incoming >= 3 or lines >= 200:
                level = GravityLevel.MODERATE
            else:
                level = GravityLevel.LOW

            recommendations = self._generate_recommendations(module_path, incoming, outgoing, lines, level)

            modules.append(ModuleGravity(
                module_path=module_path,
                lines_of_code=lines,
                incoming_dependencies=incoming,
                outgoing_dependencies=outgoing,
                responsibility_score=responsibility,
                gravity_level=level,
                recommendations=recommendations,
            ))

        return GravityReport(modules=modules)

    def _normalize_import(self, import_path: str) -> Optional[str]:
        """Normalize an import path to a module path within the runtime."""
        # Handle core.project_manager.runtime.X imports
        if "project_manager/runtime" in import_path:
            parts = import_path.split(".")
            if "runtime" in parts:
                idx = parts.index("runtime")
                return "/".join(parts[idx:])

        # Handle direct subsystem imports
        for subsys in ("durability", "ergonomics", "trust", "optimization", "compression", "coherence"):
            if import_path.startswith(subsys):
                return import_path.replace(".", "/")

        return None

    def _generate_recommendations(
        self, module_path: str, incoming: int, outgoing: int, lines: int, level: GravityLevel
    ) -> list[str]:
        """Generate recommendations based on gravity metrics."""
        recs: list[str] = []

        if level == GravityLevel.CRITICAL:
            recs.append(f"CRITICAL: {incoming} modules depend on this — decompose immediately")
        elif level == GravityLevel.HIGH:
            recs.append(f"HIGH: {incoming} modules depend on this — consider decomposition")

        if lines >= self.CRITICAL_LINES_THRESHOLD:
            recs.append(f"Module is {lines} lines — extract submodules")
        elif lines >= self.HIGH_LINES_THRESHOLD:
            recs.append(f"Module is {lines} lines — monitor for growth")

        if outgoing >= 10:
            recs.append(f"Module imports {outgoing} other modules — high coupling")

        return recs
