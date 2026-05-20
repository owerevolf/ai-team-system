"""
dual_identity.py — Dual Runtime Identity.

Purpose: One system, two modes of interaction.
NOT two separate personalities — one system with different levels of interaction.

Modes:
- LEARNING MODE: teacher, mentor, friend, patient guide
- ENGINEERING MODE: calm senior engineer, team coordinator, governed runtime operator

The same runtime adapts based on:
- user level
- current intent
- workflow stage
- explicit mode selection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


class RuntimeMode:
    LEARNING = "learning"
    GUIDED = "guided"
    ENGINEERING = "engineering"


@dataclass
class ModeConfig:
    """Configuration for a runtime mode."""
    mode: str = RuntimeMode.LEARNING
    verbosity: str = "high"  # high, medium, low
    explanation_depth: str = "detailed"  # detailed, summary, minimal
    agent_personality: str = "teacher"  # teacher, coordinator, engineer
    approval_required: bool = True
    show_reasoning: bool = True
    show_alternatives: bool = True
    educational_analogies: bool = True
    technical_precision: str = "medium"  # low, medium, high


class DualIdentity:
    """
    Manages the dual identity of the runtime.
    One system, two modes of interaction.
    """

    # Default configs per mode
    MODE_CONFIGS = {
        RuntimeMode.LEARNING: ModeConfig(
            mode=RuntimeMode.LEARNING,
            verbosity="high",
            explanation_depth="detailed",
            agent_personality="teacher",
            approval_required=True,
            show_reasoning=True,
            show_alternatives=True,
            educational_analogies=True,
            technical_precision="low",
        ),
        RuntimeMode.GUIDED: ModeConfig(
            mode=RuntimeMode.GUIDED,
            verbosity="medium",
            explanation_depth="summary",
            agent_personality="coordinator",
            approval_required=True,
            show_reasoning=True,
            show_alternatives=True,
            educational_analogies=True,
            technical_precision="medium",
        ),
        RuntimeMode.ENGINEERING: ModeConfig(
            mode=RuntimeMode.ENGINEERING,
            verbosity="low",
            explanation_depth="minimal",
            agent_personality="engineer",
            approval_required=True,
            show_reasoning=False,
            show_alternatives=False,
            educational_analogies=False,
            technical_precision="high",
        ),
    }

    def __init__(self, default_mode: str = RuntimeMode.LEARNING):
        self._current_mode = default_mode
        self._config = self.MODE_CONFIGS[default_mode]
        self._mode_history: List[Dict[str, Any]] = []

    @property
    def current_mode(self) -> str:
        return self._current_mode

    @property
    def config(self) -> ModeConfig:
        return self._config

    def switch_mode(self, new_mode: str, reason: str = "") -> ModeConfig:
        """Switch to a different mode."""
        if new_mode not in self.MODE_CONFIGS:
            logger.warning(f"Unknown mode: {new_mode}, keeping {self._current_mode}")
            return self._config

        old_mode = self._current_mode
        self._current_mode = new_mode
        self._config = self.MODE_CONFIGS[new_mode]

        self._mode_history.append({
            "from": old_mode,
            "to": new_mode,
            "reason": reason,
        })

        logger.info(f"Mode switched: {old_mode} -> {new_mode} ({reason})")
        return self._config

    def get_mode_prompt(self) -> str:
        """Get the system prompt modification for the current mode."""
        if self._current_mode == RuntimeMode.LEARNING:
            return (
                "You are a patient teacher and mentor. "
                "Explain everything clearly, use simple language, "
                "provide analogies, and never assume prior knowledge. "
                "Always explain WHY, not just WHAT. "
                "Be encouraging and supportive."
            )
        elif self._current_mode == RuntimeMode.GUIDED:
            return (
                "You are a senior engineer guiding a colleague. "
                "Explain your reasoning, show alternatives, "
                "and help them understand the engineering process. "
                "Balance explanation with execution."
            )
        else:  # ENGINEERING
            return (
                "You are a calm, precise engineering coordinator. "
                "Be concise, technical, and direct. "
                "Focus on execution quality and safety. "
                "Minimize explanation unless asked."
            )

    def format_output(self, content: str, output_type: str = "general") -> str:
        """Format output according to current mode."""
        if self._current_mode == RuntimeMode.LEARNING:
            if output_type == "explanation":
                return f"📚 **Explanation:**\n\n{content}\n\n💡 *Does this make sense? Ask me anything!*"
            elif output_type == "action":
                return f"🔧 **What I'm doing:**\n\n{content}\n\n*I'll explain each step as we go.*"
            else:
                return f"{content}\n\n*Feel free to ask if you need clarification!*"

        elif self._current_mode == RuntimeMode.GUIDED:
            if output_type == "explanation":
                return f"**Reasoning:** {content}"
            elif output_type == "action":
                return f"**Action:** {content}"
            else:
                return content

        else:  # ENGINEERING
            return content

    def should_show_reasoning(self) -> bool:
        return self._config.show_reasoning

    def should_show_alternatives(self) -> bool:
        return self._config.show_alternatives

    def should_use_analogies(self) -> bool:
        return self._config.educational_analogies

    def get_approval_message(self, action: str, risk_level: str) -> str:
        """Get mode-appropriate approval message."""
        if self._current_mode == RuntimeMode.LEARNING:
            return (
                f"Before I {action}, let me explain what this means:\n"
                f"This change has **{risk_level}** risk level.\n"
                f"Risk means: how likely is this to cause problems.\n\n"
                f"Should I proceed?"
            )
        elif self._current_mode == RuntimeMode.GUIDED:
            return (
                f"About to: {action}\n"
                f"Risk: {risk_level}\n"
                f"Approve to proceed."
            )
        else:
            return f"{action} [{risk_level}] — approve?"

    def get_mode_summary(self) -> str:
        """Get a summary of the current mode."""
        return (
            f"Mode: {self._current_mode.upper()}\n"
            f"Personality: {self._config.agent_personality}\n"
            f"Verbosity: {self._config.verbosity}\n"
            f"Explanation: {self._config.explanation_depth}\n"
            f"Analogies: {'yes' if self._config.educational_analogies else 'no'}\n"
            f"Technical precision: {self._config.technical_precision}"
        )
