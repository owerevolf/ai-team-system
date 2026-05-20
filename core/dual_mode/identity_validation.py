"""
identity_validation.py — Identity Preservation Validation.

Purpose: Check if the system has lost its soul.
The most important module of Phase 23.

Checks:
- beginner friendliness
- explanation quality
- educational accessibility
- engineering clarity
- calmness
- non-enterprise identity
- human-centered interaction

Critical question:
"Is the system still a friend-mentor, or has it become just another AI IDE?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class IdentityCheck:
    """Result of an identity preservation check."""
    check_name: str = ""
    passed: bool = False
    score: float = 0.0  # 0.0 to 1.0
    details: str = ""
    recommendations: List[str] = field(default_factory=list)


@dataclass
class IdentityReport:
    """Complete identity preservation report."""
    overall_score: float = 0.0
    passed: bool = False
    checks: List[IdentityCheck] = field(default_factory=list)
    summary: str = ""
    critical_issues: List[str] = field(default_factory=list)


class IdentityValidation:
    """
    Validates that the system preserves its identity.
    Checks if the system is still a friend-mentor, not just another AI IDE.
    """

    # Identity markers — what makes this system unique
    IDENTITY_MARKERS = {
        "beginner_friendly": {
            "description": "System is welcoming to beginners",
            "indicators": [
                "uses simple language",
                "provides analogies",
                "explains jargon",
                "patient tone",
                "encouraging feedback",
            ],
            "anti_indicators": [
                "assumes prior knowledge",
                "uses jargon without explanation",
                "impatient tone",
                "condescending language",
            ],
        },
        "educational": {
            "description": "System teaches, not just executes",
            "indicators": [
                "explains why, not just what",
                "shows reasoning",
                "provides learning resources",
                "asks guiding questions",
                "celebrates progress",
            ],
            "anti_indicators": [
                "just gives answers",
                "no explanation of reasoning",
                "no learning guidance",
                "purely task-focused",
            ],
        },
        "human_centered": {
            "description": "System is human-centered, not AI-centered",
            "indicators": [
                "asks for user input",
                "respects user decisions",
                "explains before acting",
                "adapts to user level",
                "shows empathy",
            ],
            "anti_indicators": [
                "acts autonomously",
                "ignores user preferences",
                "AI-first language",
                "robotic responses",
            ],
        },
        "calm": {
            "description": "System is calm, not chaotic",
            "indicators": [
                "measured responses",
                "no unnecessary urgency",
                "clear structure",
                "predictable behavior",
                "no spam",
            ],
            "anti_indicators": [
                "urgent tone",
                "information overload",
                "chaotic output",
                "notification spam",
            ],
        },
        "engineering_capable": {
            "description": "System can do real engineering work",
            "indicators": [
                "precise technical language",
                "understands architecture",
                "generates quality code",
                "follows best practices",
                "handles complexity",
            ],
            "anti_indicators": [
                "vague technical language",
                "poor code quality",
                "ignores best practices",
                "can't handle complexity",
            ],
        },
        "non_enterprise": {
            "description": "System is not an enterprise product",
            "indicators": [
                "simple interface",
                "no bureaucracy",
                "user-focused",
                "no unnecessary features",
                "personal tone",
            ],
            "anti_indicators": [
                "enterprise jargon",
                "bureaucratic workflows",
                "feature bloat",
                "corporate tone",
            ],
        },
        "governed": {
            "description": "System maintains human governance",
            "indicators": [
                "asks for approval",
                "explains risks",
                "provides rollback",
                "respects constraints",
                "transparent decisions",
            ],
            "anti_indicators": [
                "acts without approval",
                "hides risks",
                "no rollback option",
                "ignores constraints",
            ],
        },
    }

    def validate_identity(self, system_state: Dict[str, Any]) -> IdentityReport:
        """
        Run all identity preservation checks.
        Returns IdentityReport with overall score and details.
        """
        checks = []

        # Run each check
        checks.append(self._check_beginner_friendly(system_state))
        checks.append(self._check_educational(system_state))
        checks.append(self._check_human_centered(system_state))
        checks.append(self._check_calm(system_state))
        checks.append(self._check_engineering_capable(system_state))
        checks.append(self._check_non_enterprise(system_state))
        checks.append(self._check_governed(system_state))

        # Calculate overall score
        scores = [c.score for c in checks]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Determine if passed
        critical_failures = [c for c in checks if c.score < 0.3]
        passed = overall_score >= 0.6 and len(critical_failures) == 0

        # Collect critical issues
        critical_issues = []
        for c in checks:
            if c.score < 0.5:
                critical_issues.append(f"{c.check_name}: {c.details}")

        # Generate summary
        if passed:
            summary = "System identity is preserved. The system remains a friend-mentor."
        elif overall_score >= 0.4:
            summary = "System identity is partially preserved. Some aspects need attention."
        else:
            summary = "CRITICAL: System identity is compromised. The system may have become just another AI IDE."

        return IdentityReport(
            overall_score=round(overall_score, 2),
            passed=passed,
            checks=checks,
            summary=summary,
            critical_issues=critical_issues,
        )

    def _check_beginner_friendly(self, state: Dict[str, Any]) -> IdentityCheck:
        """Check if the system is beginner-friendly."""
        score = 1.0
        details = []
        recommendations = []

        # Check mode
        current_mode = state.get("current_mode", "")
        if current_mode == "engineering":
            score -= 0.2
            details.append("Currently in engineering mode (less beginner-friendly)")
            recommendations.append("Consider switching to learning mode for new users")

        # Check explanation depth
        explanation_depth = state.get("explanation_depth", "detailed")
        if explanation_depth == "minimal":
            score -= 0.3
            details.append("Explanation depth is minimal")
            recommendations.append("Increase explanation depth for better learning")

        # Check for analogies
        if not state.get("educational_analogies", True):
            score -= 0.2
            details.append("Educational analogies disabled")
            recommendations.append("Enable educational analogies for beginners")

        score = max(0.0, score)

        return IdentityCheck(
            check_name="beginner_friendly",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is beginner-friendly",
            recommendations=recommendations,
        )

    def _check_educational(self, state: Dict[str, Any]) -> IdentityCheck:
        """Check if the system is educational."""
        score = 1.0
        details = []
        recommendations = []

        if not state.get("show_reasoning", True):
            score -= 0.3
            details.append("Reasoning not shown")
            recommendations.append("Show reasoning to help users learn")

        if not state.get("show_alternatives", True):
            score -= 0.2
            details.append("Alternatives not shown")
            recommendations.append("Show alternatives to teach decision-making")

        score = max(0.0, score)

        return IdentityCheck(
            check_name="educational",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is educational",
            recommendations=recommendations,
        )

    def _check_human_centered(self, state: Dict[str, Any]) -> IdentityCheck:
        """Check if the system is human-centered."""
        score = 1.0
        details = []
        recommendations = []

        if state.get("autonomous_mode", False):
            score -= 0.5
            details.append("Autonomous mode enabled")
            recommendations.append("Disable autonomous mode to maintain human governance")

        if not state.get("approval_required", True):
            score -= 0.3
            details.append("Approval not required")
            recommendations.append("Require approval for significant actions")

        score = max(0.0, score)

        return IdentityCheck(
            check_name="human_centered",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is human-centered",
            recommendations=recommendations,
        )

    def _check_calm(self, state: Dict[str, Any]) -> IdentityCheck:
        """Check if the system is calm."""
        score = 1.0
        details = []
        recommendations = []

        noise_level = state.get("noise_level", 0.0)
        if noise_level > 0.5:
            score -= 0.3
            details.append(f"High noise level: {noise_level}")
            recommendations.append("Reduce notifications and event spam")

        interruption_rate = state.get("interruption_rate", 0.0)
        if interruption_rate > 5.0:
            score -= 0.3
            details.append(f"High interruption rate: {interruption_rate}/min")
            recommendations.append("Reduce interruptions")

        score = max(0.0, score)

        return IdentityCheck(
            check_name="calm",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is calm",
            recommendations=recommendations,
        )

    def _check_engineering_capable(self, state: Dict[str, Any]) -> IdentityCheck:
        """Check if the system is engineering-capable."""
        score = 0.5  # Start neutral
        details = []
        recommendations = []

        # Check for engineering features
        if state.get("patch_engine", False):
            score += 0.2
        if state.get("test_runner", False):
            score += 0.1
        if state.get("lint_runner", False):
            score += 0.1
        if state.get("git_integration", False):
            score += 0.1

        if score < 0.7:
            details.append("Limited engineering capabilities")
            recommendations.append("Enable more engineering tools")

        score = min(1.0, score)

        return IdentityCheck(
            check_name="engineering_capable",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is engineering-capable",
            recommendations=recommendations,
        )

    def _check_non_enterprise(self, state: Dict[str, Any]) -> IdentityCheck:
        """Check if the system is non-enterprise."""
        score = 1.0
        details = []
        recommendations = []

        enterprise_features = state.get("enterprise_features", 0)
        if enterprise_features > 0:
            score -= 0.3 * enterprise_features
            details.append(f"{enterprise_features} enterprise features detected")
            recommendations.append("Remove enterprise features")

        if state.get("bureaucratic_workflows", False):
            score -= 0.3
            details.append("Bureaucratic workflows detected")
            recommendations.append("Simplify workflows")

        score = max(0.0, score)

        return IdentityCheck(
            check_name="non_enterprise",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is non-enterprise",
            recommendations=recommendations,
        )

    def _check_governed(self, state: Dict[str, Any]) -> IdentityCheck:
        """Check if the system maintains human governance."""
        score = 1.0
        details = []
        recommendations = []

        if state.get("auto_execute", False):
            score -= 0.5
            details.append("Auto-execution enabled")
            recommendations.append("Disable auto-execution")

        if state.get("hidden_execution", False):
            score -= 0.5
            details.append("Hidden execution detected")
            recommendations.append("Make all execution visible")

        if not state.get("rollback_available", True):
            score -= 0.2
            details.append("Rollback not available")
            recommendations.append("Always provide rollback option")

        score = max(0.0, score)

        return IdentityCheck(
            check_name="governed",
            passed=score >= 0.5,
            score=round(score, 2),
            details="; ".join(details) if details else "System is governed",
            recommendations=recommendations,
        )
