"""
Tests for Phase 11 — Adaptive Transparency & Trust Stability.

Covers all 10 trust modules:
  P1: Transparency Contracts
  P2: Visibility Guarantees
  P3: Runtime Adaptation Inspector
  P4: User-Controlled Adaptivity
  P5: Trust Drift Detection
  P6: Explainability Compression
  P7: Predictable Runtime Personality
  P8: Audit-Visible Automation
  P9: Governance Pressure Monitoring
  P10: Simplicity Preservation
"""

import time
import pytest

from core.project_manager.runtime.trust.transparency_contracts import (
    TransparencyContractManager, VisibilityAction, EventCategory,
    DEFAULT_TRANSPARENCY_CONTRACT,
)
from core.project_manager.runtime.trust.visibility_guarantees import (
    VisibilityGuaranteeEnforcer, GuaranteeType, GuaranteeLevel,
)
from core.project_manager.runtime.trust.adaptation_inspector import (
    RuntimeAdaptationInspector, AdaptationType, AdaptationReason,
)
from core.project_manager.runtime.trust.user_controlled_adaptivity import (
    UserControlledAdaptivity, AdaptivityProfile,
)
from core.project_manager.runtime.trust.trust_drift_detection import (
    TrustDriftDetector, TrustDriftType, TrustDriftSeverity, TrustDriftThreshold,
)
from core.project_manager.runtime.trust.explainability_compression import (
    ExplainabilityCompressor, ExplanationLevel,
)
from core.project_manager.runtime.trust.predictable_personality import (
    PredictableRuntimePersonality, SignalingStyle, AlertSemantics,
)
from core.project_manager.runtime.trust.audit_visible_automation import (
    AuditVisibleAutomation, AutomationType, AutomationStatus,
)
from core.project_manager.runtime.trust.governance_pressure import (
    GovernancePressureMonitor, PressureType, PressureLevel,
)
from core.project_manager.runtime.trust.simplicity_preservation import (
    SimplicityPreservation, ComplexityBudget, ComplexityTier,
)


# ═══════════════════════════════════════════════════════════════
# P1 — Transparency Contracts
# ═══════════════════════════════════════════════════════════════

class TestTransparencyContracts:
    def test_critical_error_always_show(self):
        mgr = TransparencyContractManager()
        action = mgr.resolve_action(EventCategory.CRITICAL_ERROR)
        assert action == VisibilityAction.SHOW

    def test_integrity_failure_never_hidden(self):
        mgr = TransparencyContractManager()
        assert mgr.can_hide(EventCategory.INTEGRITY_FAILURE) is False
        assert mgr.can_hide(EventCategory.INTEGRITY_FAILURE, calm_mode=True) is False

    def test_progress_can_suppress_in_calm(self):
        mgr = TransparencyContractManager()
        assert mgr.can_hide(EventCategory.PROGRESS_UPDATE, calm_mode=True) is True

    def test_progress_not_suppress_in_normal(self):
        mgr = TransparencyContractManager()
        # SUPPRESS items are only hidden in calm mode
        assert mgr.can_hide(EventCategory.PROGRESS_UPDATE, calm_mode=False) is False
        assert mgr.can_hide(EventCategory.PROGRESS_UPDATE, calm_mode=True) is True

    def test_security_never_summarized(self):
        mgr = TransparencyContractManager()
        assert mgr.can_summarize(EventCategory.SECURITY_IMPACT) is False

    def test_telemetry_can_summarize(self):
        mgr = TransparencyContractManager()
        assert mgr.can_summarize(EventCategory.REPETITIVE_TELEMETRY) is True

    def test_override_rule(self):
        mgr = TransparencyContractManager()
        assert mgr.override(EventCategory.PROGRESS_UPDATE, VisibilityAction.SHOW) is True
        action = mgr.resolve_action(EventCategory.PROGRESS_UPDATE)
        assert action == VisibilityAction.SHOW

    def test_override_non_overridable(self):
        mgr = TransparencyContractManager()
        # Make a rule non-overridable
        mgr._rules[EventCategory.CRITICAL_ERROR].user_overridable = False
        assert mgr.override(EventCategory.CRITICAL_ERROR, VisibilityAction.SUPPRESS) is False

    def test_record_violation(self):
        mgr = TransparencyContractManager()
        v = mgr.record_violation(
            EventCategory.CRITICAL_ERROR,
            VisibilityAction.SHOW,
            VisibilityAction.SUPPRESS,
            "evt-1"
        )
        assert v.category == EventCategory.CRITICAL_ERROR
        assert v.resolved is False

    def test_get_violations(self):
        mgr = TransparencyContractManager()
        mgr.record_violation(EventCategory.CRITICAL_ERROR, VisibilityAction.SHOW,
                             VisibilityAction.SUPPRESS, "evt-1")
        violations = mgr.get_violations()
        assert len(violations) == 1

    def test_never_hide_list(self):
        mgr = TransparencyContractManager()
        never_hide = mgr.get_never_hide_list()
        assert "critical_error" in never_hide
        assert "integrity_failure" in never_hide
        assert "progress_update" not in never_hide

    def test_contract_summary(self):
        mgr = TransparencyContractManager()
        summary = mgr.get_contract_summary()
        assert summary["total_rules"] > 0
        assert "by_action" in summary

    def test_custom_rules(self):
        custom = {EventCategory.PROGRESS_UPDATE: VisibilityAction.SHOW}
        mgr = TransparencyContractManager(custom_rules=custom)
        action = mgr.resolve_action(EventCategory.PROGRESS_UPDATE)
        assert action == VisibilityAction.SHOW


# ═══════════════════════════════════════════════════════════════
# P2 — Visibility Guarantees
# ═══════════════════════════════════════════════════════════════

class TestVisibilityGuarantees:
    def test_critical_failure_always_guaranteed(self):
        enforcer = VisibilityGuaranteeEnforcer()
        g = enforcer.get_guarantee(GuaranteeType.CRITICAL_FAILURE)
        assert g is not None
        assert g.level == GuaranteeLevel.ALWAYS
        assert g.suppressible is False

    def test_critical_failure_cannot_suppress(self):
        enforcer = VisibilityGuaranteeEnforcer()
        assert enforcer.can_suppress(GuaranteeType.CRITICAL_FAILURE) is False
        assert enforcer.can_suppress(GuaranteeType.CRITICAL_FAILURE, calm_mode=True) is False

    def test_security_boundary_never_suppressed(self):
        enforcer = VisibilityGuaranteeEnforcer()
        assert enforcer.can_suppress(GuaranteeType.SECURITY_BOUNDARY) is False

    def test_data_loss_risk_never_batched(self):
        enforcer = VisibilityGuaranteeEnforcer()
        assert enforcer.can_batch(GuaranteeType.DATA_LOSS_RISK) is False

    def test_validate_action_suppress_critical(self):
        enforcer = VisibilityGuaranteeEnforcer()
        allowed, reason = enforcer.validate_action(GuaranteeType.CRITICAL_FAILURE, "suppress")
        assert allowed is False
        assert "GUARANTEE VIOLATION" in reason

    def test_validate_action_ok_for_non_guaranteed(self):
        enforcer = VisibilityGuaranteeEnforcer()
        allowed, reason = enforcer.validate_action(GuaranteeType.CRITICAL_FAILURE, "show")
        assert allowed is True

    def test_always_visible_list(self):
        enforcer = VisibilityGuaranteeEnforcer()
        always = enforcer.get_always_visible()
        assert "critical_failure" in always
        assert "security_boundary" in always

    def test_guarantee_summary(self):
        enforcer = VisibilityGuaranteeEnforcer()
        summary = enforcer.get_guarantee_summary()
        assert summary["total_guarantees"] > 0
        assert "always_visible" in summary

    def test_custom_guarantees(self):
        from core.project_manager.runtime.trust.visibility_guarantees import VisibilityGuarantee
        custom = {
            GuaranteeType.CRITICAL_FAILURE: VisibilityGuarantee(
                guarantee_type=GuaranteeType.CRITICAL_FAILURE,
                level=GuaranteeLevel.ALWAYS,
                description="Custom",
                compressible=True,  # Override
            )
        }
        enforcer = VisibilityGuaranteeEnforcer(custom_guarantees=custom)
        assert enforcer.can_compress(GuaranteeType.CRITICAL_FAILURE) is True


# ═══════════════════════════════════════════════════════════════
# P3 — Runtime Adaptation Inspector
# ═══════════════════════════════════════════════════════════════

class TestRuntimeAdaptationInspector:
    def test_record_and_retrieve(self):
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                         event_id="evt-1", event_category="progress",
                         detail="Calm mode suppresses progress")
        decisions = inspector.get_decisions()
        assert len(decisions) == 1

    def test_why_hidden(self):
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                         event_id="evt-1", event_category="progress",
                         detail="Calm mode active")
        explanation = inspector.why_hidden("evt-1")
        assert explanation is not None
        assert "Calm mode" in explanation

    def test_why_surfaced(self):
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.SURFACED, AdaptationReason.VISIBILITY_GUARANTEE,
                         event_id="evt-2", event_category="error",
                         detail="Critical error guarantee")
        explanation = inspector.why_surfaced("evt-2")
        assert explanation is not None
        assert "Critical error" in explanation

    def test_why_delayed(self):
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.DELAYED, AdaptationReason.ATTENTION_PRIORITY,
                         event_id="evt-3", event_category="suggestion",
                         detail="Low priority, batched")
        explanation = inspector.why_delayed("evt-3")
        assert explanation is not None
        assert "batched" in explanation.lower() or "Low priority" in explanation

    def test_get_event_history(self):
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                         event_id="evt-1", detail="First")
        inspector.record(AdaptationType.SURFACED, AdaptationReason.VISIBILITY_GUARANTEE,
                         event_id="evt-1", detail="Then shown")
        history = inspector.get_event_history("evt-1")
        assert len(history) == 2

    def test_filter_by_type(self):
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                         event_id="e1", detail="Suppressed")
        inspector.record(AdaptationType.SURFACED, AdaptationReason.VISIBILITY_GUARANTEE,
                         event_id="e2", detail="Shown")
        suppressed = inspector.get_decisions(adaptation_type=AdaptationType.SUPPRESSED)
        assert len(suppressed) == 1

    def test_filter_by_reason(self):
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                         event_id="e1", detail="Calm")
        inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.NOISE_REDUCTION,
                         event_id="e2", detail="Noise")
        calm = inspector.get_decisions(reason=AdaptationReason.CALM_MODE)
        assert len(calm) == 1

    def test_stats(self):
        inspector = RuntimeAdaptationInspector()
        inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                         event_id="e1", detail="Test")
        stats = inspector.get_stats()
        assert stats["total_decisions"] == 1
        assert "suppressed" in stats["by_type"]

    def test_max_decisions_limit(self):
        inspector = RuntimeAdaptationInspector(max_decisions=3)
        for i in range(10):
            inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                             event_id=f"e{i}", detail=f"Test {i}")
        assert len(inspector._decisions) <= 3

    def test_explain_method(self):
        inspector = RuntimeAdaptationInspector()
        d = inspector.record(AdaptationType.SUPPRESSED, AdaptationReason.CALM_MODE,
                             event_id="e1", detail="Calm mode active")
        explanation = d.explain()
        assert "Hidden because" in explanation
        assert "Calm mode" in explanation


# ═══════════════════════════════════════════════════════════════
# P4 — User-Controlled Adaptivity
# ═══════════════════════════════════════════════════════════════

class TestUserControlledAdaptivity:
    def test_beginner_profile(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.BEGINNER)
        settings = ctrl.get_settings()
        assert settings.compression_level == "minimal"
        assert settings.calm_level == "reduced"
        assert settings.auto_apply_low_risk is False

    def test_focused_profile(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.FOCUSED)
        settings = ctrl.get_settings()
        assert settings.compression_level == "standard"
        assert settings.calm_level == "calm"
        assert settings.auto_apply_low_risk is True
        assert settings.focus_blocks_enabled is True

    def test_expert_profile(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.EXPERT)
        settings = ctrl.get_settings()
        assert settings.compression_level == "detailed"
        assert settings.calm_level == "full"
        assert settings.auto_apply_low_risk is False

    def test_recovery_profile(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.RECOVERY)
        settings = ctrl.get_settings()
        assert settings.compression_level == "detailed"
        assert settings.explanation_level == "full_trace"

    def test_set_profile(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.BEGINNER)
        ctrl.set_profile(AdaptivityProfile.EXPERT)
        assert ctrl.profile == AdaptivityProfile.EXPERT
        assert ctrl.get_settings().compression_level == "detailed"

    def test_customize_setting(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.BEGINNER)
        assert ctrl.customize("compression_level", "detailed") is True
        assert ctrl.get_settings().compression_level == "detailed"

    def test_customize_invalid_key(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.BEGINNER)
        assert ctrl.customize("nonexistent_key", "value") is False

    def test_reset_to_defaults(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.BEGINNER)
        ctrl.customize("compression_level", "detailed")
        ctrl.reset_to_profile_defaults()
        assert ctrl.get_settings().compression_level == "minimal"

    def test_get_customizations(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.BEGINNER)
        ctrl.customize("compression_level", "detailed")
        customizations = ctrl.get_customizations()
        assert "compression_level" in customizations

    def test_available_profiles(self):
        ctrl = UserControlledAdaptivity()
        profiles = ctrl.get_available_profiles()
        assert len(profiles) == 4

    def test_profile_description(self):
        ctrl = UserControlledAdaptivity()
        desc = ctrl.get_profile_description(AdaptivityProfile.BEGINNER)
        assert "visibility" in desc.lower() or "guided" in desc.lower()

    def test_status(self):
        ctrl = UserControlledAdaptivity(AdaptivityProfile.FOCUSED)
        status = ctrl.get_status()
        assert status["profile"] == "focused"
        assert "settings" in status
        assert "description" in status


# ═══════════════════════════════════════════════════════════════
# P5 — Trust Drift Detection
# ═══════════════════════════════════════════════════════════════

class TestTrustDriftDetection:
    def test_blind_approval_detection(self):
        detector = TrustDriftDetector()
        detector.record_approval(decision_time_seconds=0.5)
        events = detector.get_drift_events()
        assert len(events) == 1
        assert events[0].drift_type == TrustDriftType.BLIND_APPROVAL

    def test_normal_approval_no_drift(self):
        detector = TrustDriftDetector()
        detector.record_approval(decision_time_seconds=5.0)
        events = detector.get_drift_events()
        assert len(events) == 0

    def test_suppression_distrust(self):
        detector = TrustDriftDetector()
        for _ in range(10):
            detector.record_reveal_hidden()
        events = detector.get_drift_events()
        distrust = [e for e in events if e.drift_type == TrustDriftType.SUPPRESSION_DISTRUST]
        assert len(distrust) >= 1

    def test_explanation_rejection(self):
        detector = TrustDriftDetector()
        for _ in range(10):
            detector.record_explanation_skip()
        events = detector.get_drift_events()
        rejection = [e for e in events if e.drift_type == TrustDriftType.EXPLANATION_REJECTION]
        assert len(rejection) >= 1

    def test_recovery_avoidance(self):
        detector = TrustDriftDetector()
        for _ in range(10):
            detector.record_manual_fix()
        events = detector.get_drift_events()
        avoidance = [e for e in events if e.drift_type == TrustDriftType.RECOVERY_AVOIDANCE]
        assert len(avoidance) >= 1

    def test_manual_bypass_escalation(self):
        detector = TrustDriftDetector()
        for _ in range(6):
            detector.record_manual_bypass()
        events = detector.get_drift_events()
        bypass = [e for e in events if e.drift_type == TrustDriftType.MANUAL_BYPASS_ESCALATION]
        assert len(bypass) >= 1

    def test_governance_fatigue(self):
        detector = TrustDriftDetector()
        for _ in range(15):
            detector.record_approval(decision_time_seconds=0.5)
        events = detector.get_drift_events()
        fatigue = [e for e in events if e.drift_type == TrustDriftType.GOVERNANCE_FATIGUE]
        assert len(fatigue) >= 1

    def test_trust_summary(self):
        detector = TrustDriftDetector()
        detector.record_approval(decision_time_seconds=0.3)
        summary = detector.get_trust_summary()
        assert "trust_score" in summary
        assert "is_healthy" in summary
        assert summary["trust_score"] < 100

    def test_trust_score_decreases(self):
        detector = TrustDriftDetector()
        for _ in range(20):
            detector.record_approval(decision_time_seconds=0.3)
        summary = detector.get_trust_summary()
        assert summary["trust_score"] < 100  # Score should decrease from perfect

    def test_filter_by_severity(self):
        detector = TrustDriftDetector()
        detector.record_approval(decision_time_seconds=0.1)  # LOW
        detector.record_manual_fix()  # May trigger higher
        detector.record_manual_bypass()
        detector.record_manual_bypass()
        detector.record_manual_bypass()
        detector.record_manual_bypass()
        detector.record_manual_bypass()
        high = detector.get_drift_events(min_severity=TrustDriftSeverity.HIGH)
        all_events = detector.get_drift_events()
        assert len(high) <= len(all_events)

    def test_drift_event_to_dict(self):
        detector = TrustDriftDetector()
        detector.record_approval(decision_time_seconds=0.5)
        events = detector.get_drift_events()
        d = events[0].to_dict()
        assert "drift_type" in d
        assert "severity" in d


# ═══════════════════════════════════════════════════════════════
# P6 — Explainability Compression
# ═══════════════════════════════════════════════════════════════

class TestExplainabilityCompression:
    def test_create_explanation(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("file_modify", "mod-1",
                          summary="Fixed import",
                          reasoning="Import error at line 5",
                          full_trace="Full trace: scan found...")
        assert exp.summary == "Fixed import"
        assert exp.get_level() == ExplanationLevel.SUMMARY

    def test_expand(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S", reasoning="R", full_trace="F")
        assert exp.get_level() == ExplanationLevel.SUMMARY
        exp.expand()
        assert exp.get_level() == ExplanationLevel.REASONING
        exp.expand()
        assert exp.get_level() == ExplanationLevel.FULL_TRACE

    def test_expand_at_max(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S", reasoning="R", full_trace="F")
        exp.set_level(ExplanationLevel.FULL_TRACE)
        assert exp.expand() is False

    def test_collapse(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S", reasoning="R", full_trace="F")
        exp.set_level(ExplanationLevel.FULL_TRACE)
        exp.collapse()
        assert exp.get_level() == ExplanationLevel.REASONING
        exp.collapse()
        assert exp.get_level() == ExplanationLevel.SUMMARY

    def test_collapse_at_min(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S")
        assert exp.collapse() is False

    def test_set_level(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S", reasoning="R", full_trace="F")
        exp.set_level(ExplanationLevel.REASONING)
        assert exp.get_level() == ExplanationLevel.REASONING

    def test_get_current_content(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="Summary", reasoning="Reasoning", full_trace="Full")
        current = exp.get_current()
        assert current.content == "Summary"
        exp.expand()
        current = exp.get_current()
        assert current.content == "Reasoning"

    def test_to_dict(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S", reasoning="R", full_trace="F")
        d = exp.to_dict()
        assert "explanation_id" in d
        assert "can_expand" in d
        assert "can_collapse" in d
        assert d["can_expand"] is True
        assert d["can_collapse"] is False  # At SUMMARY level

    def test_to_full_dict(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S", reasoning="R", full_trace="F")
        d = exp.to_full_dict()
        assert d["summary"] == "S"
        assert d["reasoning"] == "R"
        assert d["full_trace"] == "F"

    def test_get_summary_view(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S", reasoning="R", full_trace="F")
        view = comp.get_summary_view(exp.explanation_id)
        assert view is not None
        assert view["content"] == "S"

    def test_get_full_view(self):
        comp = ExplainabilityCompressor()
        exp = comp.create("test", summary="S", reasoning="R", full_trace="F")
        view = comp.get_full_view(exp.explanation_id)
        assert view is not None
        assert "summary" in view
        assert "reasoning" in view
        assert "full_trace" in view

    def test_default_level(self):
        comp = ExplainabilityCompressor(default_level=ExplanationLevel.REASONING)
        exp = comp.create("test", summary="S", reasoning="R")
        assert exp.get_level() == ExplanationLevel.REASONING

    def test_stats(self):
        comp = ExplainabilityCompressor()
        comp.create("file_modify", summary="S")
        comp.create("file_create", summary="S")
        stats = comp.get_stats()
        assert stats["total_explanations"] == 2


# ═══════════════════════════════════════════════════════════════
# P7 — Predictable Runtime Personality
# ═══════════════════════════════════════════════════════════════

class TestPredictableRuntimePersonality:
    def test_initial_state(self):
        personality = PredictableRuntimePersonality()
        state = personality.get_current_state()
        assert "signaling_style" in state
        assert state["signaling_style"] == SignalingStyle.CONSISTENT.value

    def test_can_change_frequency(self):
        personality = PredictableRuntimePersonality()
        allowed, _ = personality.can_change("frequency", "high")
        assert allowed is True

    def test_record_change(self):
        personality = PredictableRuntimePersonality()
        change = personality.record_change("frequency", "normal", "high", "User request")
        assert change is not None
        assert change.aspect == "frequency"
        assert change.new_value == "high"

    def test_change_updates_state(self):
        personality = PredictableRuntimePersonality()
        personality.record_change("frequency", "normal", "high", "Test")
        assert personality.get_current_state()["frequency"] == "high"

    def test_style_change_too_frequent(self):
        personality = PredictableRuntimePersonality()
        personality.record_change("signaling_style", "consistent", "adaptive", "First")
        allowed, reason = personality.can_change("signaling_style", "escalating")
        assert allowed is False
        assert "too frequent" in reason.lower() or "Wait" in reason

    def test_fixed_alert_semantics(self):
        personality = PredictableRuntimePersonality()
        allowed, reason = personality.can_change("alert_semantics", "contextual")
        assert allowed is False
        assert "fixed" in reason.lower()

    def test_personality_status(self):
        personality = PredictableRuntimePersonality()
        status = personality.get_personality_status()
        assert "is_stable" in status
        assert status["is_stable"] is True

    def test_stability_score(self):
        personality = PredictableRuntimePersonality()
        score = personality.get_stability_score()
        assert score == 100.0  # No changes = perfect score

    def test_stability_score_decreases(self):
        personality = PredictableRuntimePersonality()
        for _ in range(5):
            personality.record_change("frequency", "normal", "high", "Test")
        score = personality.get_stability_score()
        assert score < 100.0

    def test_get_changes(self):
        personality = PredictableRuntimePersonality()
        personality.record_change("frequency", "normal", "high", "Test")
        changes = personality.get_changes()
        assert len(changes) == 1

    def test_user_initiated_change(self):
        personality = PredictableRuntimePersonality()
        change = personality.record_change("frequency", "normal", "high",
                                           "User request", user_initiated=True)
        assert change is not None
        assert change.user_initiated is True


# ═══════════════════════════════════════════════════════════════
# P8 — Audit-Visible Automation
# ═══════════════════════════════════════════════════════════════

class TestAuditVisibleAutomation:
    def test_record_automation(self):
        audit = AuditVisibleAutomation()
        record = audit.record_automation(
            AutomationType.AUTO_APPLY,
            "Auto-applied formatting",
            ["src/auth.py"],
            "Low-risk policy"
        )
        assert record.status == AutomationStatus.EXECUTED
        assert record.reverse_available is True

    def test_reverse_automation(self):
        audit = AuditVisibleAutomation()
        record = audit.record_automation(
            AutomationType.AUTO_APPLY,
            "Auto-applied formatting",
            ["src/auth.py"],
            "Low-risk policy"
        )
        assert audit.reverse(record.record_id, "User rollback") is True
        assert record.status == AutomationStatus.REVERSED

    def test_reverse_not_available(self):
        audit = AuditVisibleAutomation()
        record = audit.record_automation(
            AutomationType.AUTO_APPLY,
            "Auto-applied",
            ["file.py"],
            "Test",
            reverse_available=False
        )
        assert audit.reverse(record.record_id, "Test") is False

    def test_reverse_already_reversed(self):
        audit = AuditVisibleAutomation()
        record = audit.record_automation(AutomationType.AUTO_APPLY, "Test", ["f"], "R")
        audit.reverse(record.record_id, "First")
        assert audit.reverse(record.record_id, "Second") is False

    def test_get_history(self):
        audit = AuditVisibleAutomation()
        audit.record_automation(AutomationType.AUTO_APPLY, "A", ["f1"], "R")
        audit.record_automation(AutomationType.BATCHING, "B", ["f2"], "R")
        history = audit.get_history()
        assert len(history) == 2

    def test_filter_history_by_type(self):
        audit = AuditVisibleAutomation()
        audit.record_automation(AutomationType.AUTO_APPLY, "A", ["f1"], "R")
        audit.record_automation(AutomationType.BATCHING, "B", ["f2"], "R")
        filtered = audit.get_history(automation_type=AutomationType.AUTO_APPLY)
        assert len(filtered) == 1

    def test_get_reversible(self):
        audit = AuditVisibleAutomation()
        r1 = audit.record_automation(AutomationType.AUTO_APPLY, "A", ["f1"], "R")
        r2 = audit.record_automation(AutomationType.BATCHING, "B", ["f2"], "R")
        audit.reverse(r1.record_id, "Rollback")
        reversible = audit.get_reversible()
        assert len(reversible) == 1  # Only r2 is still reversible

    def test_stats(self):
        audit = AuditVisibleAutomation()
        audit.record_automation(AutomationType.AUTO_APPLY, "A", ["f1"], "R")
        audit.record_automation(AutomationType.BATCHING, "B", ["f2"], "R")
        stats = audit.get_stats()
        assert stats["total_records"] == 2
        assert "auto_apply" in stats["by_type"]

    def test_record_to_dict(self):
        audit = AuditVisibleAutomation()
        record = audit.record_automation(AutomationType.AUTO_APPLY, "Test", ["f"], "R")
        d = record.to_dict()
        assert d["automation_type"] == "auto_apply"
        assert d["status"] == "executed"

    def test_max_records_limit(self):
        audit = AuditVisibleAutomation(max_records=3)
        for i in range(10):
            audit.record_automation(AutomationType.AUTO_APPLY, f"T{i}", [f"f{i}"], "R")
        assert len(audit._records) <= 3


# ═══════════════════════════════════════════════════════════════
# P9 — Governance Pressure Monitoring
# ═══════════════════════════════════════════════════════════════

class TestGovernancePressure:
    def test_record_approval(self):
        monitor = GovernancePressureMonitor()
        monitor.record_approval()
        pressure = monitor.get_current_pressure()
        assert pressure["approvals_per_hour"] == 1

    def test_record_interruption(self):
        monitor = GovernancePressureMonitor()
        monitor.record_interruption()
        pressure = monitor.get_current_pressure()
        assert pressure["interruptions_per_hour"] == 1

    def test_record_event(self):
        monitor = GovernancePressureMonitor()
        monitor.record_event()
        pressure = monitor.get_current_pressure()
        assert pressure["events_per_minute"] == 1

    def test_approval_fatigue_detection(self):
        monitor = GovernancePressureMonitor()
        for _ in range(25):
            monitor.record_approval()
        pressure = monitor.get_current_pressure()
        assert pressure["approvals_per_hour"] == 25

    def test_interruption_pressure(self):
        monitor = GovernancePressureMonitor()
        for _ in range(35):
            monitor.record_interruption()
        pressure = monitor.get_current_pressure()
        assert pressure["interruptions_per_hour"] == 35

    def test_reveal_rate(self):
        monitor = GovernancePressureMonitor()
        for _ in range(10):
            monitor.record_reveal_hidden()
        pressure = monitor.get_current_pressure()
        assert pressure["reveal_rate"] > 0

    def test_override_rate(self):
        monitor = GovernancePressureMonitor()
        for _ in range(5):
            monitor.record_override()
        pressure = monitor.get_current_pressure()
        assert pressure["override_rate"] > 0

    def test_overall_level_low(self):
        monitor = GovernancePressureMonitor()
        pressure = monitor.get_current_pressure()
        assert pressure["overall_level"] == PressureLevel.LOW.value

    def test_recommendations_healthy(self):
        monitor = GovernancePressureMonitor()
        recs = monitor.get_recommendations()
        assert len(recs) == 1
        assert "healthy" in recs[0].lower()

    def test_recommendations_fatigue(self):
        monitor = GovernancePressureMonitor()
        for _ in range(25):
            monitor.record_approval()
        recs = monitor.get_recommendations()
        assert any("approval" in r.lower() for r in recs)

    def test_pressure_reading_to_dict(self):
        monitor = GovernancePressureMonitor()
        for _ in range(25):
            monitor.record_approval()
        readings = monitor.get_pressure_readings()
        if readings:
            d = readings[0].to_dict()
            assert "pressure_type" in d
            assert "level" in d


# ═══════════════════════════════════════════════════════════════
# P10 — Simplicity Preservation
# ═══════════════════════════════════════════════════════════════

class TestSimplicityPreservation:
    def test_register_subsystem(self):
        simp = SimplicityPreservation()
        ss = simp.register_subsystem("test_mod", ComplexityTier.IMPORTANT,
                                     operational_cost=2, cognitive_cost=3,
                                     purpose="Test module")
        assert ss.name == "test_mod"
        assert ss.total_cost == 5

    def test_cost_per_value(self):
        simp = SimplicityPreservation()
        ss = simp.register_subsystem("test", ComplexityTier.ESSENTIAL,
                                     operational_cost=2, cognitive_cost=2)
        # Essential tier value = 10, total cost = 4, cpv = 0.4
        assert ss.cost_per_value < 1.0

    def test_expendable_high_cost(self):
        simp = SimplicityPreservation()
        ss = simp.register_subsystem("heavy", ComplexityTier.EXPENDABLE,
                                     operational_cost=5, cognitive_cost=5,
                                     maintenance_cost=5, observability_cost=5)
        # Expendable tier value = 1, total cost = 20, cpv = 20
        assert ss.cost_per_value > 10

    def test_complexity_report(self):
        simp = SimplicityPreservation()
        simp.register_subsystem("mod1", ComplexityTier.ESSENTIAL,
                                operational_cost=2, cognitive_cost=1)
        simp.register_subsystem("mod2", ComplexityTier.IMPORTANT,
                                operational_cost=3, cognitive_cost=2)
        report = simp.get_complexity_report()
        assert report["total_subsystems"] == 2
        assert "budget_status" in report

    def test_removal_candidates(self):
        simp = SimplicityPreservation()
        simp.register_subsystem("unused", ComplexityTier.EXPENDABLE,
                                operational_cost=1, cognitive_cost=1)
        simp.register_subsystem("used", ComplexityTier.ESSENTIAL,
                                operational_cost=2, cognitive_cost=1)
        simp.record_usage("used")
        candidates = simp.get_removal_candidates()
        assert len(candidates) >= 1
        assert candidates[0]["name"] == "unused"

    def test_budget_over(self):
        budget = ComplexityBudget(max_total_cost=5, max_subsystems=2)
        simp = SimplicityPreservation(budget=budget)
        simp.register_subsystem("m1", ComplexityTier.IMPORTANT,
                                operational_cost=3, cognitive_cost=3)
        simp.register_subsystem("m2", ComplexityTier.IMPORTANT,
                                operational_cost=3, cognitive_cost=3)
        simp.register_subsystem("m3", ComplexityTier.IMPORTANT,
                                operational_cost=3, cognitive_cost=3)
        report = simp.get_complexity_report()
        assert report["budget_status"]["total"] == "OVER"
        assert report["budget_status"]["subsystems"] == "OVER"

    def test_record_usage(self):
        simp = SimplicityPreservation()
        simp.register_subsystem("mod", ComplexityTier.IMPORTANT)
        simp.record_usage("mod")
        simp.record_usage("mod")
        ss = simp.get_subsystem_cost("mod")
        assert ss is not None
        assert ss.usage_count == 2

    def test_get_all_subsystems(self):
        simp = SimplicityPreservation()
        simp.register_subsystem("a", ComplexityTier.EXPENDABLE,
                                operational_cost=5, cognitive_cost=5)
        simp.register_subsystem("b", ComplexityTier.ESSENTIAL,
                                operational_cost=1, cognitive_cost=1)
        all_subs = simp.get_all_subsystems()
        # Sorted by cost_per_value descending — "a" should be first
        assert all_subs[0]["name"] == "a"

    def test_healthy_system(self):
        simp = SimplicityPreservation()
        simp.register_subsystem("core", ComplexityTier.ESSENTIAL,
                                operational_cost=2, cognitive_cost=1)
        report = simp.get_complexity_report()
        assert report["is_healthy"] is True
