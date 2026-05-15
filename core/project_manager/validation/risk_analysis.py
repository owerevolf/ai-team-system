"""
Risk Analysis Engine — deterministic risk scoring for changes.

Risk factors:
- Number of affected files
- Public API changes
- Dependency depth
- Hot files touched
- Critical modules touched
- Architecture violations
- Circular dependency creation
- Unstable module modification

Result: LOW / MEDIUM / HIGH / CRITICAL
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from core.project_manager.models import FileEntry
from loguru import logger


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskFactor:
    """A single risk factor."""
    name: str
    score: float        # 0-100
    weight: float       # multiplier
    description: str

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class RiskAssessment:
    """Complete risk assessment for a set of changes."""
    risk_level: RiskLevel
    total_score: float
    factors: List[RiskFactor] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    requires_approval: bool = False
    blocked: bool = False
    block_reason: str = ""

    def summary(self) -> Dict[str, Any]:
        return {
            'risk_level': self.risk_level.value,
            'total_score': round(self.total_score, 1),
            'factors': [
                {'name': f.name, 'score': f.score, 'weight': f.weight,
                 'weighted': round(f.weighted_score, 1), 'description': f.description}
                for f in self.factors
            ],
            'recommendations': self.recommendations,
            'requires_approval': self.requires_approval,
            'blocked': self.blocked,
            'block_reason': self.block_reason,
        }


class RiskAnalysisEngine:
    """
    Analyzes risk of proposed changes.

    Deterministic scoring based on structural factors.
    No AI opinions.
    """

    # Score thresholds
    LOW_THRESHOLD = 20
    MEDIUM_THRESHOLD = 50
    HIGH_THRESHOLD = 75

    def __init__(
        self,
        files: Dict[str, FileEntry],
        dependencies: Dict[str, List[str]],
        hot_files: Optional[Dict[str, int]] = None,
        protected_files: Optional[Set[str]] = None,
    ):
        self.files = files
        self.dependencies = dependencies
        self.hot_files = hot_files or {}
        self.protected_files = protected_files or set()

        # Build reverse dependencies
        self._reverse_deps: Dict[str, List[str]] = {}
        for source, targets in dependencies.items():
            for target in targets:
                if target not in self._reverse_deps:
                    self._reverse_deps[target] = []
                self._reverse_deps[target].append(source)

    def assess_changes(
        self,
        changed_files: List[str],
        architecture_violations: Optional[List[Any]] = None,
        public_api_changes: int = 0,
        new_circular_deps: bool = False,
    ) -> RiskAssessment:
        """
        Assess risk of a set of file changes.

        Args:
            changed_files: Files being changed
            architecture_violations: Any architecture rule violations
            public_api_changes: Number of public API symbols changed
            new_circular_deps: Whether changes introduce circular deps

        Returns:
            RiskAssessment with level and recommendations
        """
        factors: List[RiskFactor] = []
        recommendations: List[str] = []

        # Factor 1: Number of affected files
        affected = self._get_all_affected(changed_files)
        affected_score = min(len(affected) * 2, 40)
        factors.append(RiskFactor(
            name="affected_files",
            score=affected_score,
            weight=1.0,
            description=f"{len(affected)} files affected by changes",
        ))

        if len(affected) > 10:
            recommendations.append("Consider breaking this into smaller changes")

        # Factor 2: Public API changes
        api_score = min(public_api_changes * 10, 30)
        factors.append(RiskFactor(
            name="public_api_changes",
            score=api_score,
            weight=1.2,
            description=f"{public_api_changes} public API symbols changed",
        ))

        if public_api_changes > 0:
            recommendations.append("Public API changed — ensure backward compatibility")

        # Factor 3: Dependency depth
        max_depth = self._get_max_dependency_depth(changed_files)
        depth_score = min(max_depth * 5, 25)
        factors.append(RiskFactor(
            name="dependency_depth",
            score=depth_score,
            weight=0.8,
            description=f"Max dependency depth: {max_depth}",
        ))

        # Factor 4: Hot files touched
        hot_touched = [f for f in changed_files if f in self.hot_files]
        hot_score = min(len(hot_touched) * 8, 20)
        factors.append(RiskFactor(
            name="hot_files",
            score=hot_score,
            weight=1.0,
            description=f"{len(hot_touched)} frequently accessed files changed",
        ))

        if hot_touched:
            recommendations.append(f"Hot files modified: {', '.join(hot_touched[:3])}")

        # Factor 5: Critical modules touched
        critical = [f for f in changed_files if self._is_critical_module(f)]
        critical_score = min(len(critical) * 15, 30)
        factors.append(RiskFactor(
            name="critical_modules",
            score=critical_score,
            weight=1.5,
            description=f"{len(critical)} critical modules changed",
        ))

        if critical:
            recommendations.append("Critical modules modified — extra review recommended")

        # Factor 6: Architecture violations
        if architecture_violations:
            viol_score = min(len(architecture_violations) * 15, 30)
            factors.append(RiskFactor(
                name="architecture_violations",
                score=viol_score,
                weight=1.5,
                description=f"{len(architecture_violations)} architecture violations",
            ))
            recommendations.append("Architecture violations detected — review required")

        # Factor 7: Circular dependency creation
        if new_circular_deps:
            factors.append(RiskFactor(
                name="circular_dependencies",
                score=25,
                weight=2.0,
                description="Changes introduce circular dependencies",
            ))
            recommendations.append("Circular dependencies introduced — must be resolved")

        # Factor 8: Entry points modified
        entry_points = [f for f in changed_files
                       if f in self.files and self.files[f].is_entry_point]
        if entry_points:
            factors.append(RiskFactor(
                name="entry_points",
                score=20,
                weight=1.3,
                description=f"{len(entry_points)} entry points modified",
            ))
            recommendations.append("Entry points modified — thorough testing required")

        # Calculate total score
        total = sum(f.weighted_score for f in factors)
        total = min(total, 100)  # Cap at 100

        # Determine risk level
        if total >= self.HIGH_THRESHOLD:
            risk_level = RiskLevel.HIGH
        elif total >= self.MEDIUM_THRESHOLD:
            risk_level = RiskLevel.MEDIUM
        elif total >= self.LOW_THRESHOLD:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.LOW

        # Check for critical conditions
        blocked = False
        block_reason = ""

        if new_circular_deps:
            blocked = True
            block_reason = "Circular dependencies cannot be introduced"
            risk_level = RiskLevel.CRITICAL

        if len(critical) > 2:
            blocked = True
            block_reason = "Too many critical modules modified at once"
            risk_level = RiskLevel.CRITICAL

        # Determine if approval is required
        requires_approval = (
            risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
            or len(architecture_violations or []) > 0
            or public_api_changes > 2
            or len(critical) > 0
        )

        if not recommendations:
            recommendations.append("Low risk change — standard testing recommended")

        return RiskAssessment(
            risk_level=risk_level,
            total_score=total,
            factors=factors,
            recommendations=recommendations,
            requires_approval=requires_approval,
            blocked=blocked,
            block_reason=block_reason,
        )

    def _get_all_affected(self, changed_files: List[str]) -> Set[str]:
        """Get all transitively affected files."""
        affected: Set[str] = set()
        queue = list(changed_files)

        while queue:
            current = queue.pop(0)
            if current in affected:
                continue
            affected.add(current)

            for dep in self._reverse_deps.get(current, []):
                if dep not in affected:
                    queue.append(dep)

        return affected

    def _get_max_dependency_depth(self, changed_files: List[str]) -> int:
        """Get maximum dependency depth from changed files."""
        max_depth = 0

        for changed in changed_files:
            visited: Set[str] = set()
            queue = [(changed, 0)]

            while queue:
                current, depth = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                max_depth = max(max_depth, depth)

                for dep in self._reverse_deps.get(current, []):
                    if dep not in visited:
                        queue.append((dep, depth + 1))

        return max_depth

    def _is_critical_module(self, file_path: str) -> bool:
        """Check if a file is in a critical module."""
        critical_patterns = [
            'core/project_manager',
            'core/agent_manager',
            'core/model_router',
            'web_ui/app.py',
            'core/storage',
            'core/events',
        ]
        for pattern in critical_patterns:
            if file_path.startswith(pattern) or file_path == pattern:
                return True
        return False
