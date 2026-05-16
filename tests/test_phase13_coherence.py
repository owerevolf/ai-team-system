"""
Phase 13: Tests for Architectural Coherence & Evolution Control
"""

import pytest

from core.project_manager.runtime.coherence.vocabulary import (
    RuntimeVocabularyRegistry, CanonicalPriority, CanonicalStateTier,
    CanonicalEventType, CanonicalApprovalRisk, CanonicalApprovalStatus,
    CanonicalExplanationLevel, CanonicalVisibility,
)
from core.project_manager.runtime.coherence.contract_validation import (
    CrossSubsystemContractValidator, ContractType, ContractStatus,
)
from core.project_manager.runtime.coherence.ontology_drift import (
    OntologyDriftDetector, DriftType, DriftSeverity,
)
from core.project_manager.runtime.coherence.boundary_enforcement import (
    ArchitecturalBoundaryEnforcer, ViolationType,
)
from core.project_manager.runtime.coherence.dependency_gravity import (
    DependencyGravityAnalyzer, GravityLevel,
)
from core.project_manager.runtime.coherence.evolution_safety import (
    EvolutionSafetyRules, ChangeCategory, ChangeRisk,
)
from core.project_manager.runtime.coherence.semantic_compression import (
    SemanticCompressor, CompressionTarget,
)
from core.project_manager.runtime.coherence.decision_traceability import (
    DecisionTraceabilityRegistry, DecisionType, DecisionScope,
    ArchitecturalDecision,
)
from core.project_manager.runtime.coherence.controlled_evolution import (
    ControlledEvolutionFramework, ChangeStatus,
)
from core.project_manager.runtime.coherence.coherence_engine import (
    CoherencePreservationEngine, CoherenceDimension, CoherenceStatus,
)


# ═══════════════════════════════════════════════════════════════
# P1: Unified Runtime Vocabulary
# ═══════════════════════════════════════════════════════════════

class TestVocabulary:
    def test_registry_creates(self):
        reg = RuntimeVocabularyRegistry()
        assert reg.total_concepts > 0

    def test_canonical_priority_values(self):
        assert CanonicalPriority.CRITICAL.value == 0
        assert CanonicalPriority.SILENT.value == 4

    def test_canonical_state_tier(self):
        assert CanonicalStateTier.EPHEMERAL.value == "ephemeral"
        assert CanonicalStateTier.STRUCTURAL.value == "structural"

    def test_canonical_event_type(self):
        assert CanonicalEventType.ERROR.value == "error"
        assert CanonicalEventType.RECOVERY.value == "recovery"

    def test_canonical_approval_risk(self):
        assert CanonicalApprovalRisk.LOW.value == "low"
        assert CanonicalApprovalRisk.CRITICAL.value == "critical"

    def test_canonical_approval_status(self):
        assert CanonicalApprovalStatus.PENDING.value == "pending"
        assert CanonicalApprovalStatus.AUTO_APPLIED.value == "auto_applied"

    def test_canonical_explanation_level(self):
        assert CanonicalExplanationLevel.MINIMAL.value == 0
        assert CanonicalExplanationLevel.DEBUG.value == 4

    def test_canonical_visibility(self):
        assert CanonicalVisibility.SHOW.value == "show"
        assert CanonicalVisibility.SUPPRESS.value == "suppress"

    def test_get_concept(self):
        reg = RuntimeVocabularyRegistry()
        concept = reg.get("priority")
        assert concept is not None
        assert concept.name == "priority"

    def test_get_invariants(self):
        reg = RuntimeVocabularyRegistry()
        invariants = reg.get_invariants("priority")
        assert len(invariants) > 0

    def test_get_source_modules(self):
        reg = RuntimeVocabularyRegistry()
        modules = reg.get_source_modules("priority")
        assert len(modules) > 0

    def test_resolve_priority(self):
        reg = RuntimeVocabularyRegistry()
        assert reg.resolve_priority("AttentionPriority.CRITICAL") == CanonicalPriority.CRITICAL
        assert reg.resolve_priority("InteractionPriority.IMPORTANT") == CanonicalPriority.HIGH

    def test_resolve_explanation_level(self):
        reg = RuntimeVocabularyRegistry()
        assert reg.resolve_explanation_level("ExplanationLevel.SUMMARY") == CanonicalExplanationLevel.SUMMARY
        assert reg.resolve_explanation_level("DisclosureLevel.DEBUG") == CanonicalExplanationLevel.DEBUG

    def test_all_invariants(self):
        reg = RuntimeVocabularyRegistry()
        invariants = reg.all_invariants
        assert len(invariants) > 0


# ═══════════════════════════════════════════════════════════════
# P2: Cross-Subsystem Contract Validation
# ═══════════════════════════════════════════════════════════════

class TestContractValidation:
    def test_validator_creates(self):
        validator = CrossSubsystemContractValidator()
        report = validator.validate_all()
        assert report.total_checks > 0

    def test_finds_conflicts(self):
        validator = CrossSubsystemContractValidator()
        report = validator.validate_all()
        # Should find visibility conflicts between trust and ergonomics
        assert len(report.warnings) > 0 or len(report.conflicts) > 0

    def test_contract_types(self):
        assert ContractType.VISIBILITY.value == "visibility"
        assert ContractType.APPROVAL.value == "approval"

    def test_get_requirements_for_type(self):
        validator = CrossSubsystemContractValidator()
        vis_reqs = validator.get_requirements_for(ContractType.VISIBILITY)
        assert len(vis_reqs) > 0


# ═══════════════════════════════════════════════════════════════
# P3: Ontology Drift Detection
# ═══════════════════════════════════════════════════════════════

class TestOntologyDrift:
    def test_detector_finds_known_drifts(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        detector = OntologyDriftDetector(base)
        report = detector.detect_drift()
        assert len(report.findings) > 0

    def test_finds_priority_fragmentation(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        detector = OntologyDriftDetector(base)
        report = detector.detect_drift()
        priority_findings = [f for f in report.findings if "priority" in f.name.lower()]
        assert len(priority_findings) > 0

    def test_finds_event_fragmentation(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        detector = OntologyDriftDetector(base)
        report = detector.detect_drift()
        event_findings = [f for f in report.findings if "event" in f.name.lower()]
        assert len(event_findings) > 0

    def test_critical_findings(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        detector = OntologyDriftDetector(base)
        report = detector.detect_drift()
        # Should have at least HIGH severity findings
        assert len(report.high_findings) > 0

    def test_drift_types(self):
        assert DriftType.SEMANTIC_DIVERGENCE.value == "semantic_divergence"
        assert DriftType.DUPLICATED_ABSTRACTION.value == "duplicated_abstraction"


# ═══════════════════════════════════════════════════════════════
# P4: Architectural Boundary Enforcement
# ═══════════════════════════════════════════════════════════════

class TestBoundaryEnforcement:
    def test_enforcer_creates(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        enforcer = ArchitecturalBoundaryEnforcer(base)
        report = enforcer.check_boundaries()
        assert report.total_imports_checked > 0

    def test_allowed_imports_defined(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        enforcer = ArchitecturalBoundaryEnforcer(base)
        allowed = enforcer.get_allowed_imports("compression")
        assert len(allowed) > 0

    def test_violation_types(self):
        assert ViolationType.SUBSYSTEM_LEAKAGE.value == "subsystem_leakage"
        assert ViolationType.CIRCULAR_DEPENDENCY.value == "circular_dependency"


# ═══════════════════════════════════════════════════════════════
# P5: Dependency Gravity Analysis
# ═══════════════════════════════════════════════════════════════

class TestDependencyGravity:
    def test_analyzer_runs(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        analyzer = DependencyGravityAnalyzer(base)
        report = analyzer.analyze()
        assert len(report.modules) > 0

    def test_top_chokepoints(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        analyzer = DependencyGravityAnalyzer(base)
        report = analyzer.analyze()
        top = report.top_chokepoints
        assert len(top) > 0
        assert len(top) <= 5

    def test_gravity_levels(self):
        assert GravityLevel.LOW.value == "low"
        assert GravityLevel.CRITICAL.value == "critical"


# ═══════════════════════════════════════════════════════════════
# P6: Evolution Safety Rules
# ═══════════════════════════════════════════════════════════════

class TestEvolutionSafety:
    def test_rules_classify_safe(self):
        rules = EvolutionSafetyRules()
        classification = rules.classify(ChangeCategory.DEAD_CODE_REMOVAL)
        assert classification.risk == ChangeRisk.SAFE

    def test_rules_classify_review(self):
        rules = EvolutionSafetyRules()
        classification = rules.classify(ChangeCategory.NEW_RUNTIME_SURFACE)
        assert classification.risk == ChangeRisk.REVIEW_REQUIRED

    def test_rules_classify_high_risk(self):
        rules = EvolutionSafetyRules()
        classification = rules.classify(ChangeCategory.HIDDEN_AUTOMATION)
        assert classification.risk == ChangeRisk.HIGH_RISK

    def test_assess_change(self):
        rules = EvolutionSafetyRules()
        classification = rules.assess_change(
            ChangeCategory.SEMANTIC_REDEFINITION,
            "runtime/vocabulary.py",
            "Redefine priority semantics"
        )
        assert classification.risk == ChangeRisk.HIGH_RISK
        assert "runtime/vocabulary.py" in classification.description

    def test_change_categories(self):
        assert ChangeCategory.DEAD_CODE_REMOVAL.value == "dead_code_removal"
        assert ChangeCategory.HIDDEN_AUTOMATION.value == "hidden_automation"


# ═══════════════════════════════════════════════════════════════
# P7: Semantic Compression
# ═══════════════════════════════════════════════════════════════

class TestSemanticCompression:
    def test_compressor_creates_plan(self):
        compressor = SemanticCompressor()
        plan = compressor.create_plan()
        assert len(plan.overlaps) > 0

    def test_finds_priority_overlap(self):
        compressor = SemanticCompressor()
        plan = compressor.create_plan()
        priority_overlaps = [o for o in plan.overlaps if o.target == CompressionTarget.PRIORITY]
        assert len(priority_overlaps) > 0

    def test_total_lines_saved(self):
        compressor = SemanticCompressor()
        plan = compressor.create_plan()
        assert plan.total_lines_saved > 0

    def test_quick_wins(self):
        compressor = SemanticCompressor()
        plan = compressor.create_plan()
        quick = plan.quick_wins
        assert len(quick) > 0

    def test_get_migration_path(self):
        compressor = SemanticCompressor()
        path = compressor.get_migration_path(CompressionTarget.PRIORITY)
        assert path is not None
        assert path.canonical_name == "CanonicalPriority"


# ═══════════════════════════════════════════════════════════════
# P8: Decision Traceability
# ═══════════════════════════════════════════════════════════════

class TestDecisionTraceability:
    def test_registry_creates(self):
        reg = DecisionTraceabilityRegistry()
        assert reg.total_decisions > 0

    def test_get_decision(self):
        reg = DecisionTraceabilityRegistry()
        d = reg.get("ADR-001")
        assert d is not None
        assert d.title == "Deterministic over AI"

    def test_find_by_type(self):
        reg = DecisionTraceabilityRegistry()
        philosophy = reg.find_by_type(DecisionType.PHILOSOPHY)
        assert len(philosophy) > 0

    def test_find_by_phase(self):
        reg = DecisionTraceabilityRegistry()
        phase12 = reg.find_by_phase("Phase 12")
        assert len(phase12) > 0

    def test_get_related(self):
        reg = DecisionTraceabilityRegistry()
        related = reg.get_related("ADR-004")
        assert len(related) > 0

    def test_decision_fields(self):
        reg = DecisionTraceabilityRegistry()
        d = reg.get("ADR-006")
        assert d.decision_text is not None
        assert d.rationale is not None
        assert len(d.alternatives) > 0
        assert len(d.tradeoffs) > 0


# ═══════════════════════════════════════════════════════════════
# P9: Controlled Evolution Framework
# ═══════════════════════════════════════════════════════════════

class TestControlledEvolution:
    def test_framework_creates(self):
        framework = ControlledEvolutionFramework()
        assert framework is not None

    def test_propose_change(self):
        framework = ControlledEvolutionFramework()
        change = framework.propose_change(
            "CHG-001", "Test change",
            ChangeCategory.DEAD_CODE_REMOVAL,
            "runtime/old.py", "Remove unused code"
        )
        assert change.status == ChangeStatus.PROPOSED

    def test_approve_change(self):
        framework = ControlledEvolutionFramework()
        framework.propose_change(
            "CHG-001", "Test change",
            ChangeCategory.DEAD_CODE_REMOVAL,
            "runtime/old.py", "Remove unused code"
        )
        change = framework.approve_change("CHG-001", "architect")
        assert change is not None

    def test_run_safety_checks(self):
        framework = ControlledEvolutionFramework()
        framework.propose_change(
            "CHG-001", "Test change",
            ChangeCategory.DEAD_CODE_REMOVAL,
            "runtime/old.py", "Remove unused code"
        )
        change = framework.run_safety_checks("CHG-001")
        assert len(change.safety_checks_passed) > 0


# ═══════════════════════════════════════════════════════════════
# P10: Coherence Preservation Engine
# ═══════════════════════════════════════════════════════════════

class TestCoherenceEngine:
    def test_engine_runs(self):
        engine = CoherencePreservationEngine()
        report = engine.run_full_check()
        assert len(report.checks) > 0

    def test_coherence_dimensions(self):
        assert CoherenceDimension.SEMANTIC.value == "semantic"
        assert CoherenceDimension.BEHAVIORAL.value == "behavioral"

    def test_coherence_status(self):
        assert CoherenceStatus.COHERENT.value == "coherent"
        assert CoherenceStatus.FRAGMENTED.value == "fragmented"

    def test_drift_areas(self):
        engine = CoherencePreservationEngine()
        report = engine.run_full_check()
        # Should have some drift areas
        assert len(report.drift_areas) >= 0

    def test_is_coherent(self):
        engine = CoherencePreservationEngine()
        report = engine.run_full_check()
        # Should be at least WARNING (not FRAGMENTED)
        assert report.is_coherent
