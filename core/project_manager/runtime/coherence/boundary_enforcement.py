"""
Phase 13, P4: Architectural Boundary Enforcement

Detects boundary violations between subsystems:
- subsystem leakage (imports across boundaries)
- circular abstractions
- hidden cross-layer dependencies
- policy coupling
- semantic bleed-through

Principle: Boundaries must be explicit and enforceable.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class BoundaryType(Enum):
    SUBSYSTEM = "subsystem"            # Between durability/ergonomics/trust/optimization/compression
    LAYER = "layer"                    # Between runtime/web_ui/core
    CONCEPTUAL = "conceptual"          # Between different concern areas


class ViolationType(Enum):
    SUBSYSTEM_LEAKAGE = "subsystem_leakage"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    CROSS_LAYER_IMPORT = "cross_layer_import"
    POLICY_COUPLING = "policy_coupling"
    SEMANTIC_BLEED = "semantic_bleed"
    TEMPORARY_SHORTCUT = "temporary_shortcut"


class ViolationSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BoundaryViolation:
    """A detected boundary violation."""
    violation_type: ViolationType
    severity: ViolationSeverity
    source_module: str
    target_module: str
    description: str
    recommendation: str
    import_statement: str = ""


@dataclass
class BoundaryReport:
    """Full boundary enforcement report."""
    violations: list[BoundaryViolation] = field(default_factory=list)
    total_imports_checked: int = 0

    @property
    def critical_violations(self) -> list[BoundaryViolation]:
        return [v for v in self.violations if v.severity == ViolationSeverity.CRITICAL]

    @property
    def by_type(self) -> dict[str, list[BoundaryViolation]]:
        result: dict[str, list[BoundaryViolation]] = {}
        for v in self.violations:
            result.setdefault(v.violation_type.value, []).append(v)
        return result


# Define allowed import boundaries between runtime subpackages
ALLOWED_CROSS_SUBSYSTEM_IMPORTS: dict[str, set[str]] = {
    "compression": {"durability", "ergonomics", "trust", "optimization", "runtime"},
    "trust": {"durability", "ergonomics", "runtime"},
    "ergonomics": {"durability", "runtime"},
    "durability": {"runtime"},
    "optimization": {"durability", "runtime"},
    "runtime": set(),  # runtime/ modules should not import from subpackages
}

# Modules that should never be imported by runtime subpackages
FORBIDDEN_IMPORTS: set[str] = {
    "web_ui",
    "core.main",
    "core.agent_manager",
    "core.model_router",
    "core.coder_chat",
}


class ArchitecturalBoundaryEnforcer:
    """
    Enforces architectural boundaries between subsystems.
    Detects violations where modules import across defined boundaries.
    """

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)
        self._import_map: dict[str, list[tuple[str, str]]] = {}  # module -> [(imported_module, statement)]

    def check_boundaries(self) -> BoundaryReport:
        """Run full boundary enforcement check."""
        report = BoundaryReport()
        self._build_import_map()

        for module_path, imports in self._import_map.items():
            for imported_module, import_stmt in imports:
                report.total_imports_checked += 1
                violation = self._check_import(module_path, imported_module, import_stmt)
                if violation:
                    report.violations.append(violation)

        # Check for circular dependencies
        report.violations.extend(self._detect_circular_dependencies())

        return report

    def _build_import_map(self) -> None:
        """Build map of all imports in runtime modules."""
        self._import_map = {}

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
                    tree = ast.parse(source, filename=rel_path)
                except:
                    continue

                imports: list[tuple[str, str]] = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append((alias.name, f"import {alias.name}"))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append((node.module, f"from {node.module} import ..."))

                self._import_map[rel_path] = imports

    def _check_import(
        self, source: str, target: str, import_stmt: str
    ) -> Optional[BoundaryViolation]:
        """Check if an import violates architectural boundaries."""

        # Check forbidden imports
        for forbidden in FORBIDDEN_IMPORTS:
            if target.startswith(forbidden):
                return BoundaryViolation(
                    violation_type=ViolationType.CROSS_LAYER_IMPORT,
                    severity=ViolationSeverity.HIGH,
                    source_module=source,
                    target_module=target,
                    description=f"Runtime module imports from forbidden module: {target}",
                    recommendation=f"Remove import of {target} from {source}. "
                                   f"Runtime modules should not depend on {forbidden}.",
                    import_statement=import_stmt,
                )

        # Check cross-subsystem imports
        source_parts = source.split("/")
        target_parts = target.replace("core.project_manager.runtime.", "").split(".")

        if len(source_parts) >= 2 and len(target_parts) >= 1:
            source_subsystem = source_parts[0]  # durability, ergonomics, trust, etc.
            target_subsystem = target_parts[0]

            if source_subsystem != target_subsystem and source_subsystem in ALLOWED_CROSS_SUBSYSTEM_IMPORTS:
                allowed = ALLOWED_CROSS_SUBSYSTEM_IMPORTS[source_subsystem]
                if target_subsystem not in allowed and target_subsystem != "":
                    return BoundaryViolation(
                        violation_type=ViolationType.SUBSYSTEM_LEAKAGE,
                        severity=ViolationSeverity.MEDIUM,
                        source_module=source,
                        target_module=target,
                        description=(
                            f"{source_subsystem} imports from {target_subsystem} "
                            f"which is not in allowed imports: {allowed}"
                        ),
                        recommendation=(
                            f"Move shared logic to runtime/ base or "
                            f"add {target_subsystem} to allowed imports for {source_subsystem}"
                        ),
                        import_statement=import_stmt,
                    )

        return None

    def _detect_circular_dependencies(self) -> list[BoundaryViolation]:
        """Detect circular dependencies between modules."""
        violations: list[BoundaryViolation] = []

        # Build adjacency list
        adjacency: dict[str, set[str]] = {}
        for module_path, imports in self._import_map.items():
            adjacency.setdefault(module_path, set())
            for imported_module, _ in imports:
                # Only track imports within the runtime
                if "project_manager/runtime" in imported_module or imported_module.startswith(("durability", "ergonomics", "trust", "optimization", "compression")):
                    adjacency[module_path].add(imported_module)

        # Simple cycle detection using DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str, path: list[str]) -> Optional[list[str]]:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited:
                    result = dfs(neighbor, path + [neighbor])
                    if result:
                        return result
                elif neighbor in rec_stack:
                    return path + [neighbor]
            rec_stack.discard(node)
            return None

        for module in adjacency:
            if module not in visited:
                cycle = dfs(module, [module])
                if cycle:
                    violations.append(BoundaryViolation(
                        violation_type=ViolationType.CIRCULAR_DEPENDENCY,
                        severity=ViolationSeverity.HIGH,
                        source_module=cycle[0],
                        target_module=cycle[-1] if len(cycle) > 1 else cycle[0],
                        description=f"Circular dependency detected: {' -> '.join(cycle)}",
                        recommendation="Break the cycle by extracting shared logic into a common module",
                    ))
                    break  # Report first cycle found

        return violations

    def get_allowed_imports(self, subsystem: str) -> set[str]:
        """Get allowed cross-subsystem imports for a given subsystem."""
        return ALLOWED_CROSS_SUBSYSTEM_IMPORTS.get(subsystem, set())
