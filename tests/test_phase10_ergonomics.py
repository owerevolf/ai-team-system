"""
Tests for Phase 10 — Operational Ergonomics & Human Scaling.

Covers all 7 ergonomics modules:
  P1: Workflow Compression
  P2: Attention Management
  P3: Approval Intelligence
  P4: Noise Reduction
  P5: Calm Mode
  P6: Intent-Centric UX
  P7: Human Time Protection
"""

import time
import pytest

from core.project_manager.runtime.ergonomics.workflow_compression import (
    WorkflowCompressor, CompressionLevel, CompressedStep, CompressedView,
)
from core.project_manager.runtime.ergonomics.attention_management import (
    AttentionManager, AttentionItem, AttentionCategory, AttentionPriority,
    AttentionSnapshot,
)
from core.project_manager.runtime.ergonomics.approval_intelligence import (
    ApprovalIntelligence, ApprovalItem, ApprovalBatch, ApprovalRisk,
    ApprovalStatus,
)
from core.project_manager.runtime.ergonomics.noise_reduction import (
    NoiseReducer, NoiseEvent, NoiseType, NoiseReport,
)
from core.project_manager.runtime.ergonomics.calm_mode import (
    CalmMode, CalmLevel, CalmPolicy,
)
from core.project_manager.runtime.ergonomics.intent_centric_ux import (
    IntentCentricUX, Intent, IntentAction, UserIntent, IntentConfidence,
)
from core.project_manager.runtime.ergonomics.human_time_protection import (
    HumanTimeProtection, Interruption, InterruptionType, InterruptionUrgency,
    FocusBlock, InterruptionBatch,
)


# ═══════════════════════════════════════════════════════════════
# P1 — Workflow Compression
# ═══════════════════════════════════════════════════════════════

class TestWorkflowCompression:
    def _make_raw_steps(self, count=10):
        steps = []
        for i in range(count):
            steps.append({
                "id": f"step-{i}",
                "type": "validation" if i < 7 else "file_create",
                "label": f"Step {i}",
                "status": "done",
                "timestamp": 1000.0 + i,
                "duration_ms": 10.0,
                "summary": f"Step {i} done",
            })
        return steps

    def test_compress_standard_groups_similar(self):
        compressor = WorkflowCompressor(CompressionLevel.STANDARD)
        steps = self._make_raw_steps(10)
        view = compressor.compress(steps, workflow_id="wf-1", workflow_type="test")
        # 7 validation steps should be grouped, 3 file_create separate
        assert view.workflow_id == "wf-1"
        assert view.total_raw_steps == 10
        assert view.status == "done"
        # Should have fewer compressed steps than raw
        assert len(view.steps) < 10

    def test_compress_minimal_shows_only_active(self):
        compressor = WorkflowCompressor(CompressionLevel.MINIMAL)
        steps = self._make_raw_steps(5)
        view = compressor.compress(steps, workflow_id="wf-2")
        # Minimal: only shows last done step
        assert len(view.steps) <= 1

    def test_compress_detailed_shows_all(self):
        compressor = WorkflowCompressor(CompressionLevel.DETAILED)
        steps = self._make_raw_steps(5)
        view = compressor.compress(steps, workflow_id="wf-3")
        assert len(view.steps) == 5

    def test_compress_empty_steps(self):
        compressor = WorkflowCompressor(CompressionLevel.STANDARD)
        view = compressor.compress([], workflow_id="wf-empty")
        assert view.status == "empty"
        assert len(view.steps) == 0

    def test_compress_failed_status(self):
        compressor = WorkflowCompressor(CompressionLevel.STANDARD)
        steps = self._make_raw_steps(5)
        steps[2]["status"] = "failed"
        steps[2]["error"] = "Something broke"
        view = compressor.compress(steps, workflow_id="wf-fail")
        assert view.status == "failed"
        assert len(view.errors) == 1

    def test_compress_running_status(self):
        compressor = WorkflowCompressor(CompressionLevel.STANDARD)
        steps = self._make_raw_steps(5)
        steps[4]["status"] = "running"
        steps[4]["type"] = "file_create"  # Prominent type so not grouped away
        view = compressor.compress(steps, workflow_id="wf-run")
        assert view.status == "running"

    def test_compression_ratio(self):
        compressor = WorkflowCompressor(CompressionLevel.STANDARD)
        steps = self._make_raw_steps(20)
        view = compressor.compress(steps, workflow_id="wf-ratio")
        assert 0 < view.compression_ratio < 1.0

    def test_compressed_step_to_dict(self):
        step = CompressedStep(step_id="s1", label="Test", status="done", detail_count=5)
        d = step.to_dict()
        assert d["step_id"] == "s1"
        assert d["detail_count"] == 5

    def test_compressed_view_to_dict(self):
        view = CompressedView(
            workflow_id="wf-dict",
            workflow_type="test",
            status="done",
            started_at=1000.0,
            ended_at=1005.0,
        )
        d = view.to_dict()
        assert d["workflow_id"] == "wf-dict"
        assert d["duration_ms"] == 5000.0

    def test_outcome_messages(self):
        compressor = WorkflowCompressor(CompressionLevel.STANDARD)
        steps = self._make_raw_steps(3)
        view = compressor.compress(steps, workflow_id="wf-outcome")
        assert "completed successfully" in view.outcome


# ═══════════════════════════════════════════════════════════════
# P2 — Attention Management
# ═══════════════════════════════════════════════════════════════

class TestAttentionManagement:
    def test_add_and_get_snapshot(self):
        manager = AttentionManager()
        manager.add(AttentionItem(
            item_id="item-1",
            category=AttentionCategory.ERROR,
            priority=AttentionPriority.HIGH,
            message="Something failed",
        ))
        snapshot = manager.get_snapshot()
        assert len(snapshot.items) == 1
        assert snapshot.high_count == 1

    def test_dismiss_item(self):
        manager = AttentionManager()
        manager.add(AttentionItem(
            item_id="item-1",
            category=AttentionCategory.INFO,
            priority=AttentionPriority.NORMAL,
            message="Info message",
        ))
        assert manager.dismiss("item-1") is True
        snapshot = manager.get_snapshot()
        assert len(snapshot.items) == 0

    def test_dismiss_group(self):
        manager = AttentionManager()
        for i in range(5):
            manager.add(AttentionItem(
                item_id=f"item-{i}",
                category=AttentionCategory.WARNING,
                priority=AttentionPriority.NORMAL,
                message=f"Warning {i}",
                group_key="warnings",
            ))
        count = manager.dismiss_group("warnings")
        assert count == 5
        snapshot = manager.get_snapshot()
        assert len(snapshot.items) == 0

    def test_priority_sorting(self):
        manager = AttentionManager()
        manager.add(AttentionItem(
            item_id="low",
            category=AttentionCategory.INFO,
            priority=AttentionPriority.LOW,
            message="Low priority",
        ))
        manager.add(AttentionItem(
            item_id="critical",
            category=AttentionCategory.ERROR,
            priority=AttentionPriority.CRITICAL,
            message="Critical!",
        ))
        snapshot = manager.get_snapshot()
        assert snapshot.items[0].priority == AttentionPriority.CRITICAL
        assert snapshot.critical_count == 1

    def test_get_critical(self):
        manager = AttentionManager()
        manager.add(AttentionItem(
            item_id="crit-1",
            category=AttentionCategory.ERROR,
            priority=AttentionPriority.CRITICAL,
            message="Critical error",
        ))
        manager.add(AttentionItem(
            item_id="norm-1",
            category=AttentionCategory.INFO,
            priority=AttentionPriority.NORMAL,
            message="Normal info",
        ))
        critical = manager.get_critical()
        assert len(critical) == 1
        assert critical[0].item_id == "crit-1"

    def test_get_actionable(self):
        manager = AttentionManager()
        manager.add(AttentionItem(
            item_id="act-1",
            category=AttentionCategory.APPROVAL,
            priority=AttentionPriority.HIGH,
            message="Needs approval",
            actionable=True,
            action_label="Approve",
        ))
        manager.add(AttentionItem(
            item_id="info-1",
            category=AttentionCategory.INFO,
            priority=AttentionPriority.NORMAL,
            message="Just info",
        ))
        actionable = manager.get_actionable()
        assert len(actionable) == 1

    def test_clear_dismissed(self):
        manager = AttentionManager()
        for i in range(5):
            manager.add(AttentionItem(
                item_id=f"item-{i}",
                category=AttentionCategory.INFO,
                priority=AttentionPriority.NORMAL,
                message=f"Info {i}",
            ))
        for i in range(3):
            manager.dismiss(f"item-{i}")
        removed = manager.clear_dismissed()
        assert removed == 3

    def test_max_items_limit(self):
        manager = AttentionManager(max_items=5)
        for i in range(10):
            manager.add(AttentionItem(
                item_id=f"item-{i}",
                category=AttentionCategory.INFO,
                priority=AttentionPriority.LOW,
                message=f"Info {i}",
            ))
        assert len(manager._items) <= 5

    def test_stats(self):
        manager = AttentionManager()
        manager.add(AttentionItem(
            item_id="s1",
            category=AttentionCategory.ERROR,
            priority=AttentionPriority.CRITICAL,
            message="Error",
            actionable=True,
        ))
        stats = manager.get_stats()
        assert stats["total"] == 1
        assert stats["actionable"] == 1
        assert "CRITICAL" in stats["by_priority"]

    def test_snapshot_to_dict(self):
        manager = AttentionManager()
        manager.add(AttentionItem(
            item_id="d1",
            category=AttentionCategory.INFO,
            priority=AttentionPriority.NORMAL,
            message="Test",
        ))
        snapshot = manager.get_snapshot()
        d = snapshot.to_dict()
        assert "items" in d
        assert "critical_count" in d


# ═══════════════════════════════════════════════════════════════
# P3 — Approval Intelligence
# ═══════════════════════════════════════════════════════════════

class TestApprovalIntelligence:
    def test_add_and_get_pending(self):
        ai = ApprovalIntelligence()
        ai.add(ApprovalItem(
            title="Add requests dep",
            risk=ApprovalRisk.LOW,
            category="deps",
        ))
        pending = ai.get_pending()
        assert len(pending) == 1

    def test_decide_approval(self):
        ai = ApprovalIntelligence()
        aid = ai.add(ApprovalItem(
            title="Test approval",
            risk=ApprovalRisk.MEDIUM,
        ))
        assert ai.decide(aid, True) is True
        item = ai._items[aid]
        assert item.status == ApprovalStatus.APPROVED

    def test_auto_decide_low_risk(self):
        ai = ApprovalIntelligence()
        aid = ai.add(ApprovalItem(
            title="Low risk item",
            risk=ApprovalRisk.LOW,
        ))
        assert ai.auto_decide(aid) is True
        assert ai._items[aid].status == ApprovalStatus.AUTO_APPLIED

    def test_auto_decide_skips_high_risk(self):
        ai = ApprovalIntelligence()
        aid = ai.add(ApprovalItem(
            title="High risk item",
            risk=ApprovalRisk.HIGH,
        ))
        assert ai.auto_decide(aid) is False
        assert ai._items[aid].status == ApprovalStatus.PENDING

    def test_create_batches_groups_by_category(self):
        ai = ApprovalIntelligence()
        ai.add(ApprovalItem(title="Dep 1", risk=ApprovalRisk.MEDIUM, category="deps"))
        ai.add(ApprovalItem(title="Dep 2", risk=ApprovalRisk.MEDIUM, category="deps"))
        ai.add(ApprovalItem(title="Config 1", risk=ApprovalRisk.HIGH, category="config"))
        batches = ai.create_batches()
        # Should have at least 2 batches (deps, config)
        assert len(batches) >= 2

    def test_approve_batch(self):
        ai = ApprovalIntelligence()
        ai.add(ApprovalItem(title="Item 1", risk=ApprovalRisk.HIGH, category="test"))
        ai.add(ApprovalItem(title="Item 2", risk=ApprovalRisk.HIGH, category="test"))
        batches = ai.create_batches()
        assert len(batches) >= 1
        count = ai.approve_batch(batches[0].batch_id)
        assert count >= 1

    def test_reject_batch(self):
        ai = ApprovalIntelligence()
        ai.add(ApprovalItem(title="Item 1", risk=ApprovalRisk.HIGH, category="test"))
        batches = ai.create_batches()
        assert len(batches) >= 1
        count = ai.reject_batch(batches[0].batch_id)
        assert count >= 1

    def test_approval_surface(self):
        ai = ApprovalIntelligence()
        ai.add(ApprovalItem(title="Critical change", risk=ApprovalRisk.CRITICAL, category="security"))
        surface = ai.get_approval_surface()
        assert surface["has_critical"] is True
        assert surface["needs_attention"] is True

    def test_approval_surface_no_critical(self):
        ai = ApprovalIntelligence()
        ai.add(ApprovalItem(title="Low change", risk=ApprovalRisk.LOW, category="deps"))
        surface = ai.get_approval_surface()
        assert surface["has_critical"] is False

    def test_stats(self):
        ai = ApprovalIntelligence()
        ai.add(ApprovalItem(title="S1", risk=ApprovalRisk.LOW))
        ai.add(ApprovalItem(title="S2", risk=ApprovalRisk.HIGH))
        stats = ai.get_stats()
        assert stats["total"] == 2
        assert "by_status" in stats
        assert "by_risk" in stats

    def test_batch_to_dict(self):
        batch = ApprovalBatch(
            batch_id="b1",
            title="Test batch",
            items=[
                ApprovalItem(title="I1", risk=ApprovalRisk.MEDIUM),
                ApprovalItem(title="I2", risk=ApprovalRisk.LOW),
            ],
        )
        d = batch.to_dict()
        assert d["batch_id"] == "b1"
        assert d["item_count"] == 2

    def test_approval_item_to_dict(self):
        item = ApprovalItem(title="Test", risk=ApprovalRisk.HIGH)
        d = item.to_dict()
        assert d["title"] == "Test"
        assert d["risk"] == "high"


# ═══════════════════════════════════════════════════════════════
# P4 — Noise Reduction
# ═══════════════════════════════════════════════════════════════

class TestNoiseReduction:
    def test_new_event_passes_through(self):
        reducer = NoiseReducer()
        result = reducer.process("test", "New unique message")
        assert result == "New unique message"

    def test_duplicate_suppressed(self):
        reducer = NoiseReducer(max_repeats_before_suppress=2)
        reducer.process("test", "Repeated message")
        reducer.process("test", "Repeated message")
        result = reducer.process("test", "Repeated message")
        assert result is None  # Suppressed

    def test_different_events_pass_through(self):
        reducer = NoiseReducer()
        r1 = reducer.process("test", "Message A")
        r2 = reducer.process("test", "Message B")
        assert r1 == "Message A"
        assert r2 == "Message B"

    def test_process_explanation(self):
        reducer = NoiseReducer()
        exp = {"action_type": "file_modify", "why": "Fix import"}
        result = reducer.process_explanation(exp)
        assert result is not None

    def test_process_explanation_redundant(self):
        reducer = NoiseReducer(max_repeats_before_suppress=1)
        exp = {"action_type": "file_modify", "why": "Fix import"}
        reducer.process_explanation(exp)
        result = reducer.process_explanation(exp)
        assert result is None

    def test_process_telemetry(self):
        reducer = NoiseReducer()
        tel = {"metric": "cpu", "value": 42}
        result = reducer.process_telemetry(tel)
        assert result is not None

    def test_cleanup_stale(self):
        reducer = NoiseReducer(stale_threshold_seconds=0)
        reducer.process("test", "Old message")
        time.sleep(0.01)
        removed = reducer.cleanup_stale()
        assert removed == 1

    def test_get_report(self):
        reducer = NoiseReducer()
        for i in range(5):
            reducer.process("test", f"Message {i % 2}")  # Some duplicates
        report = reducer.get_report()
        assert report.total_events == 5
        assert "by_type" in report.to_dict()

    def test_get_stats(self):
        reducer = NoiseReducer()
        reducer.process("test", "Message 1")
        reducer.process("test", "Message 1")  # Duplicate
        stats = reducer.get_stats()
        assert stats["total_processed"] == 2
        assert stats["suppression_rate"] > 0

    def test_max_fingerprints_limit(self):
        reducer = NoiseReducer(max_fingerprints=3)
        for i in range(10):
            reducer.process("test", f"Unique message {i}")
        assert len(reducer._fingerprints) <= 3

    def test_noise_event_to_dict(self):
        event = NoiseEvent(
            noise_id="n1",
            noise_type=NoiseType.REPEATED_LOG,
            source="test",
            message="Repeated",
            fingerprint="abc123",
        )
        d = event.to_dict()
        assert d["noise_id"] == "n1"
        assert d["noise_type"] == "repeated_log"


# ═══════════════════════════════════════════════════════════════
# P5 — Calm Mode
# ═══════════════════════════════════════════════════════════════

class TestCalmMode:
    def test_full_level_shows_everything(self):
        calm = CalmMode(CalmLevel.FULL)
        assert calm.should_show("traces") is True
        assert calm.should_show("debug") is True
        assert calm.should_show("telemetry") is True

    def test_calm_level_hides_noise(self):
        calm = CalmMode(CalmLevel.CALM)
        assert calm.should_show("errors") is True
        assert calm.should_show("progress") is True
        assert calm.should_show("traces") is False
        assert calm.should_show("telemetry") is False
        assert calm.should_show("debug") is False

    def test_silent_level_only_errors(self):
        calm = CalmMode(CalmLevel.SILENT)
        assert calm.should_show("errors") is True
        assert calm.should_show("progress") is False
        assert calm.should_show("approvals") is False

    def test_set_level(self):
        calm = CalmMode(CalmLevel.FULL)
        calm.set_level(CalmLevel.CALM)
        assert calm.level == CalmLevel.CALM
        assert calm.should_show("traces") is False

    def test_filter_events_calm(self):
        calm = CalmMode(CalmLevel.CALM)
        events = [
            {"type": "error", "message": "Error!"},
            {"type": "progress", "message": "50% done"},
            {"type": "trace", "message": "Debug trace"},
            {"type": "telemetry", "metric": "cpu"},
        ]
        filtered = calm.filter_events(events)
        types = {e["type"] for e in filtered}
        assert "error" in types
        assert "progress" in types
        assert "trace" not in types
        assert "telemetry" not in types

    def test_filter_events_full(self):
        calm = CalmMode(CalmLevel.FULL)
        events = [
            {"type": "error", "message": "Error!"},
            {"type": "trace", "message": "Trace"},
        ]
        filtered = calm.filter_events(events)
        assert len(filtered) == 2

    def test_filter_explanations_calm(self):
        calm = CalmMode(CalmLevel.CALM)
        explanations = [
            {"action_type": "file_modify", "why": "Fix", "confidence": 0.9},
            {"action_type": "error", "why": "Failed", "confidence": 0.3},
            {"action_type": "recovery", "why": "Recover", "confidence": 0.8},
        ]
        filtered = calm.filter_explanations(explanations)
        types = {e["action_type"] for e in filtered}
        assert "error" in types
        assert "recovery" in types
        assert "file_modify" not in types

    def test_max_detail_items(self):
        calm = CalmMode(CalmLevel.CALM)
        events = [{"type": "progress", "message": f"Step {i}"} for i in range(20)]
        filtered = calm.filter_events(events)
        assert len(filtered) <= calm._policy.max_detail_items

    def test_get_status(self):
        calm = CalmMode(CalmLevel.CALM)
        status = calm.get_status()
        assert status["level"] == "calm"
        assert "policy" in status

    def test_calm_policy_for_level(self):
        policy = CalmPolicy.for_level(CalmLevel.REDUCED)
        assert policy.show_traces is False
        assert policy.show_debug is False
        assert policy.show_errors is True

    def test_strip_event(self):
        calm = CalmMode(CalmLevel.CALM)
        event = {
            "type": "error",
            "message": "Error!",
            "details": "Stack trace...",
            "timestamp": 1234567890,
            "source": "module.py:42",
        }
        stripped = calm._strip_event(event)
        assert "type" in stripped
        assert "message" in stripped
        assert "timestamp" not in stripped  # Calm mode hides timestamps
        assert "source" not in stripped


# ═══════════════════════════════════════════════════════════════
# P6 — Intent-Centric UX
# ═══════════════════════════════════════════════════════════════

class TestIntentCentricUX:
    def test_detect_create_project_intent(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Create a new web project")
        assert intent.intent_type == UserIntent.CREATE_PROJECT

    def test_detect_fix_errors_intent(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Fix error in auth module")
        assert intent.intent_type == UserIntent.FIX_ERRORS

    def test_detect_add_feature_intent(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Add Stripe payments to my app")
        assert intent.intent_type == UserIntent.ADD_FEATURE

    def test_detect_refactor_intent(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Refactor the user service")
        assert intent.intent_type == UserIntent.REFACTOR

    def test_detect_unknown_intent(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Hello world")
        assert intent.intent_type == UserIntent.UNKNOWN
        assert intent.confidence == IntentConfidence.LOW

    def test_create_action_from_intent(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Create a new project")
        action = ux.create_action(intent)
        assert action is not None
        assert action.intent == UserIntent.CREATE_PROJECT
        assert action.requires_approval is False

    def test_create_action_modify_requires_approval(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Change the auth module")
        action = ux.create_action(intent)
        assert action is not None
        assert action.requires_approval is True

    def test_intent_menu(self):
        ux = IntentCentricUX()
        menu = ux.get_intent_menu()
        assert len(menu) > 0
        assert all("intent" in item and "label" in item for item in menu)

    def test_intent_to_dict(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Run tests")
        d = intent.to_dict()
        assert "intent_type" in d
        assert "confidence" in d

    def test_intent_action_to_dict(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Deploy to production")
        action = ux.create_action(intent)
        d = action.to_dict()
        assert "action_id" in d
        assert "runtime_operation" in d

    def test_extract_file_parameters(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Modify auth.py and models.py")
        assert "files" in intent.parameters

    def test_clarifying_questions_for_low_confidence(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Do something")
        if intent.confidence == IntentConfidence.LOW:
            assert len(intent.clarifying_questions) > 0

    def test_suggestions_for_intent(self):
        ux = IntentCentricUX()
        intent = ux.detect_intent("Add a new feature")
        assert len(intent.suggested_actions) > 0


# ═══════════════════════════════════════════════════════════════
# P7 — Human Time Protection
# ═══════════════════════════════════════════════════════════════

class TestHumanTimeProtection:
    def test_start_focus_block(self):
        htp = HumanTimeProtection()
        htp.start_focus_block("Coding")
        block = htp.get_active_focus_block()
        assert block is not None
        assert block.label == "Coding"
        assert block.is_active

    def test_end_focus_block(self):
        htp = HumanTimeProtection()
        block_id = htp.start_focus_block("Coding")
        ended = htp.end_focus_block(block_id)
        assert ended is not None
        assert ended.is_active is False
        assert htp.get_active_focus_block() is None

    def test_critical_interruption_always_delivered(self):
        htp = HumanTimeProtection()
        htp.start_focus_block("Coding")
        interruption = Interruption(
            interruption_id="crit-1",
            interruption_type=InterruptionType.ERROR,
            urgency=InterruptionUrgency.NOW,
            message="Critical error!",
        )
        assert htp.add_interruption(interruption) is True

    def test_non_critical_deferred_in_focus(self):
        htp = HumanTimeProtection()
        htp.start_focus_block("Coding")
        interruption = Interruption(
            interruption_id="info-1",
            interruption_type=InterruptionType.NOTIFICATION,
            urgency=InterruptionUrgency.BATCH,
            message="Build complete",
        )
        assert htp.add_interruption(interruption) is False
        assert htp._total_interruptions_prevented == 1

    def test_log_only_never_delivered(self):
        htp = HumanTimeProtection()
        interruption = Interruption(
            interruption_id="log-1",
            interruption_type=InterruptionType.PROGRESS,
            urgency=InterruptionUrgency.LOG_ONLY,
            message="Background task done",
        )
        assert htp.add_interruption(interruption) is False

    def test_get_ready_interruptions(self):
        htp = HumanTimeProtection()
        htp.add_interruption(Interruption(
            interruption_id="now-1",
            interruption_type=InterruptionType.ERROR,
            urgency=InterruptionUrgency.NOW,
            message="Error!",
        ))
        # NOW interruptions are delivered immediately by add_interruption
        # So pending count should be 0 (already delivered)
        assert htp.get_pending_count() == 0

    def test_create_batch(self):
        htp = HumanTimeProtection()
        htp.add_interruption(Interruption(
            interruption_id="b1",
            interruption_type=InterruptionType.NOTIFICATION,
            urgency=InterruptionUrgency.BATCH,
            message="Notification 1",
        ))
        batch = htp.create_batch()
        assert len(batch.interruptions) >= 1

    def test_deliver_batch(self):
        htp = HumanTimeProtection()
        htp.add_interruption(Interruption(
            interruption_id="d1",
            interruption_type=InterruptionType.NOTIFICATION,
            urgency=InterruptionUrgency.BATCH,
            message="Notification",
        ))
        batch = htp.create_batch()
        delivered = htp.deliver_batch(batch.batch_id)
        assert len(delivered) >= 1

    def test_pending_count(self):
        htp = HumanTimeProtection()
        htp.add_interruption(Interruption(
            interruption_id="p1",
            interruption_type=InterruptionType.NOTIFICATION,
            urgency=InterruptionUrgency.BATCH,
            message="Pending",
        ))
        assert htp.get_pending_count() == 1

    def test_stats(self):
        htp = HumanTimeProtection()
        htp.add_interruption(Interruption(
            interruption_id="s1",
            interruption_type=InterruptionType.ERROR,
            urgency=InterruptionUrgency.NOW,
            message="Error",
        ))
        stats = htp.get_stats()
        assert stats["total_interruptions"] >= 1
        assert "prevention_rate" in stats
        assert "active_focus_block" in stats

    def test_focus_block_duration(self):
        htp = HumanTimeProtection()
        block_id = htp.start_focus_block("Test")
        block = htp.get_active_focus_block()
        assert block.duration_seconds >= 0
        htp.end_focus_block(block_id)
        # After ending, get from history
        ended_block = htp._focus_blocks[0]
        assert ended_block.duration_seconds >= 0

    def test_interruption_to_dict(self):
        interruption = Interruption(
            interruption_id="t1",
            interruption_type=InterruptionType.ERROR,
            urgency=InterruptionUrgency.NOW,
            message="Test",
        )
        d = interruption.to_dict()
        assert d["interruption_id"] == "t1"
        assert d["urgency"] == "now"
