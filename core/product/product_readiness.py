"""
product_readiness.py — Product Readiness Validation.

Purpose: Final check — is this a real product or still an engineering experiment?

The FINAL question:
"Will a person really want to move their daily development here?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class ReadinessCheck:
    """A product readiness check."""
    check_name: str = ""
    passed: bool = False
    score: float = 0.0
    details: str = ""


@dataclass
class ReadinessReport:
    """Complete product readiness report."""
    overall_score: float = 0.0
    passed: bool = False
    checks: List[ReadinessCheck] = field(default_factory=list)
    summary: str = ""
    blockers: List[str] = field(default_factory=list)


class ProductReadiness:
    """
    Validates product readiness.
    The FINAL check of the entire project.
    """

    def validate(self, system_state: Dict[str, Any]) -> ReadinessReport:
        """Run all product readiness checks."""
        checks = []

        checks.append(self._check_installation(system_state))
        checks.append(self._check_first_run(system_state))
        checks.append(self._check_ui_understandable(system_state))
        checks.append(self._check_conversation_works(system_state))
        checks.append(self._check_feature_build(system_state))
        checks.append(self._check_bug_fix(system_state))
        checks.append(self._check_review_flow(system_state))
        checks.append(self._check_continuation(system_state))
        checks.append(self._check_learning(system_state))
        checks.append(self._check_no_chaos(system_state))
        checks.append(self._check_trust(system_state))

        scores = [c.score for c in checks]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        blockers = [f"{c.check_name}: {c.details}" for c in checks if c.score < 0.3]
        critical = [c for c in checks if c.score < 0.5]

        passed = overall_score >= 0.6 and len(blockers) == 0 and len(critical) <= 2

        if passed:
            summary = "✅ Product is READY. A developer can use this system daily."
        elif overall_score >= 0.4:
            summary = "⚠️ Product is PARTIALLY READY. Some issues need fixing."
        else:
            summary = "❌ Product is NOT READY. Significant issues need to be addressed."

        return ReadinessReport(
            overall_score=round(overall_score, 2),
            passed=passed,
            checks=checks,
            summary=summary,
            blockers=blockers,
        )

    def _check_installation(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("local_install", False):
            score -= 0.3
            details.append("No local installation support")

        install_time = state.get("install_time_minutes", 0)
        if install_time > 30:
            score -= 0.2
            details.append(f"Installation takes {install_time}min (should be < 10min)")

        return self._make_check("installation", score, details)

    def _check_first_run(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("onboarding_flow", False):
            score -= 0.3
            details.append("No onboarding flow")

        if not state.get("welcome_screen", False):
            score -= 0.1
            details.append("No welcome screen")

        return self._make_check("first_run", score, details)

    def _check_ui_understandable(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if state.get("ui_elements", 0) > 50:
            score -= 0.3
            details.append(f"Too many UI elements: {state['ui_elements']}")

        if not state.get("clear_navigation", False):
            score -= 0.2
            details.append("Navigation is unclear")

        return self._make_check("ui_understandable", score, details)

    def _check_conversation_works(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("conversation_interface", False):
            score -= 0.4
            details.append("No conversation interface")

        if not state.get("context_memory", False):
            score -= 0.2
            details.append("No context memory")

        return self._make_check("conversation_works", score, details)

    def _check_feature_build(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("patch_generation", False):
            score -= 0.4
            details.append("No patch generation")

        if not state.get("test_execution", False):
            score -= 0.2
            details.append("No test execution")

        return self._make_check("feature_build", score, details)

    def _check_bug_fix(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("repo_analysis", False):
            score -= 0.3
            details.append("No repo analysis")

        if not state.get("debugging_support", False):
            score -= 0.2
            details.append("No debugging support")

        return self._make_check("bug_fix", score, details)

    def _check_review_flow(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("patch_review", False):
            score -= 0.3
            details.append("No patch review")

        if not state.get("approval_flow", False):
            score -= 0.2
            details.append("No approval flow")

        return self._make_check("review_flow", score, details)

    def _check_continuation(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("session_persistence", False):
            score -= 0.3
            details.append("No session persistence")

        if not state.get("task_continuation", False):
            score -= 0.2
            details.append("No task continuation")

        return self._make_check("continuation", score, details)

    def _check_learning(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("educational_mode", False):
            score -= 0.3
            details.append("No educational mode")

        if not state.get("explanations", False):
            score -= 0.2
            details.append("No explanations")

        return self._make_check("learning", score, details)

    def _check_no_chaos(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if state.get("autonomous_actions", 0) > 0:
            score -= 0.4
            details.append(f"{state['autonomous_actions']} autonomous actions detected")

        if state.get("hidden_execution", False):
            score -= 0.3
            details.append("Hidden execution detected")

        if state.get("agent_count", 0) > 10:
            score -= 0.2
            details.append(f"Too many agents: {state['agent_count']}")

        return self._make_check("no_chaos", score, details)

    def _check_trust(self, state: Dict[str, Any]) -> ReadinessCheck:
        score = 1.0
        details = []

        if not state.get("human_approval", True):
            score -= 0.4
            details.append("Human approval not required")

        if not state.get("rollback_available", True):
            score -= 0.2
            details.append("Rollback not available")

        if state.get("auto_merge", False):
            score -= 0.3
            details.append("Auto-merge enabled")

        return self._make_check("trust", score, details)

    def _make_check(self, name: str, score: float, details: List[str]) -> ReadinessCheck:
        score = max(0.0, score)
        return ReadinessCheck(
            check_name=name,
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "OK",
        )
