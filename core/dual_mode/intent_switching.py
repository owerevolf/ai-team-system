"""
intent_switching.py — Intent-Aware Runtime Switching.

Purpose: Runtime understands what the user wants and switches mode accordingly.

Detects:
- learning intent ("explain", "what is", "how does")
- exploration intent ("show me", "explore", "understand")
- building intent ("create", "build", "add", "implement")
- repair intent ("fix", "debug", "repair", "broken")
- explanation intent ("why", "reason", "explain")
- execution intent ("do it", "run", "execute", "apply")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


class IntentType:
    LEARNING = "learning"
    EXPLORATION = "exploration"
    BUILDING = "building"
    REPAIR = "repair"
    EXPLANATION = "explanation"
    EXECUTION = "execution"
    UNKNOWN = "unknown"


@dataclass
class IntentAnalysis:
    """Result of intent analysis."""
    intent: str = IntentType.UNKNOWN
    confidence: float = 0.0
    suggested_mode: str = ""
    reasoning: str = ""
    keywords_found: List[str] = field(default_factory=list)


class IntentSwitching:
    """
    Analyzes user intent and suggests mode switches.
    Runtime understands: is the user learning, exploring, building, or repairing?
    """

    # Intent detection patterns
    INTENT_PATTERNS = {
        IntentType.LEARNING: [
            "what is", "how does", "explain", "teach", "learn",
            "what are", "how do i", "what does", "why does",
            "i don't understand", "help me understand", "beginner",
            "new to", "first time", "never used",
        ],
        IntentType.EXPLORATION: [
            "show me", "explore", "look at", "find", "search",
            "what's in", "how is", "structure", "architecture",
            "overview", "walk through", "tour",
        ],
        IntentType.BUILDING: [
            "create", "build", "add", "implement", "make",
            "new", "start", "begin", "setup", "initialize",
            "feature", "component", "module", "system",
        ],
        IntentType.REPAIR: [
            "fix", "debug", "repair", "broken", "error",
            "bug", "issue", "problem", "not working", "crash",
            "failing", "test fails", "doesn't work",
        ],
        IntentType.EXPLANATION: [
            "why", "reason", "explain", "how come", "what caused",
            "why did", "what's the reason", "clarify",
        ],
        IntentType.EXECUTION: [
            "do it", "run", "execute", "apply", "go ahead",
            "proceed", "continue", "yes", "confirm", "approve",
            "make it so", "let's do this",
        ],
    }

    # Mode suggestions per intent
    INTENT_MODE_MAP = {
        IntentType.LEARNING: "learning",
        IntentType.EXPLORATION: "learning",
        IntentType.BUILDING: "guided",
        IntentType.REPAIR: "engineering",
        IntentType.EXPLANATION: "learning",
        IntentType.EXECUTION: "engineering",
    }

    def __init__(self, current_mode: str = "learning"):
        self._current_mode = current_mode
        self._intent_history: List[IntentAnalysis] = []

    def analyze_intent(self, user_input: str) -> IntentAnalysis:
        """Analyze user input to determine intent."""
        input_lower = user_input.lower()
        best_intent = IntentType.UNKNOWN
        best_score = 0.0
        best_keywords = []

        for intent, patterns in self.INTENT_PATTERNS.items():
            matches = []
            for pattern in patterns:
                if pattern in input_lower:
                    matches.append(pattern)

            if matches:
                score = len(matches) / len(patterns)
                if score > best_score:
                    best_score = score
                    best_intent = intent
                    best_keywords = matches

        # Boost confidence for clear signals
        confidence = min(1.0, best_score * 3)  # Scale up

        # Determine suggested mode
        suggested_mode = self.INTENT_MODE_MAP.get(best_intent, self._current_mode)

        # Build reasoning
        if best_intent != IntentType.UNKNOWN:
            reasoning = f"Detected {best_intent} intent (keywords: {', '.join(best_keywords[:3])})"
        else:
            reasoning = "No clear intent detected, keeping current mode"

        analysis = IntentAnalysis(
            intent=best_intent,
            confidence=confidence,
            suggested_mode=suggested_mode,
            reasoning=reasoning,
            keywords_found=best_keywords,
        )

        self._intent_history.append(analysis)
        return analysis

    def should_switch_mode(self, analysis: IntentAnalysis,
                           threshold: float = 0.3) -> bool:
        """Check if the intent analysis suggests a mode switch."""
        if analysis.confidence < threshold:
            return False

        if analysis.suggested_mode == self._current_mode:
            return False

        return True

    def get_switch_recommendation(self, analysis: IntentAnalysis) -> Optional[Dict[str, str]]:
        """Get a mode switch recommendation."""
        if not self.should_switch_mode(analysis):
            return None

        return {
            "from_mode": self._current_mode,
            "to_mode": analysis.suggested_mode,
            "reason": analysis.reasoning,
            "confidence": f"{analysis.confidence:.0%}",
        }

    def apply_switch(self, analysis: IntentAnalysis) -> Optional[str]:
        """Apply mode switch if recommended."""
        if self.should_switch_mode(analysis):
            old_mode = self._current_mode
            self._current_mode = analysis.suggested_mode
            logger.info(f"Intent switch: {old_mode} -> {analysis.suggested_mode} ({analysis.reasoning})")
            return analysis.suggested_mode
        return None

    def get_current_mode(self) -> str:
        return self._current_mode

    def set_mode(self, mode: str) -> None:
        self._current_mode = mode

    def get_intent_history(self, limit: int = 10) -> List[IntentAnalysis]:
        return self._intent_history[-limit:]
