"""
agent_calibration.py — Agent Behavior Calibration.

Purpose: Remove AI-chaos behavior.
TeamLead should be an engineering coordinator, NOT an AI boss character.

Rules:
- concise outputs
- no motivational fluff
- no fake confidence
- explicit uncertainty
- structured engineering responses
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CalibrationRule:
    """A behavior calibration rule."""
    rule_id: str = ""
    name: str = ""
    description: str = ""
    enabled: bool = True
    severity: str = "warning"  # info, warning, error


@dataclass
class CalibrationReport:
    """Report on agent behavior calibration."""
    agent_id: str = ""
    total_checks: int = 0
    violations: List[str] = field(default_factory=list)
    score: float = 1.0  # 0.0 to 1.0, higher = better calibrated
    recommendations: List[str] = field(default_factory=list)


class AgentCalibration:
    """
    Calibrates agent behavior for engineering precision.
    Removes fluff, enforces clarity.
    """

    # Default calibration rules
    DEFAULT_RULES = [
        CalibrationRule("no_fluff", "No Motivational Fluff",
                        "Remove phrases like 'Great question!', 'Absolutely!', 'I'd be happy to help!'"),
        CalibrationRule("no_fake_confidence", "No Fake Confidence",
                        "Replace 'I'm certain' with 'Based on analysis' or 'Likely'"),
        CalibrationRule("explicit_uncertainty", "Explicit Uncertainty",
                        "When uncertain, say so explicitly"),
        CalibrationRule("concise_output", "Concise Outputs",
                        "Keep responses focused, no unnecessary elaboration"),
        CalibrationRule("structured_response", "Structured Responses",
                        "Use structured formats: summary, details, next steps"),
        CalibrationRule("engineering_precision", "Engineering Precision",
                        "Use precise technical language, avoid vague terms"),
        CalibrationRule("no_roleplay", "No Roleplay",
                        "TeamLead is an engineering coordinator, not a character"),
        CalibrationRule("actionable_output", "Actionable Outputs",
                        "Every output should have clear next actions"),
    ]

    # Fluff patterns to detect
    FLUFF_PATTERNS = [
        "great question", "absolutely", "i'd be happy to help",
        "certainly", "of course", "wonderful", "fantastic",
        "i'm excited to", "let me help you with that",
        "as an ai", "i understand that you",
    ]

    # Fake confidence patterns
    FAKE_CONFIDENCE_PATTERNS = [
        "i'm certain", "i'm sure", "definitely will",
        "without a doubt", "guaranteed", "100% sure",
    ]

    def __init__(self):
        self._rules: Dict[str, CalibrationRule] = {}
        for rule in self.DEFAULT_RULES:
            self._rules[rule.rule_id] = rule

    def check_output(self, output: str, agent_id: str = "teamlead") -> CalibrationReport:
        """Check an agent output for calibration violations."""
        violations = []
        recommendations = []
        output_lower = output.lower()

        # Check fluff
        for pattern in self.FLUFF_PATTERNS:
            if pattern in output_lower:
                violations.append(f"Fluff detected: '{pattern}'")
                recommendations.append("Remove motivational fluff, state facts directly")

        # Check fake confidence
        for pattern in self.FAKE_CONFIDENCE_PATTERNS:
            if pattern in output_lower:
                violations.append(f"Fake confidence: '{pattern}'")
                recommendations.append("Use 'likely', 'based on analysis', or 'uncertain'")

        # Check length (rough heuristic)
        word_count = len(output.split())
        if word_count > 500:
            violations.append(f"Overly verbose: {word_count} words")
            recommendations.append("Keep responses under 300 words for routine tasks")

        # Check structure
        has_structure = any(marker in output for marker in ["##", "- ", "1.", "Summary", "Next Steps"])
        if not has_structure and word_count > 100:
            violations.append("Unstructured output")
            recommendations.append("Use structured format: Summary, Details, Next Steps")

        # Calculate score
        score = max(0.0, 1.0 - len(violations) * 0.15)

        return CalibrationReport(
            agent_id=agent_id,
            total_checks=len(self.DEFAULT_RULES),
            violations=violations,
            score=round(score, 2),
            recommendations=list(set(recommendations)),  # Deduplicate
        )

    def calibrate_output(self, output: str) -> str:
        """Attempt to calibrate an output automatically."""
        calibrated = output

        # Remove common fluff phrases
        fluff_removals = [
            "Great question! ", "Absolutely! ", "I'd be happy to help! ",
            "Certainly! ", "Of course! ", "Wonderful! ",
        ]
        for fluff in fluff_removals:
            calibrated = calibrated.replace(fluff, "")
            calibrated = calibrated.replace(fluff.lower(), "")

        return calibrated.strip()

    def get_rules(self) -> List[CalibrationRule]:
        """Get all calibration rules."""
        return list(self._rules.values())

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a calibration rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a calibration rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False
