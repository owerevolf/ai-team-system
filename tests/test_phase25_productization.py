"""
Tests for Phase 25 — Real Productization, UI Cohesion & Production Workflow Reality.

Tests:
- unified workspace mode switching
- cohesion validation
- product readiness validation
"""

import pytest

from core.product.unified_workspace import UnifiedWorkspace, WorkspaceState
from core.product.cohesion_validation import CohesionValidation, CohesionReport
from core.product.product_readiness import ProductReadiness, ReadinessReport


# ═══════════════════════════════════════════════════════════════
# Unified Workspace Tests
# ═══════════════════════════════════════════════════════════════

class TestUnifiedWorkspace:
    """Tests for UnifiedWorkspace."""

    def test_default_state(self):
        ws = UnifiedWorkspace()
        assert ws.state.active_mode == "learning"
        assert ws.state.current_view == "conversation"

    def test_switch_to_engineering(self):
        ws = UnifiedWorkspace()
        ws.switch_mode("engineering")
        assert ws.state.active_mode == "engineering"

    def test_switch_to_guided(self):
        ws = UnifiedWorkspace()
        ws.switch_mode("guided")
        assert ws.state.active_mode == "guided"

    def test_available_views_learning(self):
        ws = UnifiedWorkspace("learning")
        views = ws.get_available_views()
        assert "conversation" in views
        assert "project" in views

    def test_available_views_engineering(self):
        ws = UnifiedWorkspace("engineering")
        views = ws.get_available_views()
        assert "conversation" in views
        assert "review" in views
        assert "memory" in views

    def test_switch_view(self):
        ws = UnifiedWorkspace()
        assert ws.switch_view("project") is True
        assert ws.state.current_view == "project"

    def test_switch_view_unavailable(self):
        ws = UnifiedWorkspace("learning")
        assert ws.switch_view("memory") is False  # Not available in learning

    def test_toggle_sidebar(self):
        ws = UnifiedWorkspace()
        assert ws.state.sidebar_collapsed is False
        ws.toggle_sidebar()
        assert ws.state.sidebar_collapsed is True

    def test_set_right_panel(self):
        ws = UnifiedWorkspace()
        assert ws.set_right_panel("context") is True
        assert ws.state.right_panel == "context"

    def test_recent_conversations(self):
        ws = UnifiedWorkspace()
        ws.add_recent_conversation("Test convo", "conv1")
        assert len(ws.state.recent_conversations) == 1

    def test_workspace_summary(self):
        ws = UnifiedWorkspace()
        summary = ws.get_workspace_summary()
        assert "Workspace" in summary
        assert "learning" in summary


# ═══════════════════════════════════════════════════════════════
# Cohesion Validation Tests
# ═══════════════════════════════════════════════════════════════

class TestCohesionValidation:
    """Tests for CohesionValidation."""

    def test_cohesive_system(self):
        cv = CohesionValidation()
        state = {
            "used_terms": {"patch": 5, "review": 3},
            "always_ask_before_dangerous": True,
            "always_show_rollback": True,
            "always_explain_in_learning": True,
            "never_hide_execution": True,
            "never_auto_merge": True,
            "workflow_steps": ["understand", "plan", "generate", "review", "test", "approve", "apply"],
            "orchestration_depth": 3,
            "active_agents": 5,
            "explanations_enabled": True,
            "learning_mode_available": True,
            "growth_tracking": True,
        }
        report = cv.validate(state)
        assert report.passed is True
        assert report.overall_score >= 0.6

    def test_incohesive_system(self):
        cv = CohesionValidation()
        state = {
            "used_terms": {"patch": 5, "modification": 3, "change": 2},  # Very inconsistent
            "always_ask_before_dangerous": False,
            "always_show_rollback": False,
            "always_explain_in_learning": False,
            "never_hide_execution": False,
            "never_auto_merge": False,
            "workflow_steps": [],  # Missing all steps
            "orchestration_depth": 12,
            "active_agents": 25,
            "explanations_enabled": False,
            "learning_mode_available": False,
            "growth_tracking": False,
        }
        report = cv.validate(state)
        assert report.passed is False

    def test_terminology_check(self):
        cv = CohesionValidation()
        state = {"used_terms": {"patch": 5, "modification": 3}}
        report = cv.validate(state)
        term_check = [c for c in report.checks if c.check_name == "terminology"][0]
        assert len(term_check.issues) > 0

    def test_orchestration_check(self):
        cv = CohesionValidation()
        state = {"orchestration_depth": 10, "active_agents": 20}
        report = cv.validate(state)
        orch_check = [c for c in report.checks if c.check_name == "orchestration"][0]
        assert orch_check.passed is False


# ═══════════════════════════════════════════════════════════════
# Product Readiness Tests
# ═══════════════════════════════════════════════════════════════

class TestProductReadiness:
    """Tests for ProductReadiness."""

    def test_ready_product(self):
        pr = ProductReadiness()
        state = {
            "local_install": True,
            "install_time_minutes": 5,
            "onboarding_flow": True,
            "welcome_screen": True,
            "ui_elements": 20,
            "clear_navigation": True,
            "conversation_interface": True,
            "context_memory": True,
            "patch_generation": True,
            "test_execution": True,
            "repo_analysis": True,
            "debugging_support": True,
            "patch_review": True,
            "approval_flow": True,
            "session_persistence": True,
            "task_continuation": True,
            "educational_mode": True,
            "explanations": True,
            "autonomous_actions": 0,
            "hidden_execution": False,
            "agent_count": 5,
            "human_approval": True,
            "rollback_available": True,
            "auto_merge": False,
        }
        report = pr.validate(state)
        assert report.passed is True
        assert report.overall_score >= 0.8

    def test_unready_product(self):
        pr = ProductReadiness()
        state = {
            "local_install": False,
            "install_time_minutes": 60,
            "onboarding_flow": False,
            "conversation_interface": False,
            "patch_generation": False,
            "session_persistence": False,
            "educational_mode": False,
            "autonomous_actions": 5,
            "hidden_execution": True,
            "agent_count": 20,
            "human_approval": False,
            "rollback_available": False,
            "auto_merge": True,
        }
        report = pr.validate(state)
        assert report.passed is False
        assert len(report.blockers) > 0

    def test_installation_check(self):
        pr = ProductReadiness()
        state = {"local_install": True, "install_time_minutes": 5}
        report = pr.validate(state)
        check = [c for c in report.checks if c.check_name == "installation"][0]
        assert check.passed is True

    def test_trust_check(self):
        pr = ProductReadiness()
        state = {"human_approval": True, "rollback_available": True, "auto_merge": False}
        report = pr.validate(state)
        check = [c for c in report.checks if c.check_name == "trust"][0]
        assert check.passed is True

    def test_no_chaos_check(self):
        pr = ProductReadiness()
        state = {"autonomous_actions": 0, "hidden_execution": False, "agent_count": 5}
        report = pr.validate(state)
        check = [c for c in report.checks if c.check_name == "no_chaos"][0]
        assert check.passed is True


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for Phase 25."""

    def test_full_product_flow(self):
        """Test a complete product flow."""
        # 1. Create workspace
        ws = UnifiedWorkspace("learning")
        assert ws.state.active_mode == "learning"

        # 2. Switch to engineering
        ws.switch_mode("engineering")
        assert ws.state.active_mode == "engineering"

        # 3. Validate cohesion
        cv = CohesionValidation()
        cohesion = cv.validate({
            "used_terms": {"patch": 5},
            "always_ask_before_dangerous": True,
            "orchestration_depth": 3,
            "active_agents": 5,
            "explanations_enabled": True,
            "learning_mode_available": True,
        })
        assert cohesion.passed is True

        # 4. Validate product readiness
        pr = ProductReadiness()
        readiness = pr.validate({
            "local_install": True,
            "conversation_interface": True,
            "patch_generation": True,
            "human_approval": True,
            "rollback_available": True,
            "autonomous_actions": 0,
        })
        assert readiness.passed is True

    def test_mode_switching_maintains_cohesion(self):
        """Mode switching should maintain system cohesion."""
        ws = UnifiedWorkspace()
        cv = CohesionValidation()

        for mode in ["learning", "guided", "engineering"]:
            ws.switch_mode(mode)

            report = cv.validate({
                "used_terms": {"patch": 5},
                "always_ask_before_dangerous": True,
                "orchestration_depth": 3,
                "active_agents": 5,
                "explanations_enabled": True,
                "learning_mode_available": True,
            })

            assert report.passed is True, f"Cohesion lost in {mode} mode"
