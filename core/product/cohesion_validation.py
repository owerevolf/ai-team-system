"""
cohesion_validation.py — Runtime Cohesion Validation.

Purpose: Check if the system has fallen apart into 20 separate subsystems.
The user should feel ONE system.

Checks:
- terminology consistency
- interaction consistency
- visual consistency
- workflow consistency
- orchestration consistency
- educational consistency
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class CohesionCheck:
    """A cohesion check result."""
    check_name: str = ""
    passed: bool = False
    score: float = 0.0
    issues: List[str] = field(default_factory=list)


@dataclass
class CohesionReport:
    """Complete cohesion report."""
    overall_score: float = 0.0
    passed: bool = False
    checks: List[CohesionCheck] = field(default_factory=list)
    summary: str = ""


class CohesionValidation:
    """
    Validates that the system feels like ONE cohesive product.
    Not 20 separate subsystems.
    """

    # Expected terminology across the system
    TERMINOLOGY = {
        "patch": ["patch", "change", "modification"],
        "review": ["review", "approval", "check"],
        "test": ["test", "validation", "verification"],
        "rollback": ["rollback", "revert", "undo"],
        "agent": ["agent", "assistant", "coordinator"],
        "mode": ["learning", "guided", "engineering"],
    }

    # Expected interaction patterns
    INTERACTION_PATTERNS = {
        "always_ask_before_dangerous": True,
        "always_show_rollback": True,
        "always_explain_in_learning": True,
        "never_hide_execution": True,
        "never_auto_merge": True,
    }

    def validate(self, system_state: Dict[str, Any]) -> CohesionReport:
        """Run all cohesion checks."""
        checks = []

        checks.append(self._check_terminology(system_state))
        checks.append(self._check_interactions(system_state))
        checks.append(self._check_workflow(system_state))
        checks.append(self._check_orchestration(system_state))
        checks.append(self._check_educational(system_state))

        scores = [c.score for c in checks]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        failed = [c for c in checks if c.score < 0.5]
        passed = overall_score >= 0.6 and len(failed) <= 1

        if passed:
            summary = "System is cohesive. User feels ONE system."
        elif overall_score >= 0.4:
            summary = "System is partially cohesive. Some inconsistencies detected."
        else:
            summary = "CRITICAL: System feels like separate subsystems."

        return CohesionReport(
            overall_score=round(overall_score, 2),
            passed=passed,
            checks=checks,
            summary=summary,
        )

    def _check_terminology(self, state: Dict[str, Any]) -> CohesionCheck:
        """Check terminology consistency."""
        score = 1.0
        issues = []

        # Check that key terms are used consistently
        used_terms = state.get("used_terms", {})
        for canonical, alternatives in self.TERMINOLOGY.items():
            if canonical in used_terms:
                # Check if alternatives are also used (inconsistency)
                for alt in alternatives:
                    if alt in used_terms and alt != canonical:
                        score -= 0.1
                        issues.append(f"Term inconsistency: '{canonical}' and '{alt}' both used")

        score = max(0.0, score)

        return CohesionCheck(
            check_name="terminology",
            passed=score >= 0.5,
            score=round(score, 2),
            issues=issues,
        )

    def _check_interactions(self, state: Dict[str, Any]) -> CohesionCheck:
        """Check interaction consistency."""
        score = 1.0
        issues = []

        for pattern, expected in self.INTERACTION_PATTERNS.items():
            actual = state.get(pattern, None)
            if actual is not None and actual != expected:
                score -= 0.2
                issues.append(f"Interaction '{pattern}' is {actual}, expected {expected}")

        score = max(0.0, score)

        return CohesionCheck(
            check_name="interactions",
            passed=score >= 0.5,
            score=round(score, 2),
            issues=issues,
        )

    def _check_workflow(self, state: Dict[str, Any]) -> CohesionCheck:
        """Check workflow consistency."""
        score = 1.0
        issues = []

        # Check that workflow steps are consistent
        workflow_steps = state.get("workflow_steps", [])
        expected_steps = ["understand", "plan", "generate", "review", "test", "approve", "apply"]

        if workflow_steps:
            missing = [s for s in expected_steps if s not in workflow_steps]
            if missing:
                score -= 0.1 * len(missing)
                issues.append(f"Missing workflow steps: {missing}")

        score = max(0.0, score)

        return CohesionCheck(
            check_name="workflow",
            passed=score >= 0.5,
            score=round(score, 2),
            issues=issues,
        )

    def _check_orchestration(self, state: Dict[str, Any]) -> CohesionCheck:
        """Check orchestration consistency."""
        score = 1.0
        issues = []

        # Check orchestration depth
        orch_depth = state.get("orchestration_depth", 0)
        if orch_depth > 5:
            score -= 0.3
            issues.append(f"Orchestration too deep: {orch_depth} levels")

        # Check agent count
        agent_count = state.get("active_agents", 0)
        if agent_count > 7:
            score -= 0.2
            issues.append(f"Too many active agents: {agent_count}")

        score = max(0.0, score)

        return CohesionCheck(
            check_name="orchestration",
            passed=score >= 0.5,
            score=round(score, 2),
            issues=issues,
        )

    def _check_educational(self, state: Dict[str, Any]) -> CohesionCheck:
        """Check educational consistency."""
        score = 1.0
        issues = []

        # Check that educational features are present
        if not state.get("explanations_enabled", True):
            score -= 0.3
            issues.append("Explanations disabled")

        if not state.get("learning_mode_available", True):
            score -= 0.3
            issues.append("Learning mode not available")

        if not state.get("growth_tracking", False):
            score -= 0.1
            issues.append("Growth tracking not enabled")

        score = max(0.0, score)

        return CohesionCheck(
            check_name="educational",
            passed=score >= 0.5,
            score=round(score, 2),
            issues=issues,
        )
