"""
P3 — Architectural Drift Detection.

Monitors structural metrics to detect architecture degradation.
NO AI analysis — only structural signals.

Drift signals:
- Cyclic subsystem dependencies
- God classes (oversized modules)
- Unstable ownership (frequent changes across subsystems)
- High coupling (too many cross-subsystem imports)
- Exploding interfaces (too many public methods)
- Excessive event chaining
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class DriftSeverity(Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DriftSignal:
    """A single architectural drift signal."""
    signal_type: str
    severity: DriftSeverity
    module: str
    metric_name: str
    metric_value: float
    threshold: float
    message: str


@dataclass
class ModuleMetrics:
    """Structural metrics for a single module."""
    file_path: str
    lines: int = 0
    classes: int = 0
    functions: int = 0
    imports: int = 0
    exports: int = 0
    public_methods: int = 0
    fan_in: int = 0   # how many modules import this
    fan_out: int = 0  # how many modules this imports
    complexity: int = 0  # cyclomatic complexity estimate


class ArchitecturalDriftDetector:
    """
    Detects architectural drift through structural metrics.

    Thresholds:
    - max_module_lines: 500 (god class detection)
    - max_fan_out: 15 (high coupling)
    - max_fan_in: 20 (unstable ownership)
    - max_public_methods: 25 (exploding interface)
    - max_imports: 30 (dependency overload)
    - max_complexity: 50 (complex module)
    """

    DEFAULT_MAX_MODULE_LINES = 500
    DEFAULT_MAX_FAN_OUT = 15
    DEFAULT_MAX_FAN_IN = 20
    DEFAULT_MAX_PUBLIC_METHODS = 25
    DEFAULT_MAX_IMPORTS = 30
    DEFAULT_MAX_COMPLEXITY = 50

    def __init__(
        self,
        max_module_lines: int = DEFAULT_MAX_MODULE_LINES,
        max_fan_out: int = DEFAULT_MAX_FAN_OUT,
        max_fan_in: int = DEFAULT_MAX_FAN_IN,
        max_public_methods: int = DEFAULT_MAX_PUBLIC_METHODS,
        max_imports: int = DEFAULT_MAX_IMPORTS,
        max_complexity: int = DEFAULT_MAX_COMPLEXITY,
    ):
        self.max_module_lines = max_module_lines
        self.max_fan_out = max_fan_out
        self.max_fan_in = max_fan_in
        self.max_public_methods = max_public_methods
        self.max_imports = max_imports
        self.max_complexity = max_complexity

        self._module_metrics: Dict[str, ModuleMetrics] = {}
        self._import_graph: Dict[str, Set[str]] = defaultdict(set)

    def analyze_directory(self, directory: Path, pattern: str = "*.py") -> List[DriftSignal]:
        """
        Analyze all Python files in a directory for architectural drift.
        """
        self._module_metrics.clear()
        self._import_graph.clear()

        # Phase 1: collect metrics
        for f in sorted(directory.rglob(pattern)):
            if "__pycache__" in str(f) or "venv" in str(f):
                continue
            rel = str(f.relative_to(directory))
            metrics = self._analyze_file(f, rel)
            self._module_metrics[rel] = metrics

        # Phase 2: build import graph
        self._build_import_graph(directory)

        # Phase 3: detect drift
        signals: List[DriftSignal] = []

        for rel, metrics in self._module_metrics.items():
            # God class detection
            if metrics.lines > self.max_module_lines:
                signals.append(DriftSignal(
                    signal_type="god_class",
                    severity=DriftSeverity.CRITICAL if metrics.lines > self.max_module_lines * 2 else DriftSeverity.WARNING,
                    module=rel,
                    metric_name="lines",
                    metric_value=metrics.lines,
                    threshold=self.max_module_lines,
                    message=f"Module {rel} has {metrics.lines} lines (threshold: {self.max_module_lines})"
                ))

            # High fan-out (coupling)
            if metrics.fan_out > self.max_fan_out:
                signals.append(DriftSignal(
                    signal_type="high_coupling",
                    severity=DriftSeverity.WARNING,
                    module=rel,
                    metric_name="fan_out",
                    metric_value=metrics.fan_out,
                    threshold=self.max_fan_out,
                    message=f"Module {rel} imports {metrics.fan_out} modules (threshold: {self.max_fan_out})"
                ))

            # High fan-in (unstable ownership)
            if metrics.fan_in > self.max_fan_in:
                signals.append(DriftSignal(
                    signal_type="unstable_ownership",
                    severity=DriftSeverity.WARNING,
                    module=rel,
                    metric_name="fan_in",
                    metric_value=metrics.fan_in,
                    threshold=self.max_fan_in,
                    message=f"Module {rel} is imported by {metrics.fan_in} modules (threshold: {self.max_fan_in})"
                ))

            # Exploding interface
            if metrics.public_methods > self.max_public_methods:
                signals.append(DriftSignal(
                    signal_type="exploding_interface",
                    severity=DriftSeverity.WARNING,
                    module=rel,
                    metric_name="public_methods",
                    metric_value=metrics.public_methods,
                    threshold=self.max_public_methods,
                    message=f"Module {rel} has {metrics.public_methods} public methods (threshold: {self.max_public_methods})"
                ))

            # Dependency overload
            if metrics.imports > self.max_imports:
                signals.append(DriftSignal(
                    signal_type="dependency_overload",
                    severity=DriftSeverity.WARNING,
                    module=rel,
                    metric_name="imports",
                    metric_value=metrics.imports,
                    threshold=self.max_imports,
                    message=f"Module {rel} has {metrics.imports} imports (threshold: {self.max_imports})"
                ))

        # Phase 4: detect cyclic dependencies
        cycles = self._detect_cycles()
        for cycle in cycles:
            signals.append(DriftSignal(
                signal_type="cyclic_dependency",
                severity=DriftSeverity.CRITICAL,
                module=cycle[0],
                metric_name="cycle_length",
                metric_value=len(cycle),
                threshold=0,
                message=f"Cyclic dependency: {' -> '.join(cycle)}"
            ))

        return signals

    def _analyze_file(self, file_path: Path, rel_path: str) -> ModuleMetrics:
        """Analyze a single Python file for structural metrics."""
        metrics = ModuleMetrics(file_path=rel_path)
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            metrics.lines = content.count('\n') + 1

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    metrics.classes += 1
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not item.name.startswith('_'):
                                metrics.public_methods += 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Top-level function
                    if not node.name.startswith('_'):
                        metrics.public_methods += 1
                    metrics.functions += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics.imports += 1

        except (SyntaxError, UnicodeDecodeError):
            pass

        return metrics

    def _build_import_graph(self, directory: Path) -> None:
        """Build import graph for cycle detection."""
        for rel, metrics in self._module_metrics.items():
            file_path = directory / rel
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith('core.'):
                            # Resolve to file path
                            parts = node.module.split('.')
                            if len(parts) >= 2:
                                target = '/'.join(parts[1:]) + '.py'
                                self._import_graph[rel].add(target)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith('core.'):
                                parts = alias.name.split('.')
                                if len(parts) >= 2:
                                    target = '/'.join(parts[1:]) + '.py'
                                    self._import_graph[rel].add(target)
            except (SyntaxError, UnicodeDecodeError):
                pass

        # Calculate fan-in/fan-out
        for source, targets in self._import_graph.items():
            if source in self._module_metrics:
                self._module_metrics[source].fan_out = len(targets)
            for target in targets:
                if target in self._module_metrics:
                    self._module_metrics[target].fan_in += 1

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cyclic dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self._import_graph.get(node, set()):
                if dep not in visited:
                    result = dfs(dep)
                    if result:
                        return result
                elif dep in rec_stack:
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]

            path.pop()
            rec_stack.discard(node)
            return None

        for node in self._import_graph:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    cycles.append(cycle)

        return cycles

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all module metrics."""
        total_modules = len(self._module_metrics)
        total_lines = sum(m.lines for m in self._module_metrics.values())
        total_classes = sum(m.classes for m in self._module_metrics.values())
        total_functions = sum(m.functions for m in self._module_metrics.values())

        return {
            'total_modules': total_modules,
            'total_lines': total_lines,
            'total_classes': total_classes,
            'total_functions': total_functions,
            'avg_lines_per_module': round(total_lines / total_modules, 1) if total_modules > 0 else 0,
            'max_lines': max((m.lines for m in self._module_metrics.values()), default=0),
            'max_fan_out': max((m.fan_out for m in self._module_metrics.values()), default=0),
            'max_fan_in': max((m.fan_in for m in self._module_metrics.values()), default=0),
        }
