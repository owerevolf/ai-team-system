"""
Tests for Phase 21 — Daily Engineering Reality & Workflow Maturity.

Tests:
- enoughness enforcement
- developer friction tracking
- patch review UX
- agent calibration
- runtime calmness
"""

import pytest

from core.workflow.enoughness_enforcement import EnoughnessEnforcement, EnoughnessCheck
from core.workflow.developer_friction import DeveloperFriction, FrictionReport
from core.workflow.patch_review_ux import PatchReviewUX, PatchReviewBundle
from core.workflow.agent_calibration import AgentCalibration, CalibrationReport
from core.workflow.runtime_calmness import RuntimeCalmness, CalmnessReport


# ═══════════════════════════════════════════════════════════════
# Enoughness Enforcement Tests
# ═══════════════════════════════════════════════════════════════

class TestEnoughnessEnforcement:
    """Tests for EnoughnessEnforcement."""

    def test_check_good_idea(self):
        en = EnoughnessEnforcement()
        result = en.check_idea("Add logout button", {
            "does_it_reduce_friction": True,
            "does_it_improve_survivability": False,
            "does_it_improve_usability": True,
            "does_it_improve_learning": False,
            "does_it_improve_maintainability": True,
        })
        assert result.passed is True
        assert result.score >= 0.6

    def test_check_bad_idea(self):
        en = EnoughnessEnforcement()
        result = en.check_idea("Add autonomous agent system", {
            "does_it_reduce_friction": False,
            "does_it_improve_survivability": False,
            "does_it_improve_usability": False,
            "does_it_improve_learning": False,
            "does_it_improve_maintainability": False,
        })
        assert result.passed is False

    def test_red_flag_blocks(self):
        en = EnoughnessEnforcement()
        result = en.check_idea("Implement self-modifying runtime")
        assert result.passed is False
        assert any("RED FLAG" in r for r in result.reasons)

    def test_complexity_budget(self):
        en = EnoughnessEnforcement()
        phase = "test_phase"
        for i in range(3):
            en.register_module(phase, f"module_{i}")

        stats = en.get_phase_stats(phase)
        assert stats["modules_created"] == 3
        assert stats["budget_exhausted"] is True

    def test_should_stop(self):
        en = EnoughnessEnforcement()
        phase = "test_stop"
        for i in range(3):
            en.register_module(phase, f"module_{i}")

        should_stop, reason = en.should_stop(phase)
        assert should_stop is True
        assert "budget exhausted" in reason

    def test_should_not_stop(self):
        en = EnoughnessEnforcement()
        should_stop, reason = en.should_stop("empty_phase")
        assert should_stop is False

    def test_get_all_checks(self):
        en = EnoughnessEnforcement()
        en.check_idea("Idea 1", {"does_it_reduce_friction": True})
        en.check_idea("Idea 2", {"does_it_reduce_friction": False})
        checks = en.get_all_checks()
        assert len(checks) == 2


# ═══════════════════════════════════════════════════════════════
# Developer Friction Tests
# ═══════════════════════════════════════════════════════════════

class TestDeveloperFriction:
    """Tests for DeveloperFriction."""

    def test_record_events(self):
        df = DeveloperFriction()
        df.start_session("test")
        df.record_click("unnecessary click")
        df.record_approval("patch approval")
        df.record_context_load("context reload")

        stats = df.get_stats()
        assert stats["total_events"] == 3

    def test_approval_fatigue(self):
        df = DeveloperFriction()
        df.start_session("test")
        for i in range(6):
            df.record_approval(f"approval {i}")

        assert df.is_approval_fatigued() is True

    def test_no_approval_fatigue(self):
        df = DeveloperFriction()
        df.start_session("test")
        for i in range(3):
            df.record_approval(f"approval {i}")

        assert df.is_approval_fatigued() is False

    def test_friction_report(self):
        df = DeveloperFriction()
        df.start_session("test")
        df.record_click("click 1")
        df.record_approval("approval 1")
        df.record_orchestration("orchestration", depth=4)
        df.record_dead_end("dead end flow")
        # Add more events to trigger recommendations
        for i in range(5):
            df.record_approval(f"extra approval {i}")

        report = df.get_report("test")
        assert report.total_events == 9
        assert report.friction_score > 0
        assert len(report.recommendations) > 0

    def test_high_friction_recommendation(self):
        df = DeveloperFriction()
        df.start_session("test")
        for i in range(10):
            df.record_orchestration(f"orchestration {i}", depth=5)

        report = df.get_report("test")
        assert any("friction" in r.lower() for r in report.recommendations)


# ═══════════════════════════════════════════════════════════════
# Patch Review UX Tests
# ═══════════════════════════════════════════════════════════════

class TestPatchReviewUX:
    """Tests for PatchReviewUX."""

    def test_generate_review(self):
        ux = PatchReviewUX()
        patch_data = {
            "patch_id": "p1",
            "summary": "Add logout button",
            "reason": "User requested logout functionality",
            "risk_level": "low",
            "risk_score": 2.0,
            "files": ["auth.py", "templates/logout.html"],
            "lines_added": 15,
            "lines_removed": 3,
        }
        bundle = ux.generate_review(patch_data)
        assert bundle.patch_id == "p1"
        assert bundle.summary == "Add logout button"

    def test_review_text(self):
        ux = PatchReviewUX()
        patch_data = {
            "patch_id": "p1",
            "summary": "Add logout button",
            "reason": "User requested logout",
            "risk_level": "low",
            "files": ["auth.py"],
            "lines_added": 10,
            "lines_removed": 2,
        }
        bundle = ux.generate_review(patch_data)
        text = bundle.to_review_text()
        assert "Patch Review" in text
        assert "Add logout button" in text
        assert "Risk: LOW" in text

    def test_affected_systems_detection(self):
        ux = PatchReviewUX()
        systems = ux._detect_affected_systems(["auth/login.py", "api/routes.py"])
        assert "auth" in systems
        assert "api" in systems

    def test_generate_summary(self):
        ux = PatchReviewUX()
        patch_data = {
            "summary": "Fix auth bug",
            "files": ["auth.py"],
            "risk_level": "medium",
        }
        summary = ux.generate_summary(patch_data)
        assert "MEDIUM" in summary
        assert "Fix auth bug" in summary


# ═══════════════════════════════════════════════════════════════
# Agent Calibration Tests
# ═══════════════════════════════════════════════════════════════

class TestAgentCalibration:
    """Tests for AgentCalibration."""

    def test_check_clean_output(self):
        cal = AgentCalibration()
        output = "Summary: Fixed auth bug.\n\nDetails: Updated token validation.\n\nNext Steps: Run tests."
        report = cal.check_output(output)
        assert report.score >= 0.8
        assert len(report.violations) == 0

    def test_detect_fluff(self):
        cal = AgentCalibration()
        output = "Great question! I'd be happy to help you with that. Absolutely!"
        report = cal.check_output(output)
        assert any("Fluff" in v for v in report.violations)

    def test_detect_fake_confidence(self):
        cal = AgentCalibration()
        output = "I'm certain this will work without a doubt."
        report = cal.check_output(output)
        assert any("Fake confidence" in v for v in report.violations)

    def test_detect_verbosity(self):
        cal = AgentCalibration()
        output = "word " * 600
        report = cal.check_output(output)
        assert any("verbose" in v.lower() for v in report.violations)

    def test_calibrate_output(self):
        cal = AgentCalibration()
        output = "Great question! Here's the answer."
        calibrated = cal.calibrate_output(output)
        assert "Great question" not in calibrated

    def test_get_rules(self):
        cal = AgentCalibration()
        rules = cal.get_rules()
        assert len(rules) >= 5

    def test_enable_disable_rule(self):
        cal = AgentCalibration()
        assert cal.disable_rule("no_fluff") is True
        assert cal.enable_rule("no_fluff") is True


# ═══════════════════════════════════════════════════════════════
# Runtime Calmness Tests
# ═══════════════════════════════════════════════════════════════

class TestRuntimeCalmness:
    """Tests for RuntimeCalmness."""

    def test_calm_session(self):
        rc = RuntimeCalmness()
        rc.start_session()
        rc.record_notification("normal notification", intensity=0.2)

        report = rc.get_report()
        assert report.calmness_score >= 7.0
        assert rc.is_calm() is True

    def test_chaotic_session(self):
        rc = RuntimeCalmness()
        rc.start_session()
        for i in range(10):
            rc.record_interruption(f"interruption {i}", intensity=0.8)
            rc.record_cognitive_spike(f"spike {i}", intensity=0.9)

        report = rc.get_report()
        assert report.calmness_score < 7.0
        assert len(report.recommendations) > 0

    def test_is_calm(self):
        rc = RuntimeCalmness()
        rc.start_session()
        assert rc.is_calm() is True

    def test_not_calm(self):
        rc = RuntimeCalmness()
        rc.start_session()
        for i in range(20):
            rc.record_event_spam(f"spam {i}", intensity=0.9)

        assert rc.is_calm() is False

    def test_get_stats(self):
        rc = RuntimeCalmness()
        rc.start_session()
        rc.record_notification("test")
        rc.record_interruption("test")

        stats = rc.get_stats()
        assert stats["total_events"] == 2


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for Phase 21."""

    def test_full_workflow(self):
        """Simulate a full workflow with all Phase 21 components."""
        # 1. Check enoughness
        en = EnoughnessEnforcement()
        check = en.check_idea("Add logout button", {
            "does_it_reduce_friction": True,
            "does_it_improve_survivability": True,
            "does_it_improve_usability": True,
            "does_it_improve_learning": False,
            "does_it_improve_maintainability": False,
        })
        assert check.passed is True

        # 2. Track friction
        df = DeveloperFriction()
        df.start_session("test")
        df.record_approval("patch approval")

        # 3. Generate patch review
        ux = PatchReviewUX()
        bundle = ux.generate_review({
            "patch_id": "p1",
            "summary": "Add logout button",
            "reason": "User request",
            "risk_level": "low",
            "files": ["auth.py"],
            "lines_added": 10,
            "lines_removed": 2,
        })
        assert bundle.patch_id == "p1"

        # 4. Calibrate agent output
        cal = AgentCalibration()
        report = cal.check_output("Summary: Added logout button. Next Steps: Test.")
        assert report.score >= 0.8

        # 5. Check calmness
        rc = RuntimeCalmness()
        rc.start_session()
        assert rc.is_calm() is True

    def test_enoughness_blocks_bloat(self):
        """Enoughness enforcement should block unnecessary growth."""
        en = EnoughnessEnforcement()

        # Good idea — passes 3/5 questions
        good = en.check_idea("Simplify approval flow", {
            "does_it_reduce_friction": True,
            "does_it_improve_survivability": True,
            "does_it_improve_usability": True,
            "does_it_improve_learning": False,
            "does_it_improve_maintainability": False,
        })
        assert good.passed is True

        # Bad idea (red flag)
        bad = en.check_idea("Add autonomous self-modifying runtime")
        assert bad.passed is False

        # Bad idea (no value)
        neutral = en.check_idea("Add blockchain integration", {
            "does_it_reduce_friction": False,
            "does_it_improve_survivability": False,
            "does_it_improve_usability": False,
            "does_it_improve_learning": False,
            "does_it_improve_maintainability": False,
        })
        assert neutral.passed is False

    def test_friction_approval_fatigue(self):
        """System should detect approval fatigue."""
        df = DeveloperFriction()
        df.start_session("test")

        for i in range(10):
            df.record_approval(f"approval {i}")

        assert df.is_approval_fatigued() is True
        report = df.get_report()
        assert any("approvals" in r.lower() for r in report.recommendations)
