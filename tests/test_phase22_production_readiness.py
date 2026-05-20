"""
Tests for Phase 22 — Production Readiness, Real Repo Operations & Developer Trust.

Tests:
- developer trust explanations
- session continuity
- complexity gate
- noise collapse
- engineering metrics
"""

import os
import tempfile
import json
from pathlib import Path

import pytest

from core.production.developer_trust import DeveloperTrust, TrustExplanation
from core.production.session_continuity import SessionContinuity, SessionState
from core.production.complexity_gate import ComplexityGate, GateDecision
from core.production.noise_collapse import NoiseCollapse, NoiseRule
from core.production.engineering_metrics import EngineeringMetrics, MetricSnapshot


# ═══════════════════════════════════════════════════════════════
# Developer Trust Tests
# ═══════════════════════════════════════════════════════════════

class TestDeveloperTrust:
    """Tests for DeveloperTrust."""

    def test_explain_patch_action(self):
        dt = DeveloperTrust()
        explanation = dt.explain_action("Generate patch", {
            "task_title": "Add logout",
            "files": ["auth.py"],
            "risk_level": "low",
            "confidence": 0.9,
        })
        assert explanation.action == "Generate patch"
        assert "patch" in explanation.reason.lower()
        assert len(explanation.evidence) > 0

    def test_explain_agent_selection(self):
        dt = DeveloperTrust()
        explanation = dt.explain_agent_selection(
            "feature_development", "backend",
            ["python", "api", "database"],
            alternatives=["frontend", "teamlead"],
        )
        assert "backend" in explanation.action
        assert "feature_development" in explanation.reason
        assert len(explanation.alternatives_considered) == 2

    def test_explain_risk_detection(self):
        dt = DeveloperTrust()
        explanation = dt.explain_risk_detection(
            "auth.py", "security_risk",
            ["File handles authentication", "No input validation"],
            0.85,
        )
        assert "risk" in explanation.action.lower()
        assert explanation.confidence == 0.85

    def test_trust_score(self):
        dt = DeveloperTrust()
        score = dt.get_trust_score({
            "unexplained_actions": 2,
            "total_actions": 10,
            "unapproved_risks": 0,
            "failed_rollbacks": 0,
        })
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Mostly explained

    def test_trust_score_low(self):
        dt = DeveloperTrust()
        score = dt.get_trust_score({
            "unexplained_actions": 8,
            "total_actions": 10,
            "unapproved_risks": 2,
            "failed_rollbacks": 1,
        })
        assert score < 0.5

    def test_to_human_text(self):
        dt = DeveloperTrust()
        explanation = dt.explain_patch_generation(
            "Add logout", ["auth.py"], "low", 0.9,
            risks=["May affect existing sessions"],
        )
        text = explanation.to_human_text()
        assert "Add logout" in text
        assert "Risk level: low" in text
        assert "90%" in text


# ═══════════════════════════════════════════════════════════════
# Session Continuity Tests
# ═══════════════════════════════════════════════════════════════

class TestSessionContinuity:
    """Tests for SessionContinuity."""

    def test_create_session(self, tmp_path):
        sc = SessionContinuity(str(tmp_path / "sessions"))
        state = sc.create_session("s1", "project1", "Build feature")
        assert state.session_id == "s1"
        assert state.current_objective == "Build feature"

    def test_resume_session(self, tmp_path):
        sc = SessionContinuity(str(tmp_path / "sessions"))
        sc.create_session("s1", "project1", "Build feature")
        sc.add_unfinished_task({"id": "t1", "title": "Add logout"})

        # Resume
        sc2 = SessionContinuity(str(tmp_path / "sessions"))
        resumed = sc2.resume_session("s1")
        assert resumed is not None
        assert resumed.session_id == "s1"
        assert len(resumed.unfinished_tasks) == 1

    def test_complete_task(self, tmp_path):
        sc = SessionContinuity(str(tmp_path / "sessions"))
        sc.create_session("s1", "project1", "Build feature")
        sc.add_unfinished_task({"id": "t1", "title": "Add logout"})
        sc.complete_task("t1", "Done")

        state = sc.get_current_state()
        assert len(state.unfinished_tasks) == 0
        assert len(state.completed_tasks) == 1

    def test_add_decision(self, tmp_path):
        sc = SessionContinuity(str(tmp_path / "sessions"))
        sc.create_session("s1", "project1", "Build feature")
        sc.add_decision("Use JWT", "Stateless auth needed")

        state = sc.get_current_state()
        assert len(state.important_decisions) == 1
        assert state.important_decisions[0]["decision"] == "Use JWT"

    def test_add_constraint(self, tmp_path):
        sc = SessionContinuity(str(tmp_path / "sessions"))
        sc.create_session("s1", "project1", "Build feature")
        sc.add_constraint("Don't break existing auth")

        state = sc.get_current_state()
        assert "Don't break existing auth" in state.active_constraints

    def test_resume_summary(self, tmp_path):
        sc = SessionContinuity(str(tmp_path / "sessions"))
        sc.create_session("s1", "project1", "Build feature")
        sc.add_unfinished_task({"id": "t1", "title": "Add logout"})
        sc.add_decision("Use JWT", "Stateless auth")
        sc.add_constraint("Don't break auth")

        summary = sc.get_resume_summary()
        assert "Build feature" in summary
        assert "Add logout" in summary
        assert "Use JWT" in summary

    def test_list_sessions(self, tmp_path):
        sc = SessionContinuity(str(tmp_path / "sessions"))
        sc.create_session("s1", "project1", "Build feature")
        sc.create_session("s2", "project2", "Fix bug")

        sessions = sc.list_sessions()
        assert len(sessions) == 2

    def test_persistence(self, tmp_path):
        session_dir = tmp_path / "sessions"
        sc1 = SessionContinuity(str(session_dir))
        sc1.create_session("s1", "project1", "Build feature")
        sc1.add_unfinished_task({"id": "t1", "title": "Add logout"})

        # New instance, same directory
        sc2 = SessionContinuity(str(session_dir))
        resumed = sc2.resume_session("s1")
        assert resumed is not None
        assert len(resumed.unfinished_tasks) == 1


# ═══════════════════════════════════════════════════════════════
# Complexity Gate Tests
# ═══════════════════════════════════════════════════════════════

class TestComplexityGate:
    """Tests for ComplexityGate."""

    def test_allow_good_idea(self):
        gate = ComplexityGate()
        decision = gate.evaluate("Simplify approval flow", "usability", {
            "phase": "test",
        })
        assert decision.allowed is True
        assert decision.score >= 0.6

    def test_block_absolute(self):
        gate = ComplexityGate()
        decision = gate.evaluate("Add autonomous coding swarm")
        assert decision.allowed is False
        assert decision.score == 0.0

    def test_block_enterprise(self):
        gate = ComplexityGate()
        decision = gate.evaluate("Add enterprise permission system")
        assert decision.allowed is False

    def test_block_agi(self):
        gate = ComplexityGate()
        decision = gate.evaluate("Implement AGI planning core")
        assert decision.allowed is False

    def test_phase_budget(self):
        gate = ComplexityGate()
        gate._phase_modules["test"] = 5  # Exceed budget

        decision = gate.evaluate("Add new feature", "usability", {"phase": "test"})
        assert decision.allowed is False
        assert any("budget" in r.lower() for r in decision.reasons)

    def test_is_healthy(self):
        gate = ComplexityGate()
        healthy, reason = gate.is_healthy()
        assert healthy is True

    def test_get_stats(self):
        gate = ComplexityGate()
        gate.evaluate("Good idea", "usability", {"phase": "test"})
        gate.evaluate("Bad idea: autonomous AGI")

        stats = gate.get_stats()
        assert stats["total_decisions"] == 2
        assert stats["allowed"] >= 1
        assert stats["blocked"] >= 1


# ═══════════════════════════════════════════════════════════════
# Noise Collapse Tests
# ═══════════════════════════════════════════════════════════════

class TestNoiseCollapse:
    """Tests for NoiseCollapse."""

    def test_suppress_duplicate(self):
        nc = NoiseCollapse()
        assert nc.should_suppress("event", "same content") is False
        assert nc.should_suppress("event", "same content") is True  # Suppressed

    def test_suppress_chatter(self):
        nc = NoiseCollapse()
        assert nc.should_suppress("agent_output", "Great question! Let me help.") is True

    def test_no_suppress_different(self):
        nc = NoiseCollapse()
        assert nc.should_suppress("event", "content A") is False
        assert nc.should_suppress("event", "content B") is False

    def test_collapse_output(self):
        nc = NoiseCollapse()
        long_output = "This is a very long output. " * 100
        collapsed = nc.collapse_output(long_output, max_length=200)
        assert len(collapsed) < len(long_output)
        assert "truncated" in collapsed

    def test_no_collapse_short(self):
        nc = NoiseCollapse()
        short = "Short output"
        assert nc.collapse_output(short, max_length=500) == short

    def test_noise_report(self):
        nc = NoiseCollapse()
        nc.should_suppress("event", "duplicate")
        nc.should_suppress("event", "duplicate")  # Suppressed

        report = nc.get_noise_report()
        assert report["total_suppressions"] >= 1


# ═══════════════════════════════════════════════════════════════
# Engineering Metrics Tests
# ═══════════════════════════════════════════════════════════════

class TestEngineeringMetrics:
    """Tests for EngineeringMetrics."""

    def test_record_task_completion(self):
        em = EngineeringMetrics()
        em.record_task_completion(True)
        em.record_task_completion(True)
        em.record_task_completion(False)

        snapshot = em.get_snapshot()
        assert snapshot.task_completion_rate == pytest.approx(0.667, rel=0.1)

    def test_record_rollback(self):
        em = EngineeringMetrics()
        em.record_task_completion(True)
        em.record_rollback()

        snapshot = em.get_snapshot()
        assert snapshot.rollback_frequency == pytest.approx(1.0, rel=0.1)

    def test_record_review(self):
        em = EngineeringMetrics()
        em.record_review(True)
        em.record_review(False)
        em.record_review(True)

        snapshot = em.get_snapshot()
        assert snapshot.review_rejection_rate == pytest.approx(0.333, rel=0.1)

    def test_record_context_recovery(self):
        em = EngineeringMetrics()
        em.record_context_recovery(True)
        em.record_context_recovery(False)

        snapshot = em.get_snapshot()
        assert snapshot.context_recovery_success == 0.5

    def test_record_onboarding_time(self):
        em = EngineeringMetrics()
        em.record_onboarding_time(5.0)
        em.record_onboarding_time(10.0)

        snapshot = em.get_snapshot()
        assert snapshot.onboarding_speed == 7.5

    def test_record_architecture_check(self):
        em = EngineeringMetrics()
        em.record_architecture_check(True)
        em.record_architecture_check(False)

        snapshot = em.get_snapshot()
        assert snapshot.architecture_understanding_accuracy == 0.5

    def test_trust_stability(self):
        em = EngineeringMetrics()
        em.record_trust_event(False)
        em.record_trust_event(False)
        em.record_trust_event(True)  # Violation

        snapshot = em.get_snapshot()
        assert snapshot.trust_stability == pytest.approx(0.667, rel=0.1)

    def test_get_summary(self):
        em = EngineeringMetrics()
        em.record_task_completion(True)
        em.record_review(True)

        summary = em.get_summary()
        assert "task_completion_rate" in summary
        assert "trust_stability" in summary
        assert summary["total_tasks"] == 1


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for Phase 22."""

    def test_full_trust_flow(self, tmp_path):
        """Simulate a full trust flow."""
        # 1. Create session
        sc = SessionContinuity(str(tmp_path / "sessions"))
        sc.create_session("s1", "my_project", "Build logout feature")

        # 2. Record progress
        sc.add_unfinished_task({"id": "t1", "title": "Add logout button"})
        sc.add_decision("Use JWT", "Stateless auth")
        sc.add_constraint("Don't break existing auth")

        # 3. Generate trust explanation
        dt = DeveloperTrust()
        explanation = dt.explain_patch_generation(
            "Add logout", ["auth.py"], "low", 0.9,
        )
        assert "Add logout" in explanation.action

        # 4. Check complexity gate
        gate = ComplexityGate()
        decision = gate.evaluate("Add logout button", "usability", {"phase": "test"})
        assert decision.allowed is True

        # 5. Resume session
        sc2 = SessionContinuity(str(tmp_path / "sessions"))
        resumed = sc2.resume_session("s1")
        assert resumed is not None
        assert len(resumed.unfinished_tasks) == 1

    def test_complexity_gate_blocks_bloat(self):
        """Complexity gate should block bloat."""
        gate = ComplexityGate()

        # Good ideas
        assert gate.evaluate("Simplify approval flow", "usability", {"phase": "test"}).allowed is True
        assert gate.evaluate("Add trust explanations", "trust", {"phase": "test"}).allowed is True

        # Bad ideas
        assert gate.evaluate("Add autonomous coding swarm").allowed is False
        assert gate.evaluate("Add enterprise permission system").allowed is False
        assert gate.evaluate("Add blockchain integration").allowed is False

    def test_noise_reduction(self):
        """Noise collapse should reduce noise."""
        nc = NoiseCollapse()

        # First event passes
        assert nc.should_suppress("event", "content") is False

        # Duplicate suppressed
        assert nc.should_suppress("event", "content") is True

        # Chatter suppressed
        assert nc.should_suppress("agent_output", "Great question!") is True

        report = nc.get_noise_report()
        assert report["total_suppressions"] >= 2

    def test_metrics_tracking(self):
        """Engineering metrics should track correctly."""
        em = EngineeringMetrics()

        for _ in range(10):
            em.record_task_completion(True)
        em.record_task_completion(False)

        em.record_review(True)
        em.record_review(False)

        em.record_context_recovery(True)

        snapshot = em.get_snapshot()
        assert snapshot.task_completion_rate > 0.8
        assert snapshot.rollback_frequency == 0.0
        assert snapshot.context_recovery_success == 1.0
