"""
Tests for Phase 23 — Dual-Mode Runtime Integration.

Tests:
- dual identity mode switching
- intent detection and mode switching
- identity preservation validation
"""

import pytest

from core.dual_mode.dual_identity import DualIdentity, ModeConfig, RuntimeMode
from core.dual_mode.intent_switching import IntentSwitching, IntentAnalysis, IntentType
from core.dual_mode.identity_validation import IdentityValidation, IdentityReport


# ═══════════════════════════════════════════════════════════════
# Dual Identity Tests
# ═══════════════════════════════════════════════════════════════

class TestDualIdentity:
    """Tests for DualIdentity."""

    def test_default_mode(self):
        di = DualIdentity()
        assert di.current_mode == RuntimeMode.LEARNING

    def test_switch_to_engineering(self):
        di = DualIdentity()
        config = di.switch_mode(RuntimeMode.ENGINEERING, "User requested engineering mode")
        assert di.current_mode == RuntimeMode.ENGINEERING
        assert config.agent_personality == "engineer"

    def test_switch_to_guided(self):
        di = DualIdentity()
        config = di.switch_mode(RuntimeMode.GUIDED)
        assert di.current_mode == RuntimeMode.GUIDED
        assert config.agent_personality == "coordinator"

    def test_mode_prompt_learning(self):
        di = DualIdentity(RuntimeMode.LEARNING)
        prompt = di.get_mode_prompt()
        assert "teacher" in prompt.lower()
        assert "patient" in prompt.lower()

    def test_mode_prompt_engineering(self):
        di = DualIdentity(RuntimeMode.ENGINEERING)
        prompt = di.get_mode_prompt()
        assert "engineer" in prompt.lower() or "coordinator" in prompt.lower()

    def test_format_output_learning(self):
        di = DualIdentity(RuntimeMode.LEARNING)
        output = di.format_output("Added logout button", "action")
        assert "🔧" in output or "doing" in output.lower()

    def test_format_output_engineering(self):
        di = DualIdentity(RuntimeMode.ENGINEERING)
        output = di.format_output("Added logout button", "action")
        assert output == "Added logout button"  # No decoration

    def test_approval_message_learning(self):
        di = DualIdentity(RuntimeMode.LEARNING)
        msg = di.get_approval_message("add logout button", "low")
        assert "explain" in msg.lower()
        assert "risk" in msg.lower()

    def test_approval_message_engineering(self):
        di = DualIdentity(RuntimeMode.ENGINEERING)
        msg = di.get_approval_message("add logout button", "low")
        assert "add logout button" in msg
        assert "low" in msg

    def test_should_show_reasoning(self):
        di_learning = DualIdentity(RuntimeMode.LEARNING)
        assert di_learning.should_show_reasoning() is True

        di_engineering = DualIdentity(RuntimeMode.ENGINEERING)
        assert di_engineering.should_show_reasoning() is False

    def test_mode_history(self):
        di = DualIdentity()
        di.switch_mode(RuntimeMode.ENGINEERING, "test")
        di.switch_mode(RuntimeMode.LEARNING, "back to learning")

        assert di.current_mode == RuntimeMode.LEARNING

    def test_unknown_mode_stays(self):
        di = DualIdentity()
        di.switch_mode("nonexistent_mode")
        assert di.current_mode == RuntimeMode.LEARNING  # Unchanged


# ═══════════════════════════════════════════════════════════════
# Intent Switching Tests
# ═══════════════════════════════════════════════════════════════

class TestIntentSwitching:
    """Tests for IntentSwitching."""

    def test_detect_learning_intent(self):
        isw = IntentSwitching()
        analysis = isw.analyze_intent("What is an API?")
        assert analysis.intent == IntentType.LEARNING
        assert analysis.confidence > 0

    def test_detect_building_intent(self):
        isw = IntentSwitching()
        analysis = isw.analyze_intent("Create a new auth system")
        assert analysis.intent == IntentType.BUILDING

    def test_detect_repair_intent(self):
        isw = IntentSwitching()
        analysis = isw.analyze_intent("Fix the broken login page")
        assert analysis.intent == IntentType.REPAIR

    def test_detect_exploration_intent(self):
        isw = IntentSwitching()
        analysis = isw.analyze_intent("Show me the project structure")
        assert analysis.intent == IntentType.EXPLORATION

    def test_detect_execution_intent(self):
        isw = IntentSwitching()
        analysis = isw.analyze_intent("Yes, go ahead and apply the patch")
        assert analysis.intent == IntentType.EXECUTION

    def test_mode_suggestion(self):
        isw = IntentSwitching()
        analysis = isw.analyze_intent("What is a database?")
        assert analysis.suggested_mode == "learning"

    def test_should_switch_mode(self):
        isw = IntentSwitching(current_mode="learning")
        analysis = isw.analyze_intent("Fix the production bug")
        assert analysis.suggested_mode == "engineering"
        assert isw.should_switch_mode(analysis) is True

    def test_should_not_switch_low_confidence(self):
        isw = IntentSwitching()
        analysis = isw.analyze_intent("Hi")
        assert isw.should_switch_mode(analysis) is False

    def test_apply_switch(self):
        isw = IntentSwitching(current_mode="learning")
        analysis = isw.analyze_intent("Fix the broken auth system")
        result = isw.apply_switch(analysis)
        assert result == "engineering"
        assert isw.get_current_mode() == "engineering"

    def test_intent_history(self):
        isw = IntentSwitching()
        isw.analyze_intent("What is API?")
        isw.analyze_intent("Create auth system")
        history = isw.get_intent_history()
        assert len(history) == 2


# ═══════════════════════════════════════════════════════════════
# Identity Validation Tests
# ═══════════════════════════════════════════════════════════════

class TestIdentityValidation:
    """Tests for IdentityValidation."""

    def test_healthy_system(self):
        iv = IdentityValidation()
        state = {
            "current_mode": "learning",
            "explanation_depth": "detailed",
            "educational_analogies": True,
            "show_reasoning": True,
            "show_alternatives": True,
            "approval_required": True,
            "autonomous_mode": False,
            "noise_level": 0.1,
            "interruption_rate": 1.0,
            "patch_engine": True,
            "test_runner": True,
            "lint_runner": True,
            "git_integration": True,
            "enterprise_features": 0,
            "bureaucratic_workflows": False,
            "auto_execute": False,
            "hidden_execution": False,
            "rollback_available": True,
        }
        report = iv.validate_identity(state)
        assert report.passed is True
        assert report.overall_score >= 0.6

    def test_compromised_system(self):
        iv = IdentityValidation()
        state = {
            "current_mode": "engineering",
            "explanation_depth": "minimal",
            "educational_analogies": False,
            "show_reasoning": False,
            "show_alternatives": False,
            "approval_required": False,
            "autonomous_mode": True,
            "noise_level": 0.8,
            "interruption_rate": 10.0,
            "patch_engine": False,
            "test_runner": False,
            "lint_runner": False,
            "git_integration": False,
            "enterprise_features": 3,
            "bureaucratic_workflows": True,
            "auto_execute": True,
            "hidden_execution": True,
            "rollback_available": False,
        }
        report = iv.validate_identity(state)
        assert report.passed is False
        assert len(report.critical_issues) > 0

    def test_beginner_friendly_check(self):
        iv = IdentityValidation()
        state = {"current_mode": "learning", "explanation_depth": "detailed",
                 "educational_analogies": True}
        report = iv.validate_identity(state)
        beginner_check = [c for c in report.checks if c.check_name == "beginner_friendly"][0]
        assert beginner_check.passed is True

    def test_educational_check(self):
        iv = IdentityValidation()
        state = {"show_reasoning": True, "show_alternatives": True}
        report = iv.validate_identity(state)
        edu_check = [c for c in report.checks if c.check_name == "educational"][0]
        assert edu_check.passed is True

    def test_human_centered_check(self):
        iv = IdentityValidation()
        state = {"autonomous_mode": False, "approval_required": True}
        report = iv.validate_identity(state)
        human_check = [c for c in report.checks if c.check_name == "human_centered"][0]
        assert human_check.passed is True

    def test_calm_check(self):
        iv = IdentityValidation()
        state = {"noise_level": 0.1, "interruption_rate": 1.0}
        report = iv.validate_identity(state)
        calm_check = [c for c in report.checks if c.check_name == "calm"][0]
        assert calm_check.passed is True

    def test_engineering_capable_check(self):
        iv = IdentityValidation()
        state = {"patch_engine": True, "test_runner": True, "lint_runner": True, "git_integration": True}
        report = iv.validate_identity(state)
        eng_check = [c for c in report.checks if c.check_name == "engineering_capable"][0]
        assert eng_check.passed is True

    def test_non_enterprise_check(self):
        iv = IdentityValidation()
        state = {"enterprise_features": 0, "bureaucratic_workflows": False}
        report = iv.validate_identity(state)
        non_ent_check = [c for c in report.checks if c.check_name == "non_enterprise"][0]
        assert non_ent_check.passed is True

    def test_governed_check(self):
        iv = IdentityValidation()
        state = {"auto_execute": False, "hidden_execution": False, "rollback_available": True}
        report = iv.validate_identity(state)
        governed_check = [c for c in report.checks if c.check_name == "governed"][0]
        assert governed_check.passed is True


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for Phase 23."""

    def test_full_dual_mode_flow(self):
        """Test a complete dual-mode flow."""
        # Start in learning mode
        di = DualIdentity(RuntimeMode.LEARNING)
        isw = IntentSwitching()
        iv = IdentityValidation()

        # User asks a learning question
        analysis = isw.analyze_intent("What is an API?")
        assert analysis.intent == IntentType.LEARNING

        # System stays in learning mode
        assert isw.should_switch_mode(analysis) is False  # Already learning

        # User switches to building
        analysis = isw.analyze_intent("Create an auth system")
        assert analysis.intent == IntentType.BUILDING
        assert analysis.suggested_mode == "guided"

        # Switch to guided mode
        di.switch_mode(RuntimeMode.GUIDED, "User wants to build")
        assert di.current_mode == RuntimeMode.GUIDED

        # Validate identity
        report = iv.validate_identity({
            "current_mode": "guided",
            "explanation_depth": "summary",
            "educational_analogies": True,
            "show_reasoning": True,
            "show_alternatives": True,
            "approval_required": True,
            "autonomous_mode": False,
            "noise_level": 0.2,
            "interruption_rate": 2.0,
            "patch_engine": True,
            "test_runner": True,
            "lint_runner": True,
            "git_integration": True,
            "enterprise_features": 0,
            "bureaucratic_workflows": False,
            "auto_execute": False,
            "hidden_execution": False,
            "rollback_available": True,
        })
        assert report.passed is True

    def test_mode_switching_preserves_identity(self):
        """Mode switching should preserve system identity."""
        di = DualIdentity()
        iv = IdentityValidation()

        # Switch through all modes
        for mode in [RuntimeMode.LEARNING, RuntimeMode.GUIDED, RuntimeMode.ENGINEERING]:
            di.switch_mode(mode)

            # Identity should still be valid
            report = iv.validate_identity({
                "current_mode": mode,
                "explanation_depth": di.config.explanation_depth,
                "educational_analogies": di.config.educational_analogies,
                "show_reasoning": di.config.show_reasoning,
                "show_alternatives": di.config.show_alternatives,
                "approval_required": di.config.approval_required,
                "autonomous_mode": False,
                "noise_level": 0.2,
                "interruption_rate": 2.0,
                "patch_engine": True,
                "test_runner": True,
                "lint_runner": True,
                "git_integration": True,
                "enterprise_features": 0,
                "bureaucratic_workflows": False,
                "auto_execute": False,
                "hidden_execution": False,
                "rollback_available": True,
            })

            # All modes should preserve identity
            assert report.passed is True, f"Identity lost in {mode} mode"

    def test_intent_driven_mode_switching(self):
        """Test intent-driven mode switching."""
        di = DualIdentity(RuntimeMode.LEARNING)
        isw = IntentSwitching(current_mode="learning")

        # Learning intent
        analysis = isw.analyze_intent("Explain how authentication works")
        assert analysis.suggested_mode == "learning"

        # Building intent
        analysis = isw.analyze_intent("Build a login system")
        assert analysis.suggested_mode == "guided"
        di.switch_mode(RuntimeMode.GUIDED, analysis.reasoning)

        # Repair intent
        analysis = isw.analyze_intent("Fix the broken tests")
        assert analysis.suggested_mode == "engineering"
        di.switch_mode(RuntimeMode.ENGINEERING, analysis.reasoning)

        assert di.current_mode == RuntimeMode.ENGINEERING
