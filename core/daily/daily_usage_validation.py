"""
daily_usage_validation.py — Daily Usage Validation.

Purpose: Final check — can you really live inside this system every day?

Checks:
- can open project in morning
- can work calmly all day
- don't get tired from runtime
- understand what's happening
- trust patch review
- continue work tomorrow
- learn along the way
- not afraid of AI chaos

The FINAL question: "Does the developer want to come back here every day?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class DailyCheck:
    """A daily usage check."""
    check_name: str = ""
    passed: bool = False
    score: float = 0.0
    details: str = ""


@dataclass
class DailyReport:
    """Daily usage validation report."""
    overall_score: float = 0.0
    passed: bool = False
    checks: List[DailyCheck] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class DailyUsageValidation:
    """
    Validates that the system can be used daily.
    The FINAL check of the entire project.
    """

    def validate(self, system_state: Dict[str, Any]) -> DailyReport:
        """Run all daily usage checks."""
        checks = []

        checks.append(self._check_morning_start(system_state))
        checks.append(self._check_calm_work(system_state))
        checks.append(self._check_fatigue(system_state))
        checks.append(self._check_understanding(system_state))
        checks.append(self._check_trust(system_state))
        checks.append(self._check_continuation(system_state))
        checks.append(self._check_learning(system_state))
        checks.append(self._check_safety(system_state))

        scores = [c.score for c in checks]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        failed = [c for c in checks if c.score < 0.5]
        passed = overall_score >= 0.6 and len(failed) <= 2

        recommendations = []
        for c in failed:
            recommendations.append(f"{c.check_name}: {c.details}")

        if passed:
            summary = "✅ System is ready for daily use. The developer can live inside this system."
        elif overall_score >= 0.4:
            summary = "⚠️ System is partially ready. Some aspects need improvement before daily use."
        else:
            summary = "❌ System is NOT ready for daily use. Significant issues need to be addressed."

        return DailyReport(
            overall_score=round(overall_score, 2),
            passed=passed,
            checks=checks,
            summary=summary,
            recommendations=recommendations,
        )

    def _check_morning_start(self, state: Dict[str, Any]) -> DailyCheck:
        """Check if starting the day is easy."""
        score = 1.0
        details = []

        # Check session continuity
        if not state.get("session_continuity", False):
            score -= 0.3
            details.append("No session continuity — have to start from scratch each time")

        # Check resume time
        resume_time = state.get("resume_time_seconds", 0)
        if resume_time > 30:
            score -= 0.2
            details.append(f"Resume takes {resume_time}s (should be < 10s)")

        # Check state recovery
        if not state.get("state_recovery", False):
            score -= 0.2
            details.append("No state recovery — lost context after restart")

        score = max(0.0, score)

        return DailyCheck(
            check_name="morning_start",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "Morning start is smooth",
        )

    def _check_calm_work(self, state: Dict[str, Any]) -> DailyCheck:
        """Check if working is calm."""
        score = 1.0
        details = []

        noise_level = state.get("noise_level", 0.0)
        if noise_level > 0.5:
            score -= 0.3
            details.append(f"High noise level: {noise_level}")

        interruption_rate = state.get("interruption_rate", 0.0)
        if interruption_rate > 5.0:
            score -= 0.3
            details.append(f"Too many interruptions: {interruption_rate}/min")

        if state.get("agent_chatter", False):
            score -= 0.2
            details.append("Agent chatter is noisy")

        score = max(0.0, score)

        return DailyCheck(
            check_name="calm_work",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "Work environment is calm",
        )

    def _check_fatigue(self, state: Dict[str, Any]) -> DailyCheck:
        """Check if the system causes fatigue."""
        score = 1.0
        details = []

        approval_count = state.get("daily_approvals", 0)
        if approval_count > 20:
            score -= 0.3
            details.append(f"Too many approvals: {approval_count}/day")

        click_count = state.get("daily_clicks", 0)
        if click_count > 100:
            score -= 0.2
            details.append(f"Too many clicks: {click_count}/day")

        context_switches = state.get("context_switches", 0)
        if context_switches > 10:
            score -= 0.2
            details.append(f"Too many context switches: {context_switches}/day")

        score = max(0.0, score)

        return DailyCheck(
            check_name="fatigue",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System does not cause fatigue",
        )

    def _check_understanding(self, state: Dict[str, Any]) -> DailyCheck:
        """Check if the user understands what's happening."""
        score = 1.0
        details = []

        if not state.get("explain_actions", False):
            score -= 0.3
            details.append("Actions are not explained")

        if not state.get("show_reasoning", False):
            score -= 0.2
            details.append("Reasoning is not shown")

        if state.get("hidden_operations", 0) > 0:
            score -= 0.3
            details.append(f"{state['hidden_operations']} hidden operations")

        score = max(0.0, score)

        return DailyCheck(
            check_name="understanding",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is understandable",
        )

    def _check_trust(self, state: Dict[str, Any]) -> DailyCheck:
        """Check if the user can trust the system."""
        score = 1.0
        details = []

        rollback_rate = state.get("rollback_rate", 0.0)
        if rollback_rate > 0.3:
            score -= 0.3
            details.append(f"High rollback rate: {rollback_rate:.0%}")

        if not state.get("approval_required", True):
            score -= 0.3
            details.append("Approval not required — system can act autonomously")

        if state.get("auto_execute", False):
            score -= 0.3
            details.append("Auto-execution enabled")

        score = max(0.0, score)

        return DailyCheck(
            check_name="trust",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is trustworthy",
        )

    def _check_continuation(self, state: Dict[str, Any]) -> DailyCheck:
        """Check if work can continue tomorrow."""
        score = 1.0
        details = []

        if not state.get("progress_persistence", False):
            score -= 0.3
            details.append("Progress is not persisted")

        if not state.get("task_continuation", False):
            score -= 0.2
            details.append("Tasks cannot be continued")

        if not state.get("memory_persistence", False):
            score -= 0.2
            details.append("Memory is not persisted")

        score = max(0.0, score)

        return DailyCheck(
            check_name="continuation",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "Work can continue tomorrow",
        )

    def _check_learning(self, state: Dict[str, Any]) -> DailyCheck:
        """Check if the user learns along the way."""
        score = 1.0
        details = []

        if not state.get("educational_mode", False):
            score -= 0.2
            details.append("Educational mode not available")

        if not state.get("explanations", False):
            score -= 0.3
            details.append("No explanations provided")

        if not state.get("growth_tracking", False):
            score -= 0.2
            details.append("No growth tracking")

        score = max(0.0, score)

        return DailyCheck(
            check_name="learning",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "Learning is supported",
        )

    def _check_safety(self, state: Dict[str, Any]) -> DailyCheck:
        """Check if the system is safe from AI chaos."""
        score = 1.0
        details = []

        if state.get("autonomous_mode", False):
            score -= 0.4
            details.append("Autonomous mode is dangerous")

        if not state.get("human_governance", True):
            score -= 0.4
            details.append("Human governance is disabled")

        if state.get("hidden_execution", False):
            score -= 0.3
            details.append("Hidden execution detected")

        score = max(0.0, score)

        return DailyCheck(
            check_name="safety",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is safe",
        )
