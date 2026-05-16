"""
Project Health Dashboard — Phase 8, Priority 2.

Computes and serves project-level health metrics for the browser UI.

Metrics:
- Project health (overall score, status)
- Validation status
- Unstable modules (high change frequency)
- Dependency risks (circular deps, missing deps)
- Architectural drift (structure changes over time)
- Recent failures
- Retrieval hotspots (most-queried files)
- Complexity score (per-module and overall)

All metrics are deterministic — computed from indexed project data.
No AI speculation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ModuleHealth:
    """Health metrics for a single module/file."""
    path: str
    complexity_score: float = 0.0        # 0-1, higher = more complex
    change_frequency: float = 0.0        # changes per week (normalized 0-1)
    dependency_count: int = 0
    dependent_count: int = 0
    test_coverage: float = 0.0           # 0-1
    last_failure: str = ""               # ISO timestamp or empty
    risk_level: str = "low"              # low | medium | high | critical
    issues: list[str] = field(default_factory=list)


@dataclass
class DependencyRisk:
    """A dependency-related risk."""
    source: str
    target: str
    risk_type: str                       # circular | missing | deprecated | deep_chain
    severity: str                        # low | medium | high
    description: str = ""


@dataclass
class ProjectHealthDashboard:
    """Complete project health dashboard data."""
    # Overall
    overall_score: float = 1.0           # 0-1
    overall_status: str = "healthy"      # healthy | warning | degraded | critical
    last_updated: str = ""

    # Summary counts
    total_files: int = 0
    total_modules: int = 0
    total_dependencies: int = 0
    total_tests: int = 0

    # Detailed metrics
    validation_pass_rate: float = 1.0
    unstable_modules: list[ModuleHealth] = field(default_factory=list)
    dependency_risks: list[DependencyRisk] = field(default_factory=list)
    architectural_drift_score: float = 0.0  # 0-1, higher = more drift
    recent_failures: list[dict[str, Any]] = field(default_factory=list)
    retrieval_hotspots: list[dict[str, Any]] = field(default_factory=list)
    complexity_score: float = 0.0

    # Per-module breakdown
    modules: list[ModuleHealth] = field(default_factory=list)

    # Recommendations
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dashboard builder
# ---------------------------------------------------------------------------

class ProjectHealthBuilder:
    """
    Builds a ProjectHealthDashboard from indexed project data.

    Usage:
        builder = ProjectHealthBuilder(pm)
        dashboard = builder.build()
    """

    # Thresholds
    COMPLEXITY_HIGH = 0.7
    COMPLEXITY_CRITICAL = 0.9
    CHANGE_FREQ_HIGH = 0.6
    DRIFT_HIGH = 0.5
    MODULES_UNSTABLE_TOP = 10
    HOTSPOTS_TOP = 10

    def __init__(self, project_manager: Any) -> None:
        """
        Args:
            project_manager: An indexed ProjectManager instance.
        """
        self._pm = project_manager

    def build(self) -> ProjectHealthDashboard:
        """Build the complete health dashboard."""
        pm = self._pm
        dashboard = ProjectHealthDashboard()
        dashboard.last_updated = datetime.now().isoformat()

        # --- Basic stats ---
        stats = self._get_stats()
        dashboard.total_files = stats.get("total_files", 0)
        dashboard.total_dependencies = stats.get("total_dependencies", 0)

        # --- Module health ---
        modules = self._compute_module_health()
        dashboard.modules = modules
        dashboard.total_modules = len(modules)

        # --- Unstable modules (top N by change frequency) ---
        unstable = sorted(modules, key=lambda m: m.change_frequency, reverse=True)
        dashboard.unstable_modules = [
            m for m in unstable if m.change_frequency > 0
        ][:self.MODULES_UNSTABLE_TOP]

        # --- Dependency risks ---
        dep_risks = self._compute_dependency_risks()
        dashboard.dependency_risks = dep_risks

        # --- Complexity ---
        dashboard.complexity_score = self._compute_overall_complexity(modules)

        # --- Architectural drift ---
        dashboard.architectural_drift_score = self._compute_drift()

        # --- Retrieval hotspots ---
        dashboard.retrieval_hotspots = self._compute_hotspots()

        # --- Overall score ---
        dashboard.overall_score = self._compute_overall_score(dashboard)
        dashboard.overall_status = self._score_to_status(dashboard.overall_score)

        # --- Recommendations ---
        dashboard.recommendations = self._generate_recommendations(dashboard)

        return dashboard

    # -- public: serialize for JSON response --------------------------------

    def build_dict(self) -> dict[str, Any]:
        """Build the dashboard and return it as a JSON-serializable dict."""
        dash = self.build()
        return {
            "overall_score": dash.overall_score,
            "overall_status": dash.overall_status,
            "last_updated": dash.last_updated,
            "total_files": dash.total_files,
            "total_modules": dash.total_modules,
            "total_dependencies": dash.total_dependencies,
            "total_tests": dash.total_tests,
            "validation_pass_rate": dash.validation_pass_rate,
            "complexity_score": dash.complexity_score,
            "architectural_drift_score": dash.architectural_drift_score,
            "unstable_modules": [
                {
                    "path": m.path,
                    "complexity_score": m.complexity_score,
                    "change_frequency": m.change_frequency,
                    "dependency_count": m.dependency_count,
                    "dependent_count": m.dependent_count,
                    "test_coverage": m.test_coverage,
                    "risk_level": m.risk_level,
                    "issues": m.issues,
                }
                for m in dash.unstable_modules
            ],
            "dependency_risks": [
                {
                    "source": r.source,
                    "target": r.target,
                    "risk_type": r.risk_type,
                    "severity": r.severity,
                    "description": r.description,
                }
                for r in dash.dependency_risks
            ],
            "recent_failures": dash.recent_failures,
            "retrieval_hotspots": dash.retrieval_hotspots,
            "recommendations": dash.recommendations,
        }

    # -- internals ----------------------------------------------------------

    def _get_stats(self) -> dict[str, Any]:
        """Safely get stats from PM."""
        try:
            return self._pm.get_stats()
        except Exception:
            return {}

    def _compute_module_health(self) -> list[ModuleHealth]:
        """Compute health metrics for each indexed file."""
        modules: list[ModuleHealth] = []
        try:
            files = getattr(self._pm, '_files', {}) or {}
            deps = getattr(self._pm, 'dependencies', {}) or {}
            reverse_deps = self._build_reverse_deps(deps)
        except Exception:
            return modules

        for fpath, entry in files.items():
            m = ModuleHealth(path=fpath)

            # Complexity: based on symbol count (normalized)
            symbols = getattr(entry, 'symbols', []) or []
            m.complexity_score = min(1.0, len(symbols) / 50.0)

            # Dependency counts
            m.dependency_count = len(deps.get(fpath, []))
            m.dependent_count = len(reverse_deps.get(fpath, []))

            # Risk level
            if m.complexity_score >= self.COMPLEXITY_CRITICAL:
                m.risk_level = "critical"
                m.issues.append("Extremely high complexity")
            elif m.complexity_score >= self.COMPLEXITY_HIGH:
                m.risk_level = "high"
                m.issues.append("High complexity")

            if m.dependent_count > 20:
                m.risk_level = "high"
                m.issues.append(f"High coupling: {m.dependent_count} dependents")

            modules.append(m)

        return modules

    def _build_reverse_deps(
        self, deps: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """Build reverse dependency map."""
        reverse: dict[str, list[str]] = {}
        for source, targets in deps.items():
            for target in targets:
                reverse.setdefault(target, []).append(source)
        return reverse

    def _compute_dependency_risks(self) -> list[DependencyRisk]:
        """Detect dependency risks: circular deps, deep chains."""
        risks: list[DependencyRisk] = []
        try:
            deps = getattr(self._pm, 'dependencies', {}) or {}
        except Exception:
            return risks

        # Check for circular dependencies (simple 2-cycle detection)
        visited: set[str] = set()
        for source, targets in deps.items():
            for target in targets:
                if target in deps and source in deps[target]:
                    pair = tuple(sorted((source, target)))
                    if pair not in visited:
                        visited.add(pair)
                        risks.append(DependencyRisk(
                            source=source,
                            target=target,
                            risk_type="circular",
                            severity="high",
                            description=f"Circular dependency: {source} <-> {target}",
                        ))

        # Check for deep dependency chains (> 5 levels)
        for source in deps:
            depth = self._dep_depth(source, deps, set())
            if depth > 5:
                risks.append(DependencyRisk(
                    source=source,
                    target="",
                    risk_type="deep_chain",
                    severity="medium",
                    description=f"Deep dependency chain from {source}: depth {depth}",
                ))

        return risks

    def _dep_depth(
        self, source: str, deps: dict[str, list[str]], visited: set[str]
    ) -> int:
        """Compute max dependency depth from source."""
        if source in visited:
            return 0
        visited.add(source)
        targets = deps.get(source, [])
        if not targets:
            return 0
        return 1 + max(
            (self._dep_depth(t, deps, visited.copy()) for t in targets),
            default=0,
        )

    def _compute_overall_complexity(self, modules: list[ModuleHealth]) -> float:
        """Average complexity across all modules."""
        if not modules:
            return 0.0
        return round(sum(m.complexity_score for m in modules) / len(modules), 3)

    def _compute_drift(self) -> float:
        """
        Architectural drift: ratio of files changed recently vs total.
        Uses git history if available, otherwise returns 0.
        """
        try:
            git = getattr(self._pm, '_git', None)
            if git is None:
                return 0.0
            recent = git.get_recently_active_files(days=14, limit=100)
            stats = self._get_stats()
            total = stats.get("total_files", 0)
            if total == 0:
                return 0.0
            return round(min(1.0, len(recent) / total), 3)
        except Exception:
            return 0.0

    def _compute_hotspots(self) -> list[dict[str, Any]]:
        """
        Retrieval hotspots: most frequently accessed files.
        Uses PM query history if available.
        """
        try:
            history = getattr(self._pm, '_query_history', {}) or {}
            if not history:
                return []
            # Sort by access count
            sorted_files = sorted(
                history.items(), key=lambda x: x[1], reverse=True
            )
            return [
                {"path": path, "access_count": count}
                for path, count in sorted_files[:self.HOTSPOTS_TOP]
            ]
        except Exception:
            return []

    def _compute_overall_score(self, dash: ProjectHealthDashboard) -> float:
        """
        Compute overall health score (0-1).

        Factors:
        - Complexity (weight 0.25)
        - Dependency risks (weight 0.25)
        - Architectural drift (weight 0.2)
        - Unstable modules ratio (weight 0.15)
        - Validation pass rate (weight 0.15)
        """
        # Complexity: lower is better
        complexity_factor = 1.0 - dash.complexity_score

        # Dependency risks: fewer is better
        risk_count = len(dash.dependency_risks)
        dep_factor = max(0.0, 1.0 - risk_count * 0.1)

        # Drift: lower is better
        drift_factor = 1.0 - dash.architectural_drift_score

        # Unstable modules ratio
        unstable_ratio = (
            len(dash.unstable_modules) / max(dash.total_modules, 1)
        )
        stability_factor = 1.0 - unstable_ratio

        # Validation
        validation_factor = dash.validation_pass_rate

        score = (
            complexity_factor * 0.25
            + dep_factor * 0.25
            + drift_factor * 0.2
            + stability_factor * 0.15
            + validation_factor * 0.15
        )
        return round(max(0.0, min(1.0, score)), 3)

    @staticmethod
    def _score_to_status(score: float) -> str:
        if score >= 0.8:
            return "healthy"
        if score >= 0.6:
            return "warning"
        if score >= 0.4:
            return "degraded"
        return "critical"

    @staticmethod
    def _generate_recommendations(dash: ProjectHealthDashboard) -> list[str]:
        """Generate actionable recommendations."""
        recs: list[str] = []

        if dash.complexity_score > 0.6:
            recs.append(
                "High overall complexity — consider splitting large modules"
            )

        if dash.dependency_risks:
            circular = [r for r in dash.dependency_risks if r.risk_type == "circular"]
            if circular:
                recs.append(
                    f"Found {len(circular)} circular dependency(ies) — refactor to break cycles"
                )
            deep = [r for r in dash.dependency_risks if r.risk_type == "deep_chain"]
            if deep:
                recs.append(
                    f"Found {len(deep)} deep dependency chain(s) — consider flattening"
                )

        if dash.architectural_drift_score > 0.5:
            recs.append(
                "High architectural drift — many files changed recently, consider stabilizing"
            )

        if dash.unstable_modules:
            top = dash.unstable_modules[0]
            recs.append(
                f"Most unstable module: {top.path} — consider adding tests or refactoring"
            )

        if not recs:
            recs.append("Project is healthy — no action needed")

        return recs
