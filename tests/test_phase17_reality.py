"""
Phase 17: Tests for Operational Reality & Long-Term Usage Validation
"""

import pytest

from core.project_manager.runtime.reality.long_run_sessions import (
    LongRunSessionSimulator, HealthIndicator, HealthStatus, SessionPhase,
)
from core.project_manager.runtime.reality.repo_diversity import (
    RealRepositoryDiversityValidator, RepoType, ValidationResult,
)
from core.project_manager.runtime.reality.contributor_observation import (
    ContributorRealityObserver, ObservationType, Severity,
)
from core.project_manager.runtime.reality.plugin_stress import (
    PluginEcosystemStressTester, PluginThreatType, ThreatSeverity,
)
from core.project_manager.runtime.reality.remaining import (
    GovernanceFatigueRealityCheck, FatigueIndicator, FatigueLevel,
    RecoveryUnderRealFailures, FailureType, RecoveryResult,
    CognitiveSustainabilityMonitor, CognitiveIndicator, CognitiveHealth,
    ArchitecturalRealityDriftDetector, DriftType,
    EcosystemPressureMapper, PressureSource, PressureIntensity,
    RealityCalibratedSimplification, SimplificationType,
)


# P1: Long-Run Sessions
class TestLongRunSessions:
    def test_simulator_creates(self):
        sim = LongRunSessionSimulator("test")
        assert sim is not None

    def test_record_snapshot(self):
        sim = LongRunSessionSimulator("test")
        snap = sim.record_snapshot(HealthIndicator.LATENCY, 100)
        assert snap.indicator == HealthIndicator.LATENCY
        assert snap.value == 100

    def test_simulate_typical_session(self):
        sim = LongRunSessionSimulator("test")
        report = sim.simulate_typical_session(days=7)
        assert report.session_id == "test"
        assert len(report.snapshots) > 0
        assert len(report.phases_completed) > 0

    def test_health_status(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.CRITICAL.value == "critical"


# P2: Repo Diversity
class TestRepoDiversity:
    def test_validator_creates(self):
        val = RealRepositoryDiversityValidator()
        assert val is not None

    def test_validate_repo_type(self):
        val = RealRepositoryDiversityValidator()
        result = val.validate_repo_type(RepoType.MONOREPO)
        assert result.repo_type == RepoType.MONOREPO

    def test_run_all_validations(self):
        val = RealRepositoryDiversityValidator()
        report = val.run_all_validations()
        assert len(report.validations) > 0

    def test_repo_types(self):
        assert RepoType.MONOREPO.value == "monorepo"
        assert RepoType.LEGACY.value == "legacy"


# P3: Contributor Observation
class TestContributorObservation:
    def test_observer_creates(self):
        obs = ContributorRealityObserver()
        assert obs.total_observations > 0

    def test_generate_report(self):
        obs = ContributorRealityObserver()
        report = obs.generate_report()
        assert len(report.observations) > 0

    def test_critical_observations(self):
        obs = ContributorRealityObserver()
        critical = obs.get_critical_issues()
        assert len(critical) > 0

    def test_observation_types(self):
        assert ObservationType.CONFUSION_POINT.value == "confusion_point"
        assert Severity.CRITICAL.value == "critical"


# P4: Plugin Stress
class TestPluginStress:
    def test_tester_creates(self):
        tester = PluginEcosystemStressTester()
        assert tester.total_threats > 0

    def test_run_all_tests(self):
        tester = PluginEcosystemStressTester()
        report = tester.run_all_tests()
        assert report.blocked + report.passed_through == tester.total_threats

    def test_threat_types(self):
        assert PluginThreatType.MALICIOUS.value == "malicious"
        assert ThreatSeverity.CRITICAL.value == "critical"


# P5: Governance Fatigue
class TestGovernanceFatigue:
    def test_check_creates(self):
        check = GovernanceFatigueRealityCheck()
        assert check is not None

    def test_assess_healthy(self):
        check = GovernanceFatigueRealityCheck()
        result = check.assess(FatigueIndicator.APPROVAL_SKIP_RATE, 0.1)
        assert result.level == FatigueLevel.HEALTHY

    def test_assess_burnout(self):
        check = GovernanceFatigueRealityCheck()
        result = check.assess(FatigueIndicator.APPROVAL_SKIP_RATE, 0.9)
        assert result.level == FatigueLevel.BURNOUT


# P6: Real Failures
class TestRealFailures:
    def test_scenarios_exist(self):
        recovery = RecoveryUnderRealFailures()
        assert recovery.total_scenarios > 0

    def test_get_scenario(self):
        recovery = RecoveryUnderRealFailures()
        scenario = recovery.get_scenario("interrupted_indexing")
        assert scenario is not None
        assert scenario.failure_type == FailureType.INTERRUPTED_INDEXING

    def test_failure_types(self):
        assert FailureType.INTERRUPTED_INDEXING.value == "interrupted_indexing"
        assert RecoveryResult.FULL_RECOVERY.value == "full_recovery"


# P7: Cognitive Sustainability
class TestCognitiveSustainability:
    def test_monitor_creates(self):
        monitor = CognitiveSustainabilityMonitor()
        assert monitor is not None

    def test_assess_healthy(self):
        monitor = CognitiveSustainabilityMonitor()
        health = monitor.assess(CognitiveIndicator.MENTAL_EXHAUSTION, 0.1)
        assert health == CognitiveHealth.HEALTHY

    def test_assess_unsustainable(self):
        monitor = CognitiveSustainabilityMonitor()
        health = monitor.assess(CognitiveIndicator.MENTAL_EXHAUSTION, 0.9)
        assert health == CognitiveHealth.UNSUSTAINABLE


# P8: Reality Drift
class TestRealityDrift:
    def test_detector_creates(self):
        detector = ArchitecturalRealityDriftDetector()
        assert detector.total_drifts > 0

    def test_high_severity_drifts(self):
        detector = ArchitecturalRealityDriftDetector()
        high = detector.get_high_severity_drifts()
        assert len(high) > 0

    def test_drift_types(self):
        assert DriftType.UNDOCUMENTED_PATTERN.value == "undocumented_pattern"
        assert DriftType.GOVERNANCE_BYPASS_RITUAL.value == "governance_bypass_ritual"


# P9: Ecosystem Pressure
class TestEcosystemPressure:
    def test_mapper_creates(self):
        mapper = EcosystemPressureMapper()
        assert mapper.total_pressures > 0

    def test_get_by_intensity(self):
        mapper = EcosystemPressureMapper()
        high = mapper.get_pressures_by_intensity(PressureIntensity.HIGH)
        assert len(high) > 0

    def test_pressures_to_address(self):
        mapper = EcosystemPressureMapper()
        to_address = mapper.get_pressures_to_address()
        # All pressures have should_address=False in current config
        assert len(to_address) == 0

    def test_pressure_sources(self):
        assert PressureSource.ENTERPRISE.value == "enterprise"
        assert PressureIntensity.CRITICAL.value == "critical"


# P10: Reality Simplification
class TestRealitySimplification:
    def test_simplification_creates(self):
        simp = RealityCalibratedSimplification()
        assert simp.total_opportunities > 0

    def test_safe_removals(self):
        simp = RealityCalibratedSimplification()
        safe = simp.get_safe_removals()
        assert len(safe) > 0

    def test_total_savings(self):
        simp = RealityCalibratedSimplification()
        savings = simp.get_total_savings()
        assert savings > 0

    def test_simplification_types(self):
        assert SimplificationType.UNUSED_WORKFLOW.value == "unused_workflow"
        assert SimplificationType.OVER_ENGINEERED.value == "over_engineered"
