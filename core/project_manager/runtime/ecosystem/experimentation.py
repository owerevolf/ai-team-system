"""
Phase 15, P3: Safe Experimentation Framework

Allows experimentation without destroying core runtime.
Sandbox zones, feature flags, isolated plugin domains.

Principle: Experimentation > stagnation, but isolation > chaos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ExperimentZone(Enum):
    SANDBOX = "sandbox"            # Fully isolated, no core access
    EXPERIMENTAL_API = "experimental_api"  # New APIs, clearly marked
    ISOLATED_PLUGIN = "isolated_plugin"    # Plugin with restricted capabilities
    FEATURE_FLAG = "feature_flag"          # Behind flag, can be toggled off
    NON_CORE_EXTENSION = "non_core"        # Extension boundary, no core changes


class ExperimentRisk(Enum):
    LOW = "low"                    # No core impact, safe to experiment
    MEDIUM = "medium"              # Potential core impact, needs monitoring
    HIGH = "high"                  # Core impact possible, needs isolation


@dataclass
class ExperimentDefinition:
    """A defined experiment with safety boundaries."""
    name: str
    zone: ExperimentZone
    risk: ExperimentRisk
    description: str
    allowed_capabilities: list[str]
    forbidden_capabilities: list[str]
    rollback_procedure: str
    success_criteria: list[str] = field(default_factory=list)
    max_duration_days: int = 30


@dataclass
class FeatureFlag:
    """A feature flag for experimental features."""
    name: str
    description: str
    default_enabled: bool = False
    zone: ExperimentZone = ExperimentZone.FEATURE_FLAG
    dependencies: list[str] = field(default_factory=list)
    rollback_impact: str = "none"


class SafeExperimentationFramework:
    """
    Manages safe experimentation zones.
    Allows innovation without risking core runtime stability.
    """

    def __init__(self) -> None:
        self._experiments: dict[str, ExperimentDefinition] = {}
        self._feature_flags: dict[str, FeatureFlag] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default experiment zones and feature flags."""

        # Default experiment zones
        self.register_experiment(ExperimentDefinition(
            name="sandbox_runtime",
            zone=ExperimentZone.SANDBOX,
            risk=ExperimentRisk.LOW,
            description="Fully isolated runtime layer for testing new execution models",
            allowed_capabilities=["read_files", "execute_commands", "modify_context"],
            forbidden_capabilities=["modify_governance", "bypass_approvals", "access_network"],
            rollback_procedure="Delete sandbox layer, no core impact",
            success_criteria=["No core runtime modifications", "All tests pass"],
        ))

        self.register_experiment(ExperimentDefinition(
            name="experimental_apis",
            zone=ExperimentZone.EXPERIMENTAL_API,
            risk=ExperimentRisk.MEDIUM,
            description="New APIs marked as experimental, subject to change",
            allowed_capabilities=["new_endpoints", "new_parameters", "new_responses"],
            forbidden_capabilities=["breaking_existing_contracts", "modifying_core_types"],
            rollback_procedure="Deprecate experimental API, migrate users to stable version",
            success_criteria=["API is used by at least one client", "No breaking changes to stable APIs"],
        ))

        self.register_experiment(ExperimentDefinition(
            name="isolated_plugins",
            zone=ExperimentZone.ISOLATED_PLUGIN,
            risk=ExperimentRisk.MEDIUM,
            description="Plugins running in isolated domain with restricted capabilities",
            allowed_capabilities=["read_files", "write_files", "trigger_workflows"],
            forbidden_capabilities=["modify_governance", "bypass_approvals", "access_network", "modify_pm_core"],
            rollback_procedure="Disable plugin, verify no core state corruption",
            success_criteria=["Plugin works within boundaries", "No core contract violations"],
        ))

        # Default feature flags
        self.register_feature_flag(FeatureFlag(
            name="experimental_compression",
            description="Enable experimental compression algorithms",
            default_enabled=False,
            zone=ExperimentZone.FEATURE_FLAG,
            dependencies=["compression/compression_engine"],
            rollback_impact="Falls back to standard compression",
        ))

        self.register_feature_flag(FeatureFlag(
            name="new_trust_model",
            description="Enable new trust drift detection model",
            default_enabled=False,
            zone=ExperimentZone.FEATURE_FLAG,
            dependencies=["trust/trust_drift_detection"],
            rollback_impact="Falls back to previous trust model",
        ))

    def register_experiment(self, experiment: ExperimentDefinition) -> None:
        """Register an experiment definition."""
        self._experiments[experiment.name] = experiment

    def register_feature_flag(self, flag: FeatureFlag) -> None:
        """Register a feature flag."""
        self._feature_flags[flag.name] = flag

    def get_experiment(self, name: str) -> Optional[ExperimentDefinition]:
        """Get an experiment definition."""
        return self._experiments.get(name)

    def get_feature_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get a feature flag."""
        return self._feature_flags.get(name)

    def list_experiments(self, zone: Optional[ExperimentZone] = None) -> list[ExperimentDefinition]:
        """List experiments, optionally filtered by zone."""
        if zone:
            return [e for e in self._experiments.values() if e.zone == zone]
        return list(self._experiments.values())

    def list_feature_flags(self, enabled_only: bool = False) -> list[FeatureFlag]:
        """List feature flags."""
        if enabled_only:
            return [f for f in self._feature_flags.values() if f.default_enabled]
        return list(self._feature_flags.values())

    def validate_experiment(self, name: str) -> tuple[bool, list[str]]:
        """Validate that an experiment is properly isolated."""
        experiment = self._experiments.get(name)
        if not experiment:
            return False, [f"Unknown experiment: {name}"]

        issues: list[str] = []

        # Check that forbidden capabilities are actually forbidden
        for cap in experiment.forbidden_capabilities:
            if cap in experiment.allowed_capabilities:
                issues.append(f"Capability '{cap}' is both allowed and forbidden")

        # Check that rollback procedure exists
        if not experiment.rollback_procedure:
            issues.append("No rollback procedure defined")

        # Check max duration
        if experiment.max_duration_days <= 0:
            issues.append("Invalid max duration")

        return len(issues) == 0, issues

    @property
    def total_experiments(self) -> int:
        return len(self._experiments)

    @property
    def total_feature_flags(self) -> int:
        return len(self._feature_flags)
