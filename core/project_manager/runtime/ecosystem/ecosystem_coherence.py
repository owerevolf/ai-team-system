"""
Phase 15, P8: Ecosystem Coherence Metrics

Monitors ecosystem-level coherence:
- plugin semantic conflicts
- incompatible runtime assumptions
- ecosystem fragmentation
- extension governance violations

Without central authoritarian control.

Principle: Monitor ecosystem health, don't control it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EcosystemDimension(Enum):
    PLUGIN_SEMANTICS = "plugin_semantics"
    RUNTIME_ASSUMPTIONS = "runtime_assumptions"
    GOVERNANCE_COMPATIBILITY = "governance_compatibility"
    BOUNDARY_INTEGRITY = "boundary_integrity"


class EcosystemHealth(Enum):
    HEALTHY = "healthy"
    MINOR_ISSUES = "minor_issues"
    FRAGMENTATION_RISK = "fragmentation_risk"
    FRAGMENTED = "fragmented"


@dataclass
class EcosystemIssue:
    """An ecosystem-level coherence issue."""
    dimension: EcosystemDimension
    description: str
    affected_plugins: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class EcosystemCoherenceReport:
    """Full ecosystem coherence report."""
    issues: list[EcosystemIssue] = field(default_factory=list)
    total_plugins: int = 0
    compatible_plugins: int = 0

    @property
    def overall_health(self) -> EcosystemHealth:
        if not self.issues:
            return EcosystemHealth.HEALTHY
        critical = sum(1 for i in self.issues if "conflict" in i.description.lower())
        if critical > 3:
            return EcosystemHealth.FRAGMENTED
        elif critical > 0:
            return EcosystemHealth.FRAGMENTATION_RISK
        return EcosystemHealth.MINOR_ISSUES


class EcosystemCoherenceMetrics:
    """
    Monitors ecosystem-level coherence.
    Detects plugin conflicts, fragmentation, and governance violations.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, dict] = {}

    def register_plugin(self, name: str, metadata: dict) -> None:
        """Register a plugin with its metadata."""
        self._plugins[name] = metadata

    def check_semantic_conflicts(self) -> list[EcosystemIssue]:
        """Check for semantic conflicts between plugins."""
        issues: list[EcosystemIssue] = []

        # Check for plugins defining conflicting concepts
        concept_owners: dict[str, list[str]] = {}
        for name, meta in self._plugins.items():
            for concept in meta.get("defines_concepts", []):
                concept_owners.setdefault(concept, []).append(name)

        for concept, owners in concept_owners.items():
            if len(owners) > 1:
                issues.append(EcosystemIssue(
                    dimension=EcosystemDimension.PLUGIN_SEMANTICS,
                    description=f"Concept '{concept}' defined by multiple plugins: {', '.join(owners)}",
                    affected_plugins=owners,
                    recommendation=f"Use canonical definition of '{concept}' or namespace the plugin's version",
                ))

        return issues

    def check_governance_violations(self) -> list[EcosystemIssue]:
        """Check for governance violations by plugins."""
        issues: list[EcosystemIssue] = []

        for name, meta in self._plugins.items():
            caps = meta.get("capabilities", [])
            if "bypass_approvals" in caps:
                issues.append(EcosystemIssue(
                    dimension=EcosystemDimension.GOVERNANCE_COMPATIBILITY,
                    description=f"Plugin '{name}' requests forbidden capability: bypass_approvals",
                    affected_plugins=[name],
                    recommendation="Remove bypass_approvals — use approval workflow instead",
                ))
            if "modify_pm_core" in caps:
                issues.append(EcosystemIssue(
                    dimension=EcosystemDimension.BOUNDARY_INTEGRITY,
                    description=f"Plugin '{name}' requests forbidden capability: modify_pm_core",
                    affected_plugins=[name],
                    recommendation="Remove modify_pm_core — plugins cannot modify core runtime",
                ))

        return issues

    def generate_report(self) -> EcosystemCoherenceReport:
        """Generate full ecosystem coherence report."""
        issues: list[EcosystemIssue] = []
        issues.extend(self.check_semantic_conflicts())
        issues.extend(self.check_governance_violations())

        return EcosystemCoherenceReport(
            issues=issues,
            total_plugins=len(self._plugins),
            compatible_plugins=len(self._plugins) - len(set(
                p for i in issues for p in i.affected_plugins
            )),
        )
