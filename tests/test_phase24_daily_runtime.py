"""
Tests for Phase 24 — Real Developer Experience, Self-Development & Daily Use Maturity.

Tests:
- self-development governed flow
- self-protection blocks dangerous actions
- growth journey progression
- daily usage validation
"""

import pytest

from core.daily.self_development import SelfDevelopment, SelfDevTask
from core.daily.self_protection import SelfProtection, ProtectionDecision
from core.daily.growth_journey import GrowthJourney, UserProgress, JourneyStage, STAGES
from core.daily.daily_usage_validation import DailyUsageValidation, DailyReport


# ═══════════════════════════════════════════════════════════════
# Self-Development Tests
# ═══════════════════════════════════════════════════════════════

class TestSelfDevelopment:
    """Tests for SelfDevelopment."""

    def test_create_task(self):
        sd = SelfDevelopment()
        task = sd.create_task("Add docstrings", "Add missing docstrings", ["utils.py"])
        assert task is not None
        assert task.title == "Add docstrings"
        assert task.status == "pending"

    def test_block_protected_area(self):
        sd = SelfDevelopment()
        task = sd.create_task("Modify gate", "Try to modify complexity gate",
                              ["core/production/complexity_gate.py"])
        assert task is None  # Blocked

    def test_task_limit(self):
        sd = SelfDevelopment()
        created = 0
        for i in range(5):
            task = sd.create_task(f"Task {i}", f"Description {i}", [f"file_{i}.py"])
            if task is not None:
                created += 1
        assert created == 3  # Max 3 per session

    def test_advance_task(self):
        sd = SelfDevelopment()
        task = sd.create_task("Test", "Test", ["test.py"])
        assert sd.advance_task(task.task_id, "planning") is True
        assert task.status == "planning"

    def test_invalid_transition(self):
        sd = SelfDevelopment()
        task = sd.create_task("Test", "Test", ["test.py"])
        assert sd.advance_task(task.task_id, "applied") is False  # Can't skip steps

    def test_safe_candidates(self):
        sd = SelfDevelopment()
        candidates = sd.get_safe_self_dev_candidates()
        assert len(candidates) > 0
        for c in candidates:
            assert "title" in c
            assert "risk" in c


# ═══════════════════════════════════════════════════════════════
# Self-Protection Tests
# ═══════════════════════════════════════════════════════════════

class TestSelfProtection:
    """Tests for SelfProtection."""

    def test_block_dangerous_action(self):
        sp = SelfProtection()
        decision = sp.check_action("bypass_governance")
        assert decision.allowed is False
        assert decision.risk_level == "critical"

    def test_block_rewrite_core(self):
        sp = SelfProtection()
        decision = sp.check_action("rewrite_orchestration_core")
        assert decision.allowed is False

    def test_approval_required(self):
        sp = SelfProtection()
        decision = sp.check_action("modify_approval_flow")
        assert decision.allowed is False
        assert decision.blocked_by == "approval_required"

    def test_approval_granted(self):
        sp = SelfProtection()
        decision = sp.check_action("modify_approval_flow", {"human_approved": True})
        assert decision.allowed is True

    def test_protected_file(self):
        sp = SelfProtection()
        assert sp.is_protected_file("core/production/complexity_gate.py") is True
        assert sp.is_protected_file("web_ui/app.py") is False

    def test_patch_safety(self):
        sp = SelfProtection()
        decision = sp.validate_patch_safety(["core/production/self_protection.py"])
        assert decision.allowed is False

    def test_safe_patch(self):
        sp = SelfProtection()
        decision = sp.validate_patch_safety(["web_ui/app.py"])
        assert decision.allowed is True

    def test_protection_status(self):
        sp = SelfProtection()
        status = sp.get_protection_status()
        assert status["status"] == "active"
        assert status["blocked_actions"] > 0


# ═══════════════════════════════════════════════════════════════
# Growth Journey Tests
# ═══════════════════════════════════════════════════════════════

class TestGrowthJourney:
    """Tests for GrowthJourney."""

    def test_default_stage(self):
        gj = GrowthJourney()
        progress = gj.get_or_create_progress("user1")
        assert progress.current_stage == JourneyStage.BEGINNER

    def test_record_milestone(self):
        gj = GrowthJourney()
        assert gj.record_milestone("user1", "first_conversation") is True
        progress = gj.get_or_create_progress("user1")
        assert "first_conversation" in progress.completed_milestones

    def test_duplicate_milestone(self):
        gj = GrowthJourney()
        gj.record_milestone("user1", "first_conversation")
        assert gj.record_milestone("user1", "first_conversation") is False

    def test_record_skill(self):
        gj = GrowthJourney()
        gj.record_skill("user1", "code_reading", 2)
        progress = gj.get_or_create_progress("user1")
        assert progress.skills_demonstrated["code_reading"] == 2

    def test_stage_advancement(self):
        gj = GrowthJourney()
        progress = gj.get_or_create_progress("user1")

        # Complete all beginner milestones
        for milestone in gj.MILESTONES[JourneyStage.BEGINNER]:
            gj.record_milestone("user1", milestone)

        # Should have advanced
        progress = gj.get_or_create_progress("user1")
        assert progress.current_stage != JourneyStage.BEGINNER

    def test_adapt_to_stage(self):
        gj = GrowthJourney()
        progress = gj.get_or_create_progress("user1")

        # Manually set to engineering
        progress.current_stage = JourneyStage.INDEPENDENT_ENGINEER
        gj._adapt_to_stage(progress)

        assert progress.preferred_mode == "engineering"
        assert progress.explanation_preference == "minimal"

    def test_stage_guidance(self):
        gj = GrowthJourney()
        guidance = gj.get_stage_guidance(JourneyStage.BEGINNER)
        assert "getting started" in guidance.lower() or "explain" in guidance.lower()

    def test_progress_summary(self):
        gj = GrowthJourney()
        gj.record_milestone("user1", "first_conversation")
        summary = gj.get_progress_summary("user1")
        assert "First Conversation" in summary  # Title case in output
        assert "Journey" in summary


# ═══════════════════════════════════════════════════════════════
# Daily Usage Validation Tests
# ═══════════════════════════════════════════════════════════════

class TestDailyUsageValidation:
    """Tests for DailyUsageValidation."""

    def test_healthy_system(self):
        dv = DailyUsageValidation()
        state = {
            "session_continuity": True,
            "resume_time_seconds": 5,
            "state_recovery": True,
            "noise_level": 0.1,
            "interruption_rate": 1.0,
            "agent_chatter": False,
            "daily_approvals": 5,
            "daily_clicks": 30,
            "context_switches": 3,
            "explain_actions": True,
            "show_reasoning": True,
            "hidden_operations": 0,
            "approval_required": True,
            "auto_execute": False,
            "rollback_rate": 0.05,
            "progress_persistence": True,
            "task_continuation": True,
            "memory_persistence": True,
            "educational_mode": True,
            "explanations": True,
            "growth_tracking": True,
            "autonomous_mode": False,
            "human_governance": True,
            "hidden_execution": False,
        }
        report = dv.validate(state)
        assert report.passed is True
        assert report.overall_score >= 0.6

    def test_unhealthy_system(self):
        dv = DailyUsageValidation()
        state = {
            "session_continuity": False,
            "resume_time_seconds": 60,
            "state_recovery": False,
            "noise_level": 0.8,
            "interruption_rate": 15.0,
            "agent_chatter": True,
            "daily_approvals": 50,
            "daily_clicks": 200,
            "context_switches": 20,
            "explain_actions": False,
            "show_reasoning": False,
            "hidden_operations": 5,
            "approval_required": False,
            "auto_execute": True,
            "rollback_rate": 0.5,
            "progress_persistence": False,
            "task_continuation": False,
            "memory_persistence": False,
            "educational_mode": False,
            "explanations": False,
            "growth_tracking": False,
            "autonomous_mode": True,
            "human_governance": False,
            "hidden_execution": True,
        }
        report = dv.validate(state)
        assert report.passed is False
        assert len(report.recommendations) > 0

    def test_morning_start_check(self):
        dv = DailyUsageValidation()
        state = {"session_continuity": True, "resume_time_seconds": 5, "state_recovery": True}
        report = dv.validate(state)
        morning_check = [c for c in report.checks if c.check_name == "morning_start"][0]
        assert morning_check.passed is True

    def test_trust_check(self):
        dv = DailyUsageValidation()
        state = {"approval_required": True, "auto_execute": False, "rollback_rate": 0.05}
        report = dv.validate(state)
        trust_check = [c for c in report.checks if c.check_name == "trust"][0]
        assert trust_check.passed is True

    def test_safety_check(self):
        dv = DailyUsageValidation()
        state = {"autonomous_mode": False, "human_governance": True, "hidden_execution": False}
        report = dv.validate(state)
        safety_check = [c for c in report.checks if c.check_name == "safety"][0]
        assert safety_check.passed is True


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for Phase 24."""

    def test_self_dev_flow(self):
        """Test a complete self-development flow."""
        sd = SelfDevelopment()
        sp = SelfProtection()

        # Create a safe self-dev task
        task = sd.create_task("Add docstrings", "Add missing docstrings", ["utils.py"])
        assert task is not None

        # Check patch safety
        decision = sp.validate_patch_safety(task.target_files)
        assert decision.allowed is True

        # Advance through flow
        assert sd.advance_task(task.task_id, "planning") is True
        assert sd.advance_task(task.task_id, "generating") is True
        assert sd.advance_task(task.task_id, "reviewing") is True
        assert sd.advance_task(task.task_id, "testing") is True
        assert sd.advance_task(task.task_id, "approved") is True
        assert sd.advance_task(task.task_id, "applied") is True

        assert task.status == "applied"

    def test_self_protection_blocks_self_dev(self):
        """Self-protection should block dangerous self-dev."""
        sd = SelfDevelopment()
        sp = SelfProtection()

        # Try to modify protected file
        task = sd.create_task("Modify gate", "Try to modify",
                              ["core/production/complexity_gate.py"])
        assert task is None  # Blocked by self-development

        # Try to bypass governance
        decision = sp.check_action("bypass_governance")
        assert decision.allowed is False

    def test_growth_journey_progression(self):
        """Test user progression through stages."""
        gj = GrowthJourney()

        # Beginner milestones
        for milestone in gj.MILESTONES[JourneyStage.BEGINNER]:
            gj.record_milestone("user1", milestone)

        progress = gj.get_or_create_progress("user1")
        # Should have advanced
        assert progress.current_stage != JourneyStage.BEGINNER

    def test_daily_validation_integration(self):
        """Test daily validation with real system state."""
        dv = DailyUsageValidation()

        # Simulate a healthy daily state
        state = {
            "session_continuity": True,
            "resume_time_seconds": 3,
            "state_recovery": True,
            "noise_level": 0.1,
            "interruption_rate": 0.5,
            "agent_chatter": False,
            "daily_approvals": 3,
            "daily_clicks": 20,
            "context_switches": 2,
            "explain_actions": True,
            "show_reasoning": True,
            "hidden_operations": 0,
            "approval_required": True,
            "auto_execute": False,
            "rollback_rate": 0.0,
            "progress_persistence": True,
            "task_continuation": True,
            "memory_persistence": True,
            "educational_mode": True,
            "explanations": True,
            "growth_tracking": True,
            "autonomous_mode": False,
            "human_governance": True,
            "hidden_execution": False,
        }

        report = dv.validate(state)
        assert report.passed is True
        assert report.overall_score >= 0.8
