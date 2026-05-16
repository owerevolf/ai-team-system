"""
Phase 18: Tests for Reduction, Settlement & Long-Term Stewardship
"""

import pytest

from core.project_manager.runtime.stewardship.retirement import (
    SubsystemRetirementFramework, RetirementStatus, RetirementReason,
)
from core.project_manager.runtime.stewardship.semantic_settlement import (
    APISemanticSettlement, StabilityLevel,
)
from core.project_manager.runtime.stewardship.governance_settlement import (
    GovernanceSettlementReview, GovernanceEssentiality,
)
from core.project_manager.runtime.stewardship.remaining import (
    RuntimeWeightIndex, WeightDimension, WeightStatus,
    LongTermMaintainershipModel, MaintainershipRisk,
    PluginBoundaryFreezing, BoundaryType,
    ConceptualCompressionPass, CompressionType,
    EcosystemSustainabilityReview, SustainabilityDimension, SustainabilityLevel,
    ArchitecturePreservationLayer, PreservationType,
    StewardshipEngine, StewardshipVerdict,
)


# P1: Retirement
class TestRetirement:
    def test_framework_creates(self):
        fw = SubsystemRetirementFramework()
        assert fw.total_candidates > 0

    def test_safe_retirements(self):
        fw = SubsystemRetirementFramework()
        report = fw.generate_report()
        assert len(report.safe_to_retire) > 0

    def test_total_savings(self):
        fw = SubsystemRetirementFramework()
        assert fw.total_safe_savings > 0

    def test_mark_deprecated(self):
        fw = SubsystemRetirementFramework()
        result = fw.mark_deprecated("stabilization/slimming.py")
        assert result


# P2: Semantic Settlement
class TestSemanticSettlement:
    def test_settlement_creates(self):
        settlement = APISemanticSettlement()
        assert settlement.total_contracts > 0

    def test_frozen_contract(self):
        settlement = APISemanticSettlement()
        contract = settlement.get_contract("approval_semantics")
        assert contract.stability == StabilityLevel.FROZEN

    def test_change_blocked(self):
        settlement = APISemanticSettlement()
        allowed, reason = settlement.check_change_allowed("approval_semantics", [])
        assert not allowed

    def test_change_allowed(self):
        settlement = APISemanticSettlement()
        allowed, reason = settlement.check_change_allowed(
            "approval_semantics", ["architect", "safety_reviewer", "team_lead"]
        )
        assert allowed


# P3: Governance Settlement
class TestGovernanceSettlement:
    def test_review_creates(self):
        review = GovernanceSettlementReview()
        assert review.total_items > 0

    def test_removable_items(self):
        review = GovernanceSettlementReview()
        removable = review.get_removable()
        assert len(removable) > 0

    def test_essential_items(self):
        review = GovernanceSettlementReview()
        essential = review.get_essential()
        assert len(essential) > 0


# P4: Weight Index
class TestWeightIndex:
    def test_index_creates(self):
        index = RuntimeWeightIndex()
        assert index is not None

    def test_measure_healthy(self):
        index = RuntimeWeightIndex()
        m = index.measure(WeightDimension.SUBSYSTEM_COUNT, 6)
        assert m.status == WeightStatus.HEALTHY

    def test_measure_critical(self):
        index = RuntimeWeightIndex()
        m = index.measure(WeightDimension.SUBSYSTEM_COUNT, 15)
        assert m.status == WeightStatus.CRITICAL


# P5: Maintainership
class TestMaintainership:
    def test_model_creates(self):
        model = LongTermMaintainershipModel()
        assert model.total_subsystems > 0

    def test_high_risk(self):
        model = LongTermMaintainershipModel()
        high = model.get_high_risk()
        assert len(high) > 0

    def test_rotation_ready(self):
        model = LongTermMaintainershipModel()
        ready = model.get_rotation_ready()
        assert len(ready) > 0


# P6: Plugin Boundaries
class TestPluginBoundaries:
    def test_freezing_creates(self):
        freezing = PluginBoundaryFreezing()
        assert freezing.total_boundaries > 0

    def test_never_bypass(self):
        freezing = PluginBoundaryFreezing()
        boundary = freezing.check_violation(BoundaryType.NEVER_BYPASS_APPROVALS)
        assert boundary is not None
        assert "disabled" in boundary.violation_consequence.lower()


# P7: Conceptual Compression
class TestConceptualCompression:
    def test_pass_creates(self):
        comp = ConceptualCompressionPass()
        assert comp.total_opportunities > 0

    def test_high_impact(self):
        comp = ConceptualCompressionPass()
        high = comp.get_high_impact()
        assert len(high) > 0


# P8: Ecosystem Sustainability
class TestEcosystemSustainability:
    def test_review_creates(self):
        review = EcosystemSustainabilityReview()
        assert review.total_assessments > 0

    def test_unsustainable(self):
        review = EcosystemSustainabilityReview()
        unsustainable = review.get_unsustainable()
        # All should be sustainable or monitor
        assert len(unsustainable) == 0


# P9: Architecture Preservation
class TestArchitecturePreservation:
    def test_layer_creates(self):
        layer = ArchitecturePreservationLayer()
        assert layer.total_artifacts > 0

    def test_critical_artifacts(self):
        layer = ArchitecturePreservationLayer()
        critical = layer.get_critical_artifacts()
        assert len(critical) > 0

    def test_identity_preserved(self):
        layer = ArchitecturePreservationLayer()
        identity = layer.get_artifacts(PreservationType.IDENTITY)
        assert len(identity) > 0
        assert "NOT" in identity[0].content

    def test_anti_goals_preserved(self):
        layer = ArchitecturePreservationLayer()
        anti = layer.get_artifacts(PreservationType.ANTI_GOALS)
        assert len(anti) > 0
        assert "AGI" in anti[0].content


# P10: Stewardship Engine
class TestStewardshipEngine:
    def test_engine_creates(self):
        engine = StewardshipEngine()
        assert engine is not None

    def test_assess_healthy(self):
        engine = StewardshipEngine()
        assessment = engine.assess_area("durability", 0.85)
        assert assessment.verdict == StewardshipVerdict.HEALTHY

    def test_assess_critical(self):
        engine = StewardshipEngine()
        assessment = engine.assess_area("problematic", 0.2)
        assert assessment.verdict == StewardshipVerdict.CRITICAL

    def test_should_not_expand_healthy(self):
        engine = StewardshipEngine()
        expand, reason = engine.should_expand("durability", 0.85)
        assert not expand

    def test_generate_report(self):
        engine = StewardshipEngine()
        scores = {"durability": 0.85, "ergonomics": 0.80, "trust": 0.70, "ecosystem": 0.55}
        report = engine.generate_report(scores)
        assert len(report) == 4
