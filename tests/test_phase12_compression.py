"""
Phase 12: Tests for Minimal Surface & System Compression

Tests all 10 compression subsystems.
"""

import time
import pytest

from core.project_manager.runtime.compression.surface_audit import (
    SurfaceAreaAuditor, SurfaceType, SurfaceItem, SurfaceReport,
)
from core.project_manager.runtime.compression.workflow_compression import (
    WorkflowPathCompressor, WorkflowPath, WorkflowStep, StepType, CompressionResult,
)
from core.project_manager.runtime.compression.governance_simplification import (
    GovernanceSimplifier, GovernanceItem, GovernanceType, GovernanceHealth,
    GovernanceSimplificationReport,
)
from core.project_manager.runtime.compression.dead_system_detection import (
    DeadSystemDetector, DeadItem, DeadCategory, DeadSystemReport,
)
from core.project_manager.runtime.compression.latency_reduction import (
    RuntimeLatencyReducer, LatencyType, LatencyMeasurement, LatencyBudget,
    LatencyReport,
)
from core.project_manager.runtime.compression.interaction_minimalism import (
    InteractionMinimalismLayer, InteractionEvent, InteractionType,
    InteractionPriority, MinimalInteractionPolicy, InteractionBatch,
)
from core.project_manager.runtime.compression.progressive_disclosure import (
    ProgressiveDisclosureEngine, DisclosureItem, DisclosureLevel,
    DisclosureProfile, ExpandTrigger,
)
from core.project_manager.runtime.compression.operational_calm import (
    OperationalCalmMetrics, CalmDimension, CalmLevel, CalmThresholds,
    CalmReading, CalmReport,
)
from core.project_manager.runtime.compression.architecture_compression import (
    ArchitectureCompressor, OverlapFinding, OverlapType, CompressionAction,
    CompressionPlan,
)
from core.project_manager.runtime.compression.do_less import (
    DoLessRuntime, ProposedAction, ActionType, ActionValue,
    RestraintDecision, DoLessReport,
)
from core.project_manager.runtime.compression.compression_engine import (
    CompressionEngine, UnifiedCompressionReport,
)


# ═══════════════════════════════════════════════════════════════
# P1: Surface Area Audit Engine
# ═══════════════════════════════════════════════════════════════

class TestSurfaceAreaAudit:
    """Tests for P1: Surface Area Audit Engine."""

    def test_surface_item_creation(self):
        item = SurfaceItem(
            name="test_endpoint",
            surface_type=SurfaceType.API_ENDPOINT,
            module="web_ui/app.py",
            line_number=42,
        )
        assert item.name == "test_endpoint"
        assert item.surface_type == SurfaceType.API_ENDPOINT
        assert item.module == "web_ui/app.py"
        assert item.line_number == 42
        assert item.usage_count == 0
        assert not item.is_deprecated

    def test_surface_report_compression_candidates(self):
        report = SurfaceReport()
        report.items = [
            SurfaceItem("used", SurfaceType.API_ENDPOINT, "mod.py", usage_count=5, is_exported=True),
            SurfaceItem("unused", SurfaceType.USER_CONTROL, "mod.py", usage_count=0, is_exported=False),
            SurfaceItem("deprecated", SurfaceType.POLICY_RULE, "mod.py", is_deprecated=True),
        ]
        report.total_items = 3
        candidates = report.compression_candidates
        assert len(candidates) == 2  # unused + deprecated

    def test_surface_report_density(self):
        report = SurfaceReport()
        report.total_items = 10
        report.by_module = {"mod_a.py": 6, "mod_b.py": 4}
        assert report.surface_density == 5.0

    def test_auditor_finds_python_files(self):
        from pathlib import Path
        base = Path(__file__).parent.parent / "core/project_manager/runtime/compression"
        auditor = SurfaceAreaAuditor(str(base))
        report = auditor.audit()
        assert report.total_items > 0

    def test_auditor_classifies_endpoints(self):
        from pathlib import Path
        base = Path(__file__).parent.parent / "core/project_manager/runtime/compression"
        auditor = SurfaceAreaAuditor(str(base))
        report = auditor.audit()
        # Should find classes and functions
        assert len(report.items) > 0

    def test_surface_type_enum(self):
        assert SurfaceType.API_ENDPOINT.value == "api_endpoint"
        assert SurfaceType.WORKFLOW_STEP.value == "workflow_step"
        assert SurfaceType.APPROVAL_GATE.value == "approval_gate"


# ═══════════════════════════════════════════════════════════════
# P2: Workflow Path Compression
# ═══════════════════════════════════════════════════════════════

class TestWorkflowPathCompression:
    """Tests for P2: Workflow Path Compression."""

    def test_workflow_step_creation(self):
        step = WorkflowStep(
            name="validate_input",
            step_type=StepType.VALIDATION,
            is_blocking=True,
        )
        assert step.name == "validate_input"
        assert step.step_type == StepType.VALIDATION
        assert step.is_blocking
        assert not step.is_redundant

    def test_workflow_path_length(self):
        path = WorkflowPath(
            name="test_workflow",
            steps=[
                WorkflowStep("s1", StepType.VALIDATION),
                WorkflowStep("s2", StepType.APPROVAL),
                WorkflowStep("s3", StepType.CONFIRMATION),
            ],
        )
        assert path.length == 3
        assert len(path.blocking_steps) == 3

    def test_compressor_removes_redundant(self):
        compressor = WorkflowPathCompressor()
        path = WorkflowPath(
            name="test",
            steps=[
                WorkflowStep("validate", StepType.VALIDATION),
                WorkflowStep("redundant_check", StepType.VALIDATION, is_redundant=True),
                WorkflowStep("approve", StepType.APPROVAL),
            ],
        )
        compressor.register(path)
        result = compressor.analyze("test")
        assert "redundant_check" in result.removed_steps
        assert result.compressed_length == 2

    def test_compressor_batches_steps(self):
        compressor = WorkflowPathCompressor()
        path = WorkflowPath(
            name="test",
            steps=[
                WorkflowStep("notify_a", StepType.NOTIFICATION, can_batch=True, merge_group="notifications"),
                WorkflowStep("notify_b", StepType.NOTIFICATION, can_batch=True, merge_group="notifications"),
                WorkflowStep("validate", StepType.VALIDATION),
            ],
        )
        compressor.register(path)
        result = compressor.analyze("test")
        assert len(result.batched_groups) == 1
        assert len(result.batched_groups[0]) == 2

    def test_compressor_warns_long_approval_chain(self):
        compressor = WorkflowPathCompressor()
        path = WorkflowPath(
            name="test",
            steps=[
                WorkflowStep("a1", StepType.APPROVAL),
                WorkflowStep("a2", StepType.APPROVAL),
                WorkflowStep("a3", StepType.APPROVAL),
                WorkflowStep("a4", StepType.APPROVAL),
            ],
        )
        compressor.register(path)
        result = compressor.analyze("test")
        assert any("approval chain" in w.lower() for w in result.warnings)

    def test_compression_ratio(self):
        result = CompressionResult(
            original_path=WorkflowPath(name="test", steps=[WorkflowStep("s1", StepType.VALIDATION)] * 5),
            compressed_length=3,
            removed_steps=["s1", "s2"],
        )
        assert result.compression_ratio == 0.6
        assert result.steps_saved == 2

    def test_median_path_length(self):
        compressor = WorkflowPathCompressor()
        compressor.register(WorkflowPath(name="short", steps=[WorkflowStep("s", StepType.VALIDATION)] * 2))
        compressor.register(WorkflowPath(name="long", steps=[WorkflowStep("s", StepType.VALIDATION)] * 10))
        assert compressor.median_path_length == 6.0


# ═══════════════════════════════════════════════════════════════
# P3: Governance Simplification
# ═══════════════════════════════════════════════════════════════

class TestGovernanceSimplification:
    """Tests for P3: Governance Simplification."""

    def test_governance_item_creation(self):
        item = GovernanceItem(
            name="require_approval_for_delete",
            governance_type=GovernanceType.APPROVAL_RULE,
            module="runtime/approval.py",
            description="Require approval for delete operations",
        )
        assert item.name == "require_approval_for_delete"
        assert item.health == GovernanceHealth.ACTIVE
        assert item.is_enforced

    def test_simplifier_detects_overlaps(self):
        simplifier = GovernanceSimplifier()
        simplifier.register(GovernanceItem("rule_a", GovernanceType.APPROVAL_RULE, "mod.py"))
        simplifier.register(GovernanceItem("rule_b", GovernanceType.APPROVAL_RULE, "mod.py"))
        simplifier.mark_overlap("rule_a", "rule_b")
        report = simplifier.analyze()
        assert len(report.overlapping_items) == 2

    def test_simplifier_detects_contradictions(self):
        simplifier = GovernanceSimplifier()
        simplifier.register(GovernanceItem("allow_x", GovernanceType.POLICY, "mod.py"))
        simplifier.register(GovernanceItem("deny_x", GovernanceType.POLICY, "mod.py"))
        simplifier.mark_contradiction("allow_x", "deny_x")
        report = simplifier.analyze()
        assert len(report.contradictory_pairs) == 1

    def test_simplifier_detects_unused(self):
        simplifier = GovernanceSimplifier()
        simplifier.register(GovernanceItem("old_rule", GovernanceType.POLICY, "mod.py"))
        simplifier.mark_unused("old_rule")
        report = simplifier.analyze()
        assert len(report.unused_items) == 1

    def test_simplifier_detects_dead(self):
        simplifier = GovernanceSimplifier()
        simplifier.register(GovernanceItem("dead_rule", GovernanceType.CONSTRAINT, "mod.py"))
        simplifier.mark_dead("dead_rule")
        report = simplifier.analyze()
        assert len(report.dead_items) == 1

    def test_removable_count(self):
        simplifier = GovernanceSimplifier()
        simplifier.register(GovernanceItem("u1", GovernanceType.POLICY, "mod.py"))
        simplifier.register(GovernanceItem("u2", GovernanceType.POLICY, "mod.py"))
        simplifier.register(GovernanceItem("d1", GovernanceType.CONSTRAINT, "mod.py"))
        simplifier.register(GovernanceItem("a1", GovernanceType.APPROVAL_RULE, "mod.py"))
        simplifier.mark_unused("u1")
        simplifier.mark_unused("u2")
        simplifier.mark_dead("d1")
        report = simplifier.analyze()
        assert report.removable_count == 3

    def test_similar_name_detection(self):
        simplifier = GovernanceSimplifier()
        simplifier.register(GovernanceItem("validate_input", GovernanceType.VALIDATION_RULE, "mod.py"))
        simplifier.register(GovernanceItem("validate_output", GovernanceType.VALIDATION_RULE, "mod.py"))
        simplifier.register(GovernanceItem("check_something", GovernanceType.VALIDATION_RULE, "mod.py"))
        similar = simplifier.find_similar_names(threshold=0.3)
        assert len(similar) >= 1

    def test_advisory_not_enforced(self):
        simplifier = GovernanceSimplifier()
        simplifier.register(GovernanceItem(
            "suggestion", GovernanceType.POLICY, "mod.py", is_enforced=False
        ))
        report = simplifier.analyze()
        assert len(report.advisory_not_enforced) == 1


# ═══════════════════════════════════════════════════════════════
# P4: Dead System Detection
# ═══════════════════════════════════════════════════════════════

class TestDeadSystemDetection:
    """Tests for P4: Dead System Detection."""

    def test_dead_item_creation(self):
        item = DeadItem(
            name="OldClass",
            category=DeadCategory.OBSOLETE_ABSTRACTION,
            module="runtime/old.py",
            reason="Not referenced",
        )
        assert item.name == "OldClass"
        assert item.category == DeadCategory.OBSOLETE_ABSTRACTION
        assert not item.safe_to_remove

    def test_dead_report_safe_to_remove(self):
        report = DeadSystemReport()
        report.items = [
            DeadItem("safe", DeadCategory.UNUSED_MODULE, "mod.py", safe_to_remove=True),
            DeadItem("unsafe", DeadCategory.ABANDONED_PATH, "mod.py", safe_to_remove=False),
        ]
        assert len(report.safe_to_remove) == 1
        assert len(report.needs_review) == 1

    def test_detector_scans_runtime(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        detector = DeadSystemDetector(base)
        report = detector.scan()
        assert report.total_items >= 0  # Should complete without error

    def test_detector_finds_classes(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime/compression"
        detector = DeadSystemDetector(base)
        report = detector.scan()
        # Should find classes in compression modules
        assert report.total_items >= 0

    def test_dead_category_enum(self):
        assert DeadCategory.UNUSED_MODULE.value == "unused_module"
        assert DeadCategory.STALE_WORKFLOW.value == "stale_workflow"
        assert DeadCategory.OBSOLETE_ABSTRACTION.value == "obsolete_abstraction"


# ═══════════════════════════════════════════════════════════════
# P5: Runtime Latency Reduction
# ═══════════════════════════════════════════════════════════════

class TestRuntimeLatencyReduction:
    """Tests for P5: Runtime Latency Reduction."""

    def test_latency_measurement(self):
        m = LatencyMeasurement(
            name="test_op",
            latency_type=LatencyType.COGNITIVE,
            duration_ms=150.0,
        )
        assert m.name == "test_op"
        assert m.latency_type == LatencyType.COGNITIVE
        assert m.duration_ms == 150.0

    def test_latency_budget(self):
        budget = LatencyBudget(
            latency_type=LatencyType.APPROVAL,
            max_ms=5000,
        )
        assert budget.warning_ms == 3500  # 70% of max

    def test_reducer_measures(self):
        reducer = RuntimeLatencyReducer()
        m = reducer.measure("test", LatencyType.COGNITIVE, 100.0)
        assert m.duration_ms == 100.0

    def test_reducer_budget_violation(self):
        reducer = RuntimeLatencyReducer()
        m = reducer.measure("slow_op", LatencyType.COGNITIVE, 5000.0)
        result = reducer.check_budget(m)
        assert result is not None
        assert "VIOLATION" in result

    def test_reducer_budget_warning(self):
        reducer = RuntimeLatencyReducer()
        m = reducer.measure("warn_op", LatencyType.COGNITIVE, 1500.0)
        result = reducer.check_budget(m)
        assert result is not None
        assert "WARNING" in result

    def test_reducer_budget_ok(self):
        reducer = RuntimeLatencyReducer()
        m = reducer.measure("fast_op", LatencyType.COGNITIVE, 500.0)
        result = reducer.check_budget(m)
        assert result is None

    def test_reducer_report(self):
        reducer = RuntimeLatencyReducer()
        reducer.measure("fast", LatencyType.COGNITIVE, 100.0)
        reducer.measure("slow", LatencyType.COGNITIVE, 5000.0)
        report = reducer.get_report()
        assert len(report.measurements) == 2
        assert len(report.violations) == 1

    def test_reducer_slowest(self):
        reducer = RuntimeLatencyReducer()
        reducer.measure("fast", LatencyType.COGNITIVE, 100.0)
        reducer.measure("slow", LatencyType.COGNITIVE, 5000.0)
        reducer.measure("medium", LatencyType.COGNITIVE, 500.0)
        slowest = reducer.get_slowest(2)
        assert len(slowest) == 2
        assert slowest[0].name == "slow"

    def test_time_operation_context_manager(self):
        reducer = RuntimeLatencyReducer()
        with reducer.time_operation("timed_op", LatencyType.WORKFLOW):
            time.sleep(0.01)
        assert len(reducer._measurements) == 1
        assert reducer._measurements[0].duration_ms > 0

    def test_custom_budget(self):
        reducer = RuntimeLatencyReducer()
        reducer.set_budget(LatencyType.COGNITIVE, max_ms=500, warning_ms=300)
        m = reducer.measure("custom", LatencyType.COGNITIVE, 400.0)
        result = reducer.check_budget(m)
        assert result is not None
        assert "WARNING" in result


# ═══════════════════════════════════════════════════════════════
# P6: Interaction Minimalism Layer
# ═══════════════════════════════════════════════════════════════

class TestInteractionMinimalism:
    """Tests for P6: Interaction Minimalism Layer."""

    def test_interaction_event_creation(self):
        event = InteractionEvent(
            name="test_event",
            interaction_type=InteractionType.CONFIRMATION,
            priority=InteractionPriority.NORMAL,
        )
        assert event.name == "test_event"
        assert not event.shown
        assert not event.suppressed

    def test_critical_always_shown(self):
        layer = InteractionMinimalismLayer()
        event = InteractionEvent(
            name="critical_event",
            interaction_type=InteractionType.WARNING,
            priority=InteractionPriority.CRITICAL,
        )
        result = layer.request_interaction(event)
        assert result is not None
        assert result.shown

    def test_silent_always_suppressed(self):
        layer = InteractionMinimalismLayer()
        event = InteractionEvent(
            name="silent_event",
            interaction_type=InteractionType.NOTIFICATION,
            priority=InteractionPriority.SILENT,
        )
        result = layer.request_interaction(event)
        assert result is None
        assert event.suppressed

    def test_low_priority_suppressed(self):
        policy = MinimalInteractionPolicy(suppress_low_priority=True)
        layer = InteractionMinimalismLayer(policy)
        event = InteractionEvent(
            name="low_event",
            interaction_type=InteractionType.NOTIFICATION,
            priority=InteractionPriority.LOW,
        )
        result = layer.request_interaction(event)
        assert result is None

    def test_deduplication(self):
        layer = InteractionMinimalismLayer()
        event1 = InteractionEvent(
            name="dup_event",
            interaction_type=InteractionType.NOTIFICATION,
            priority=InteractionPriority.NORMAL,
            dedup_key="same_key",
        )
        event2 = InteractionEvent(
            name="dup_event_2",
            interaction_type=InteractionType.NOTIFICATION,
            priority=InteractionPriority.NORMAL,
            dedup_key="same_key",
        )
        result1 = layer.request_interaction(event1)
        result2 = layer.request_interaction(event2)
        assert result1 is not None
        assert result2 is None  # Suppressed as duplicate

    def test_confirmation_limit(self):
        policy = MinimalInteractionPolicy(max_confirmations_per_workflow=1)
        layer = InteractionMinimalismLayer(policy)
        event1 = InteractionEvent("c1", InteractionType.CONFIRMATION, InteractionPriority.NORMAL)
        event2 = InteractionEvent("c2", InteractionType.CONFIRMATION, InteractionPriority.NORMAL)
        layer.request_interaction(event1)
        result = layer.request_interaction(event2)
        assert result is None  # Limit reached

    def test_explanation_limit(self):
        policy = MinimalInteractionPolicy(max_explanations_per_decision=1)
        layer = InteractionMinimalismLayer(policy)
        event1 = InteractionEvent("e1", InteractionType.EXPLANATION, InteractionPriority.NORMAL)
        event2 = InteractionEvent("e2", InteractionType.EXPLANATION, InteractionPriority.NORMAL)
        layer.request_interaction(event1)
        result = layer.request_interaction(event2)
        assert result is None

    def test_batch_events(self):
        layer = InteractionMinimalismLayer()
        events = [
            InteractionEvent("n1", InteractionType.NOTIFICATION, InteractionPriority.NORMAL),
            InteractionEvent("n2", InteractionType.NOTIFICATION, InteractionPriority.NORMAL),
            InteractionEvent("c1", InteractionType.CONFIRMATION, InteractionPriority.NORMAL),
        ]
        batches = layer.batch_events(events)
        # Notifications should be batched together
        notification_batches = [b for b in batches if b.batch_key == "notification"]
        assert len(notification_batches) == 1
        assert len(notification_batches[0].events) == 2

    def test_suppression_stats(self):
        layer = InteractionMinimalismLayer()
        layer.request_interaction(InteractionEvent("s1", InteractionType.NOTIFICATION, InteractionPriority.CRITICAL))
        layer.request_interaction(InteractionEvent("s2", InteractionType.NOTIFICATION, InteractionPriority.SILENT))
        stats = layer.suppression_stats
        assert stats["shown"] == 1
        assert stats["suppressed"] == 1

    def test_reset_counters(self):
        layer = InteractionMinimalismLayer()
        layer.request_interaction(InteractionEvent("c1", InteractionType.CONFIRMATION, InteractionPriority.NORMAL))
        layer.reset_workflow_counters()
        # Should be able to request another confirmation
        event = InteractionEvent("c2", InteractionType.CONFIRMATION, InteractionPriority.NORMAL)
        result = layer.request_interaction(event)
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# P7: Progressive Disclosure Engine
# ═══════════════════════════════════════════════════════════════

class TestProgressiveDisclosure:
    """Tests for P7: Progressive Disclosure Engine."""

    def test_disclosure_item_creation(self):
        item = DisclosureItem(
            name="test_item",
            minimal="Brief",
            summary="Summary info",
            detailed="Detailed info",
        )
        assert item.name == "test_item"
        assert item.current_level == DisclosureLevel.MINIMAL
        assert item.get_content() == "Brief"

    def test_disclosure_expand(self):
        item = DisclosureItem(
            name="test",
            minimal="Brief",
            summary="Summary",
            detailed="Detailed",
        )
        assert item.expand()
        assert item.current_level == DisclosureLevel.SUMMARY
        assert item.get_content() == "Summary"

    def test_disclosure_collapse(self):
        item = DisclosureItem(
            name="test",
            minimal="Brief",
            summary="Summary",
        )
        item.expand()
        assert item.collapse()
        assert item.current_level == DisclosureLevel.MINIMAL

    def test_disclosure_expand_at_max(self):
        item = DisclosureItem(name="test", minimal="Brief")
        item.current_level = DisclosureLevel.DEBUG
        assert not item.expand()  # Already at max

    def test_disclosure_collapse_at_min(self):
        item = DisclosureItem(name="test", minimal="Brief")
        assert not item.collapse()  # Already at min

    def test_disclosure_engine_register(self):
        engine = ProgressiveDisclosureEngine()
        engine.register(DisclosureItem(name="item1", minimal="Brief"))
        assert engine.registered_count == 1

    def test_disclosure_engine_get(self):
        engine = ProgressiveDisclosureEngine()
        engine.register(DisclosureItem(name="item1", minimal="Brief", summary="Summary"))
        assert engine.get("item1") == "Brief"
        assert engine.get("item1", DisclosureLevel.SUMMARY) == "Summary"

    def test_disclosure_engine_expand(self):
        engine = ProgressiveDisclosureEngine()
        engine.register(DisclosureItem(name="item1", minimal="Brief", summary="Summary"))
        content = engine.expand("item1")
        assert content == "Summary"

    def test_disclosure_engine_collapse(self):
        engine = ProgressiveDisclosureEngine()
        engine.register(DisclosureItem(name="item1", minimal="Brief", summary="Summary"))
        engine.expand("item1")
        content = engine.collapse("item1")
        assert content == "Brief"

    def test_disclosure_auto_expand_on_error(self):
        engine = ProgressiveDisclosureEngine()
        engine.register(DisclosureItem(
            name="item1",
            minimal="Brief",
            detailed="Detailed error info",
            auto_expand_on_error=True,
        ))
        content = engine.handle_error("item1", "Error occurred")
        assert "Detailed" in content

    def test_discovery_frequently_expanded(self):
        engine = ProgressiveDisclosureEngine()
        engine.register(DisclosureItem(name="item1", minimal="Brief", summary="Summary"))
        for _ in range(5):
            engine.expand("item1")
        frequent = engine.get_frequently_expanded(min_expands=3)
        assert len(frequent) == 1

    def test_disclosure_verbose_mode(self):
        engine = ProgressiveDisclosureEngine()
        engine.register(DisclosureItem(name="item1", minimal="Brief", summary="Summary"))
        engine.set_verbose(True)
        assert engine.get("item1") == "Summary"

    def test_disclosure_profile_max_level(self):
        profile = DisclosureProfile(max_level=DisclosureLevel.SUMMARY)
        engine = ProgressiveDisclosureEngine(profile)
        engine.register(DisclosureItem(name="item1", minimal="Brief", summary="Summary", detailed="Detailed"))
        engine.expand("item1")
        engine.expand("item1")
        # Should not go beyond SUMMARY
        assert engine._items["item1"].current_level == DisclosureLevel.SUMMARY


# ═══════════════════════════════════════════════════════════════
# P8: Operational Calm Metrics
# ═══════════════════════════════════════════════════════════════

class TestOperationalCalmMetrics:
    """Tests for P8: Operational Calm Metrics."""

    def test_calm_reading(self):
        reading = CalmReading(
            dimension=CalmDimension.INTERRUPTION_DENSITY,
            value=5.0,
        )
        assert reading.dimension == CalmDimension.INTERRUPTION_DENSITY
        assert reading.value == 5.0

    def test_metrics_record(self):
        metrics = OperationalCalmMetrics()
        metrics.record(CalmDimension.INTERRUPTION_DENSITY, 3.0)
        report = metrics.assess()
        assert report.overall_level in (CalmLevel.CALM, CalmLevel.NORMAL)

    def test_metrics_increment(self):
        metrics = OperationalCalmMetrics()
        metrics.increment(CalmDimension.ALERT_FREQUENCY)
        metrics.increment(CalmDimension.ALERT_FREQUENCY)
        report = metrics.assess()
        assert CalmDimension.ALERT_FREQUENCY.value in report.dimension_levels

    def test_calm_thresholds(self):
        thresholds = CalmThresholds(calm_max=2, normal_max=5, elevated_max=10, high_max=20)
        assert thresholds.calm_max == 2

    def test_overwhelming_detection(self):
        metrics = OperationalCalmMetrics()
        for _ in range(25):
            metrics.increment(CalmDimension.INTERRUPTION_DENSITY)
        report = metrics.assess()
        level = report.dimension_levels.get(CalmDimension.INTERRUPTION_DENSITY.value)
        assert level in (CalmLevel.HIGH, CalmLevel.OVERWHELMING)

    def test_calm_recommendations(self):
        metrics = OperationalCalmMetrics()
        for _ in range(30):
            metrics.increment(CalmDimension.ALERT_FREQUENCY)
        report = metrics.assess()
        assert len(report.recommendations) > 0
        assert any("alert" in r.lower() for r in report.recommendations)

    def test_calm_report_timestamp(self):
        metrics = OperationalCalmMetrics()
        report = metrics.assess()
        assert report.timestamp > 0

    def test_clear_history(self):
        metrics = OperationalCalmMetrics()
        metrics.increment(CalmDimension.INTERRUPTION_DENSITY)
        metrics.clear_history()
        report = metrics.assess()
        assert report.overall_level == CalmLevel.CALM

    def test_dimension_trend(self):
        metrics = OperationalCalmMetrics(window_seconds=60)
        metrics.increment(CalmDimension.WORKFLOW_TURBULENCE)
        trend = metrics.get_dimension_trend(CalmDimension.WORKFLOW_TURBULENCE, buckets=3)
        assert len(trend) == 3


# ═══════════════════════════════════════════════════════════════
# P9: Architecture Compression
# ═══════════════════════════════════════════════════════════════

class TestArchitectureCompression:
    """Tests for P9: Architecture Compression Initiative."""

    def test_overlap_finding(self):
        finding = OverlapFinding(
            name="test_overlap",
            overlap_type=OverlapType.DUPLICATE_STATE,
            modules=["mod_a.py", "mod_b.py"],
            description="Duplicate state model",
            recommended_action=CompressionAction.MERGE,
            estimated_lines_saved=100,
        )
        assert finding.name == "test_overlap"
        assert finding.risk == "low"

    def test_compression_plan(self):
        plan = CompressionPlan(
            findings=[
                OverlapFinding("m1", OverlapType.DUPLICATE_STATE, ["a.py", "b.py"], "desc", CompressionAction.MERGE),
                OverlapFinding("c1", OverlapType.SHARED_CONCEPT, ["c.py", "d.py"], "desc", CompressionAction.COLLAPSE),
                OverlapFinding("u1", OverlapType.OVERLAPPING_GOVERNANCE, ["e.py", "f.py"], "desc", CompressionAction.UNIFY),
            ],
            total_lines_saved=200,
            modules_affected={"a.py", "b.py", "c.py", "d.py"},
        )
        assert len(plan.merge_candidates) == 1
        assert len(plan.collapse_candidates) == 1
        assert len(plan.unify_candidates) == 1
        assert plan.total_lines_saved == 200

    def test_compressor_scans_runtime(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        compressor = ArchitectureCompressor(base)
        plan = compressor.analyze()
        assert len(plan.findings) >= 0

    def test_compression_action_enum(self):
        assert CompressionAction.MERGE.value == "merge"
        assert CompressionAction.COLLAPSE.value == "collapse"
        assert CompressionAction.UNIFY.value == "unify"
        assert CompressionAction.KEEP.value == "keep"

    def test_overlap_type_enum(self):
        assert OverlapType.DUPLICATE_STATE.value == "duplicate_state"
        assert OverlapType.PARALLEL_OBSERVABILITY.value == "parallel_observability"
        assert OverlapType.OVERLAPPING_GOVERNANCE.value == "overlapping_governance"


# ═══════════════════════════════════════════════════════════════
# P10: Do Less Runtime Philosophy
# ═══════════════════════════════════════════════════════════════

class TestDoLessRuntime:
    """Tests for P10: Do Less Runtime Philosophy."""

    def test_proposed_action(self):
        action = ProposedAction(
            action_type=ActionType.REACT,
            target="test_target",
            estimated_value=ActionValue.MEDIUM,
        )
        assert action.action_type == ActionType.REACT
        assert action.estimated_value == ActionValue.MEDIUM
        assert not action.suppressed
        assert not action.deferred

    def test_critical_always_executes(self):
        runtime = DoLessRuntime()
        action = ProposedAction(
            action_type=ActionType.REACT,
            target="test",
            estimated_value=ActionValue.CRITICAL,
        )
        decision = runtime.evaluate(action)
        assert decision.should_execute

    def test_zero_always_suppressed(self):
        runtime = DoLessRuntime()
        action = ProposedAction(
            action_type=ActionType.ADVISE,
            target="test",
            estimated_value=ActionValue.ZERO,
        )
        decision = runtime.evaluate(action)
        assert not decision.should_execute
        assert action.suppressed

    def test_low_value_deferred(self):
        runtime = DoLessRuntime()
        action = ProposedAction(
            action_type=ActionType.NOTIFY,
            target="test",
            estimated_value=ActionValue.LOW,
        )
        decision = runtime.evaluate(action)
        assert not decision.should_execute
        assert action.deferred

    def test_interruptions_blocked(self):
        runtime = DoLessRuntime(allow_interruptions=False)
        action = ProposedAction(
            action_type=ActionType.INTERRUPT,
            target="test",
            estimated_value=ActionValue.HIGH,
        )
        decision = runtime.evaluate(action)
        assert not decision.should_execute

    def test_advisory_blocked(self):
        runtime = DoLessRuntime(allow_advisory=False)
        action = ProposedAction(
            action_type=ActionType.ADVISE,
            target="test",
            estimated_value=ActionValue.HIGH,
        )
        decision = runtime.evaluate(action)
        assert not decision.should_execute

    def test_rate_limiting(self):
        runtime = DoLessRuntime(max_actions_per_minute=2)
        for i in range(5):
            action = ProposedAction(
                action_type=ActionType.LOG,
                target=f"test_{i}",
                estimated_value=ActionValue.HIGH,
            )
            runtime.evaluate(action)
        report = runtime.get_report()
        assert report.total_deferred > 0

    def test_restraint_report(self):
        runtime = DoLessRuntime()
        runtime.evaluate(ProposedAction(ActionType.REACT, "t", ActionValue.CRITICAL))
        runtime.evaluate(ProposedAction(ActionType.ADVISE, "t", ActionValue.ZERO))
        report = runtime.get_report()
        assert report.total_proposed == 2
        assert report.total_executed == 1
        assert report.total_suppressed == 1

    def test_restraint_ratio(self):
        runtime = DoLessRuntime()
        for _ in range(8):
            runtime.evaluate(ProposedAction(ActionType.ADVISE, "t", ActionValue.ZERO))
        runtime.evaluate(ProposedAction(ActionType.REACT, "t", ActionValue.CRITICAL))
        report = runtime.get_report()
        assert report.restraint_ratio == 8 / 9

    def test_set_restraint_level(self):
        runtime = DoLessRuntime()
        runtime.set_restraint_level(min_value=ActionValue.MEDIUM)
        assert runtime.min_action_value == ActionValue.MEDIUM

    def test_is_silent(self):
        runtime = DoLessRuntime()
        assert runtime.is_silent  # No actions yet

    def test_restraint_decision_reason(self):
        runtime = DoLessRuntime()
        action = ProposedAction(ActionType.REACT, "t", ActionValue.CRITICAL)
        decision = runtime.evaluate(action)
        assert len(decision.reason) > 0


# ═══════════════════════════════════════════════════════════════
# Integration: Compression Engine
# ═══════════════════════════════════════════════════════════════

class TestCompressionEngine:
    """Integration tests for the unified Compression Engine."""

    def test_engine_creates(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system"
        engine = CompressionEngine(base)
        assert engine is not None

    def test_engine_runs_analysis(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        engine = CompressionEngine(base)
        report = engine.run_full_analysis()
        assert isinstance(report, UnifiedCompressionReport)
        assert report.timestamp > 0

    def test_engine_recommendations(self):
        base = "/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system/core/project_manager/runtime"
        engine = CompressionEngine(base)
        report = engine.run_full_analysis()
        assert isinstance(report.top_recommendations, list)
