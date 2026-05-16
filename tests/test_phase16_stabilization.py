"""
Phase 16: Tests for Stabilization, Consolidation & Operational Hardening
"""

import pytest

from core.project_manager.runtime.stabilization.consolidation import (
    RuntimeConsolidationEngine, ConsolidationType, ConsolidationPriority,
)
from core.project_manager.runtime.stabilization.freeze_zones import (
    ArchitectureFreezeZones, FreezeLevel,
)
from core.project_manager.runtime.stabilization.hardening import (
    OperationalHardeningSuite, StressType, HardeningResult,
)
from core.project_manager.runtime.stabilization.contributor_validation import (
    RealContributorValidator, ValidationMetric, MetricStatus,
)
from core.project_manager.runtime.stabilization.governance_reduction import (
    GovernanceReductionPass, GovernanceIssueType, ReductionPriority,
)
from core.project_manager.runtime.stabilization.slimming import (
    RuntimeSlimmingInitiative, SlimmingType,
)
from core.project_manager.runtime.stabilization.freeze_review import (
    ArchitecturalFreezeReview, SettlementStatus,
)
from core.project_manager.runtime.stabilization.meta_limiter import (
    MetaSystemLimiter, MetaLevel, LimiterAction,
)
from core.project_manager.runtime.stabilization.ecosystem_stability import (
    EcosystemStabilityValidator, StabilityDimension, StabilityLevel,
)
from core.project_manager.runtime.stabilization.enoughness import (
    EnoughnessEngine, EnoughnessVerdict,
)


# P1: Consolidation
class TestConsolidation:
    def test_engine_creates(self):
        engine = RuntimeConsolidationEngine()
        assert engine.total_items > 0

    def test_report_has_critical(self):
        engine = RuntimeConsolidationEngine()
        report = engine.generate_report()
        assert len(report.critical_items) > 0

    def test_total_savings(self):
        engine = RuntimeConsolidationEngine()
        assert engine.total_potential_savings > 0

    def test_apply_consolidation(self):
        engine = RuntimeConsolidationEngine()
        result = engine.apply_consolidation("CalmDimension duplication")
        assert result


# P2: Freeze Zones
class TestFreezeZones:
    def test_freeze_zones_creates(self):
        zones = ArchitectureFreezeZones()
        assert zones.total_frozen > 0

    def test_frozen_concepts(self):
        zones = ArchitectureFreezeZones()
        frozen = zones.get_frozen_concepts()
        assert len(frozen) > 0

    def test_check_change_blocked(self):
        zones = ArchitectureFreezeZones()
        allowed, reason = zones.check_change_allowed("approval_semantics", [])
        assert not allowed

    def test_check_change_allowed(self):
        zones = ArchitectureFreezeZones()
        allowed, reason = zones.check_change_allowed(
            "approval_semantics",
            ["architect", "safety_reviewer", "team_lead"]
        )
        assert allowed


# P3: Hardening
class TestHardening:
    def test_suite_creates(self):
        suite = OperationalHardeningSuite()
        assert suite.total_tests > 0

    def test_stress_types(self):
        assert StressType.LONG_SESSION.value == "long_session"
        assert StressType.CONTEXT_STORM.value == "context_storm"

    def test_hardening_result(self):
        assert HardeningResult.PASSED.value == "passed"
        assert HardeningResult.FAILED.value == "failed"


# P4: Contributor Validation
class TestContributorValidation:
    def test_validator_creates(self):
        validator = RealContributorValidator()
        assert validator is not None

    def test_generate_report(self):
        validator = RealContributorValidator()
        report = validator.generate_report()
        assert len(report.metrics) > 0

    def test_record_measurement(self):
        validator = RealContributorValidator()
        validator.record_measurement(ValidationMetric.ONBOARDING_TIME, 90)
        metric = validator.get_metric(ValidationMetric.ONBOARDING_TIME)
        assert metric.status == MetricStatus.MEASURED


# P5: Governance Reduction
class TestGovernanceReduction:
    def test_reduction_creates(self):
        reduction = GovernanceReductionPass()
        assert reduction.total_issues > 0

    def test_high_priority_issues(self):
        reduction = GovernanceReductionPass()
        report = reduction.generate_report()
        assert len(report.high_priority) > 0

    def test_safe_removals(self):
        reduction = GovernanceReductionPass()
        report = reduction.generate_report()
        assert len(report.safe_to_remove) > 0


# P6: Slimming
class TestSlimming:
    def test_slimming_creates(self):
        slimming = RuntimeSlimmingInitiative()
        assert slimming.total_items > 0

    def test_potential_savings(self):
        slimming = RuntimeSlimmingInitiative()
        assert slimming.total_potential_savings > 0

    def test_safe_removals(self):
        slimming = RuntimeSlimmingInitiative()
        report = slimming.generate_report()
        assert len(report.safe_removals) > 0


# P7: Freeze Review
class TestFreezeReview:
    def test_review_creates(self):
        review = ArchitecturalFreezeReview()
        assert review.total_subsystems > 0

    def test_settled_subsystems(self):
        review = ArchitecturalFreezeReview()
        settled = review.get_settled_subsystems()
        assert len(settled) > 0

    def test_should_freeze(self):
        review = ArchitecturalFreezeReview()
        freeze, reason = review.should_freeze("state_lifecycle")
        assert freeze


# P8: Meta Limiter
class TestMetaLimiter:
    def test_limiter_creates(self):
        limiter = MetaSystemLimiter()
        assert limiter is not None

    def test_blocks_meta_meta(self):
        limiter = MetaSystemLimiter()
        check = limiter.check_system("test", MetaLevel.META_META)
        assert check.action == LimiterAction.BLOCK

    def test_allows_core(self):
        limiter = MetaSystemLimiter()
        check = limiter.check_system("test", MetaLevel.CORE)
        assert check.action == LimiterAction.ALLOW

    def test_dangerous_patterns(self):
        limiter = MetaSystemLimiter()
        patterns = limiter.get_dangerous_patterns()
        assert len(patterns) > 0


# P9: Ecosystem Stability
class TestEcosystemStability:
    def test_validator_creates(self):
        validator = EcosystemStabilityValidator()
        assert validator is not None

    def test_generate_report(self):
        validator = EcosystemStabilityValidator()
        report = validator.generate_report()
        assert len(report.indicators) > 0

    def test_stability_levels(self):
        assert StabilityLevel.STABLE.value == "stable"
        assert StabilityLevel.CRITICAL.value == "critical"


# P10: Enoughness
class TestEnoughness:
    def test_engine_creates(self):
        engine = EnoughnessEngine()
        assert engine.total_areas > 0

    def test_generate_report(self):
        engine = EnoughnessEngine()
        report = engine.generate_report()
        assert len(report.assessments) > 0

    def test_should_expand_enough(self):
        engine = EnoughnessEngine()
        expand, reason = engine.should_expand("durability", "new feature")
        assert not expand  # durability is ENOUGH

    def test_should_expand_underbuilt(self):
        engine = EnoughnessEngine()
        expand, reason = engine.should_expand("ecosystem", "new feature")
        assert expand  # ecosystem is UNDERBUILT

    def test_verdicts(self):
        assert EnoughnessVerdict.ENOUGH.value == "enough"
        assert EnoughnessVerdict.OVERBUILT.value == "overbuilt"
