"""
Phase 15: Tests for Ecosystem Sustainability & Contributor Scalability
"""

import pytest

from core.project_manager.runtime.ecosystem.onboarding import (
    ContributorOnboardingCompressor, OnboardingLevel,
)
from core.project_manager.runtime.ecosystem.learning_paths import (
    ArchitecturalLearningPaths, LearningPathType,
)
from core.project_manager.runtime.ecosystem.experimentation import (
    SafeExperimentationFramework, ExperimentZone, ExperimentRisk,
)
from core.project_manager.runtime.ecosystem.fork_drift import (
    ForkDriftAnalyzer, DriftDimension, DriftLevel,
)
from core.project_manager.runtime.ecosystem.plugin_governance import (
    PluginEcosystemGovernance, CapabilityType, CapabilityRisk,
)
from core.project_manager.runtime.ecosystem.maintainer_load import (
    MaintainerLoadProtector, LoadType, LoadLevel,
)
from core.project_manager.runtime.ecosystem.succession import (
    ArchitecturalSuccessionPlanner,
)
from core.project_manager.runtime.ecosystem.ecosystem_coherence import (
    EcosystemCoherenceMetrics, EcosystemDimension, EcosystemHealth,
)
from core.project_manager.runtime.ecosystem.contributor_ergonomics import (
    ContributorErgonomics, FrictionType, FrictionLevel,
)
from core.project_manager.runtime.ecosystem.identity import (
    CoreIdentityPreservation, IdentityAspect, PressureType,
)


# ═══════════════════════════════════════════════════════════════
# P1: Contributor Onboarding
# ═══════════════════════════════════════════════════════════════

class TestOnboarding:
    def test_compressor_creates(self):
        comp = ContributorOnboardingCompressor()
        assert comp.total_modules > 0

    def test_five_levels(self):
        comp = ContributorOnboardingCompressor()
        assert len(comp.levels) == 5

    def test_get_modules_for_level(self):
        comp = ContributorOnboardingCompressor()
        level1 = comp.get_modules_for_level(OnboardingLevel.OVERVIEW)
        assert len(level1) > 0

    def test_create_path_core_maintainer(self):
        comp = ContributorOnboardingCompressor()
        path = comp.create_path("core_maintainer")
        assert len(path) > 0

    def test_create_path_plugin_developer(self):
        comp = ContributorOnboardingCompressor()
        path = comp.create_path("plugin_developer")
        assert len(path) > 0
        # Plugin path should be shorter than core
        core_path = comp.create_path("core_maintainer")
        assert len(path) < len(core_path)

    def test_estimate_time(self):
        comp = ContributorOnboardingCompressor()
        time = comp.estimate_total_time("core_maintainer")
        assert time > 0

    def test_module_has_prerequisites(self):
        comp = ContributorOnboardingCompressor()
        module = comp.get_module("execution_model")
        assert module is not None
        assert len(module.prerequisites) > 0


# ═══════════════════════════════════════════════════════════════
# P2: Learning Paths
# ═══════════════════════════════════════════════════════════════

class TestLearningPaths:
    def test_paths_exist(self):
        paths = ArchitecturalLearningPaths()
        assert paths.total_paths > 0

    def test_recovery_path(self):
        paths = ArchitecturalLearningPaths()
        path = paths.get_path(LearningPathType.RECOVERY)
        assert path is not None
        assert path.total_steps > 0
        assert path.total_minutes > 0

    def test_governance_path(self):
        paths = ArchitecturalLearningPaths()
        path = paths.get_path(LearningPathType.GOVERNANCE)
        assert path is not None

    def test_observability_path(self):
        paths = ArchitecturalLearningPaths()
        path = paths.get_path(LearningPathType.OBSERVABILITY)
        assert path is not None

    def test_execution_path(self):
        paths = ArchitecturalLearningPaths()
        path = paths.get_path(LearningPathType.EXECUTION)
        assert path is not None

    def test_plugin_path(self):
        paths = ArchitecturalLearningPaths()
        path = paths.get_path(LearningPathType.PLUGIN)
        assert path is not None

    def test_total_learning_time(self):
        paths = ArchitecturalLearningPaths()
        total = paths.get_total_learning_time()
        assert total > 0


# ═══════════════════════════════════════════════════════════════
# P3: Safe Experimentation
# ═══════════════════════════════════════════════════════════════

class TestExperimentation:
    def test_framework_creates(self):
        fw = SafeExperimentationFramework()
        assert fw.total_experiments > 0

    def test_sandbox_zone(self):
        fw = SafeExperimentationFramework()
        sandbox = fw.list_experiments(ExperimentZone.SANDBOX)
        assert len(sandbox) > 0

    def test_experiment_validation(self):
        fw = SafeExperimentationFramework()
        valid, issues = fw.validate_experiment("sandbox_runtime")
        assert valid

    def test_feature_flags(self):
        fw = SafeExperimentationFramework()
        flags = fw.list_feature_flags()
        assert len(flags) > 0

    def test_experiment_risk_levels(self):
        assert ExperimentRisk.LOW.value == "low"
        assert ExperimentRisk.HIGH.value == "high"


# ═══════════════════════════════════════════════════════════════
# P4: Fork Drift
# ═══════════════════════════════════════════════════════════════

class TestForkDrift:
    def test_analyzer_creates(self):
        analyzer = ForkDriftAnalyzer()
        assert analyzer is not None

    def test_register_fork(self):
        analyzer = ForkDriftAnalyzer()
        report = analyzer.register_fork("test_fork")
        assert report.fork_name == "test_fork"

    def test_check_concept_compatibility(self):
        analyzer = ForkDriftAnalyzer()
        compatible, msg = analyzer.check_concept_compatibility("CanonicalPriority", "test_fork")
        assert compatible

    def test_check_governance_compatibility(self):
        analyzer = ForkDriftAnalyzer()
        compatible, msg = analyzer.check_governance_compatibility("safety_over_autonomy", "test_fork")
        assert not compatible  # Core governance rule

    def test_drift_dimensions(self):
        assert DriftDimension.SEMANTIC.value == "semantic"
        assert DriftDimension.GOVERNANCE.value == "governance"


# ═══════════════════════════════════════════════════════════════
# P5: Plugin Governance
# ═══════════════════════════════════════════════════════════════

class TestPluginGovernance:
    def test_governance_creates(self):
        gov = PluginEcosystemGovernance()
        assert gov is not None

    def test_register_plugin(self):
        gov = PluginEcosystemGovernance()
        from core.project_manager.runtime.ecosystem.plugin_governance import ExtensionContract
        contract = ExtensionContract(
            plugin_name="test_plugin",
            allowed_capabilities=[CapabilityType.READ_FILES, CapabilityType.WRITE_FILES],
        )
        gov.register_plugin(contract)
        assert gov.total_plugins == 1

    def test_forbidden_capability(self):
        gov = PluginEcosystemGovernance()
        from core.project_manager.runtime.ecosystem.plugin_governance import ExtensionContract
        contract = ExtensionContract(
            plugin_name="bad_plugin",
            allowed_capabilities=[CapabilityType.BYPASS_APPROVALS],
        )
        gov.register_plugin(contract)
        valid, issues = gov.validate_plugin("bad_plugin")
        assert not valid

    def test_capability_risk(self):
        from core.project_manager.runtime.ecosystem.plugin_governance import CAPABILITY_RISK
        assert CAPABILITY_RISK[CapabilityType.READ_FILES] == CapabilityRisk.LOW
        assert CAPABILITY_RISK[CapabilityType.BYPASS_APPROVALS] == CapabilityRisk.FORBIDDEN

    def test_create_safe_contract(self):
        gov = PluginEcosystemGovernance()
        contract = gov.create_safe_contract("safe_plugin", [
            CapabilityType.READ_FILES,
            CapabilityType.BYPASS_APPROVALS,  # Will be filtered out
        ])
        assert CapabilityType.READ_FILES in contract.allowed_capabilities
        assert CapabilityType.BYPASS_APPROVALS in contract.forbidden_capabilities


# ═══════════════════════════════════════════════════════════════
# P6: Maintainer Load
# ═══════════════════════════════════════════════════════════════

class TestMaintainerLoad:
    def test_protector_creates(self):
        prot = MaintainerLoadProtector()
        assert prot is not None

    def test_register_maintainer(self):
        prot = MaintainerLoadProtector()
        m = prot.register_maintainer("alice")
        assert m.name == "alice"

    def test_record_activity(self):
        prot = MaintainerLoadProtector()
        prot.register_maintainer("alice")
        prot.record_activity("alice", LoadType.REVIEW, 5)
        load = prot.get_load("alice")
        assert load.loads[LoadType.REVIEW] == 5

    def test_load_levels(self):
        assert LoadLevel.HEALTHY.value == "healthy"
        assert LoadLevel.BURNOUT_RISK.value == "burnout_risk"

    def test_generate_report(self):
        prot = MaintainerLoadProtector()
        prot.register_maintainer("alice")
        report = prot.generate_report()
        assert len(report.maintainers) == 1

    def test_suggest_distribution(self):
        prot = MaintainerLoadProtector()
        prot.register_maintainer("overloaded")
        prot.register_maintainer("underloaded")
        prot.record_activity("overloaded", LoadType.REVIEW, 30)
        suggestions = prot.suggest_load_distribution("overloaded")
        assert len(suggestions) > 0


# ═══════════════════════════════════════════════════════════════
# P7: Succession Planning
# ═══════════════════════════════════════════════════════════════

class TestSuccession:
    def test_planner_creates(self):
        planner = ArchitecturalSuccessionPlanner()
        assert planner.total_subsystems > 0

    def test_get_subsystem(self):
        planner = ArchitecturalSuccessionPlanner()
        durability = planner.get_subsystem("durability")
        assert durability is not None
        assert len(durability.critical_invariants) > 0

    def test_assess_readiness(self):
        planner = ArchitecturalSuccessionPlanner()
        readiness = planner.assess_succession_readiness("durability")
        assert readiness.subsystem == "durability"
        assert 0 <= readiness.readiness_score <= 1

    def test_identify_knowledge_gaps(self):
        planner = ArchitecturalSuccessionPlanner()
        gaps = planner.identify_knowledge_gaps()
        # Should identify gaps (no maintainers assigned in test data)
        assert len(gaps) > 0


# ═══════════════════════════════════════════════════════════════
# P8: Ecosystem Coherence
# ═══════════════════════════════════════════════════════════════

class TestEcosystemCoherence:
    def test_metrics_creates(self):
        metrics = EcosystemCoherenceMetrics()
        assert metrics is not None

    def test_register_plugin(self):
        metrics = EcosystemCoherenceMetrics()
        metrics.register_plugin("test_plugin", {
            "defines_concepts": ["MyConcept"],
            "capabilities": ["read_files"],
        })

    def test_check_semantic_conflicts(self):
        metrics = EcosystemCoherenceMetrics()
        metrics.register_plugin("plugin_a", {"defines_concepts": ["SharedConcept"]})
        metrics.register_plugin("plugin_b", {"defines_concepts": ["SharedConcept"]})
        conflicts = metrics.check_semantic_conflicts()
        assert len(conflicts) > 0

    def test_check_governance_violations(self):
        metrics = EcosystemCoherenceMetrics()
        metrics.register_plugin("bad_plugin", {
            "capabilities": ["bypass_approvals"],
        })
        violations = metrics.check_governance_violations()
        assert len(violations) > 0

    def test_generate_report(self):
        metrics = EcosystemCoherenceMetrics()
        report = metrics.generate_report()
        assert report.total_plugins == 0


# ═══════════════════════════════════════════════════════════════
# P9: Contributor Ergonomics
# ═══════════════════════════════════════════════════════════════

class TestContributorErgonomics:
    def test_ergonomics_creates(self):
        erg = ContributorErgonomics()
        assert erg is not None

    def test_generate_report(self):
        erg = ContributorErgonomics()
        report = erg.generate_report()
        assert len(report.friction_points) > 0
        assert 0 <= report.overall_score <= 100

    def test_high_friction_areas(self):
        erg = ContributorErgonomics()
        report = erg.generate_report()
        high = report.high_friction_areas
        assert isinstance(high, list)

    def test_optimization_suggestions(self):
        erg = ContributorErgonomics()
        suggestions = erg.get_optimization_suggestions()
        assert len(suggestions) > 0

    def test_friction_types(self):
        assert FrictionType.CONTRIBUTION_PATH.value == "contribution_path"
        assert FrictionLevel.EXHAUSTING.value == "exhausting"


# ═══════════════════════════════════════════════════════════════
# P10: Core Identity
# ═══════════════════════════════════════════════════════════════

class TestCoreIdentity:
    def test_identity_creates(self):
        identity = CoreIdentityPreservation()
        assert len(identity.get_all_identity()) > 0

    def test_purpose_identity(self):
        identity = CoreIdentityPreservation()
        purpose = identity.get_identity(IdentityAspect.PURPOSE)
        assert purpose is not None
        assert len(purpose.what_it_is) > 0
        assert len(purpose.what_it_is_not) > 0

    def test_architecture_identity(self):
        identity = CoreIdentityPreservation()
        arch = identity.get_identity(IdentityAspect.ARCHITECTURE)
        assert arch is not None
        assert "66" in arch.statement or "runtime" in arch.statement.lower()

    def test_values_identity(self):
        identity = CoreIdentityPreservation()
        values = identity.get_identity(IdentityAspect.VALUES)
        assert values is not None
        assert "deterministic" in str(values.what_it_is).lower()

    def test_boundaries_identity(self):
        identity = CoreIdentityPreservation()
        boundaries = identity.get_identity(IdentityAspect.BOUNDARIES)
        assert boundaries is not None
        assert len(boundaries.what_it_is_not) > 0

    def test_assess_pressure(self):
        identity = CoreIdentityPreservation()
        pressure = identity.assess_pressure(PressureType.CLOUD)
        assert pressure.risk_level in ("low", "medium", "high")
        assert len(pressure.mitigation) > 0

    def test_identity_summary(self):
        identity = CoreIdentityPreservation()
        summary = identity.get_identity_summary()
        assert len(summary) > 0
        assert "NOT" in summary  # Should contain what it is NOT
