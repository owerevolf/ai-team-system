"""
intent_preservation.py — Identity Anchor Runtime.

Problem: After 50 tasks, AI forgets why the project exists.

Intent preservation stores:
- project identity
- educational philosophy
- UX goals
- anti-goals
- engineering values
- architectural principles

Example:
  THIS PROJECT IS:
  - educational-first
  - human-controlled
  - beginner-friendly
  - local-first

  THIS PROJECT IS NOT:
  - autonomous AGI
  - enterprise SaaS
  - self-modifying AI
  - hidden automation

This is the identity anchor runtime.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class IntentStatement:
    """A single intent statement."""
    statement: str = ""
    category: str = ""  # identity, anti_goal, principle, value
    priority: int = 5  # 1 = highest
    immutable: bool = False  # cannot be changed by AI
    created_at: str = ""
    updated_at: str = ""


class IntentPreservation:
    """
    Identity anchor runtime.

    Ensures the project's core identity is never lost.
    Anti-goals prevent drift into unwanted directions.
    """

    # Default identity for AI Team System
    DEFAULT_IDENTITY = {
        "name": "AI Team System",
        "purpose": "AI-assisted engineering workspace with human governance",
        "target_audience": "Developers who want AI assistance without losing control",
        "core_values": [
            "human-controlled",
            "educational-first",
            "beginner-friendly",
            "local-first",
            "transparent",
            "predictable",
        ],
        "anti_goals": [
            "autonomous AGI",
            "enterprise SaaS",
            "self-modifying AI",
            "hidden automation",
            "unrestricted shell access",
            "autonomous deploy",
            "auto merge to main",
        ],
        "ux_philosophy": (
            "Every action must have visible feedback. "
            "Never leave the user wondering if something worked. "
            "Show loading states, success messages, and error messages."
        ),
        "coding_preferences": [
            "PATCHES > DIRECT WRITES",
            "NO FREE AGENTS",
            "HUMAN APPROVAL REQUIRED",
            "WORKSPACE ISOLATION",
            "Tests before code",
            "Small commits",
            "Descriptive commit messages",
        ],
        "educational_principles": [
            "Explain why, not just what",
            "Show working code, not just tests",
            "Progressive complexity",
            "Safe experimentation",
        ],
    }

    def __init__(self):
        self._intents: Dict[str, IntentStatement] = {}
        self._immutable_intents: Dict[str, IntentStatement] = {}
        self._lock = threading.Lock()
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default identity statements."""
        now = datetime.utcnow().isoformat() + "Z"

        # Core identity
        for value in self.DEFAULT_IDENTITY["core_values"]:
            key = f"value:{value}"
            self._immutable_intents[key] = IntentStatement(
                statement=value, category="value", priority=1,
                immutable=True, created_at=now, updated_at=now,
            )

        # Anti-goals
        for anti_goal in self.DEFAULT_IDENTITY["anti_goals"]:
            key = f"anti:{anti_goal}"
            self._immutable_intents[key] = IntentStatement(
                statement=anti_goal, category="anti_goal", priority=1,
                immutable=True, created_at=now, updated_at=now,
            )

        # Coding preferences
        for pref in self.DEFAULT_IDENTITY["coding_preferences"]:
            key = f"pref:{pref}"
            self._immutable_intents[key] = IntentStatement(
                statement=pref, category="principle", priority=2,
                immutable=True, created_at=now, updated_at=now,
            )

        # Educational principles
        for principle in self.DEFAULT_IDENTITY["educational_principles"]:
            key = f"edu:{principle}"
            self._immutable_intents[key] = IntentStatement(
                statement=principle, category="principle", priority=3,
                immutable=True, created_at=now, updated_at=now,
            )

    def add_intent(self, statement: str, category: str = "principle",
                   priority: int = 5, immutable: bool = False) -> IntentStatement:
        """Add an intent statement."""
        with self._lock:
            key = f"{category}:{statement}"
            now = datetime.utcnow().isoformat() + "Z"
            intent = IntentStatement(
                statement=statement, category=category,
                priority=priority, immutable=immutable,
                created_at=now, updated_at=now,
            )

            if immutable:
                self._immutable_intents[key] = intent
            else:
                self._intents[key] = intent

            return intent

    def remove_intent(self, statement: str, category: str = "principle") -> bool:
        """Remove a non-immutable intent."""
        key = f"{category}:{statement}"
        with self._lock:
            if key in self._immutable_intents:
                logger.warning(f"Cannot remove immutable intent: {key}")
                return False
            if key in self._intents:
                del self._intents[key]
                return True
            return False

    def get_identity_summary(self) -> str:
        """Get compressed identity summary for LLM context."""
        lines = ["# Project Identity", ""]

        # Core values
        values = [i.statement for i in self._immutable_intents.values()
                  if i.category == "value"]
        if values:
            lines.append(f"**Core Values:** {', '.join(values)}")

        # Anti-goals
        anti_goals = [i.statement for i in self._immutable_intents.values()
                      if i.category == "anti_goal"]
        if anti_goals:
            lines.append(f"\n**Anti-Goals (NEVER):**")
            for ag in anti_goals:
                lines.append(f"- {ag}")

        # Principles
        principles = [i.statement for i in self._immutable_intents.values()
                      if i.category == "principle"]
        if principles:
            lines.append(f"\n**Engineering Principles:**")
            for p in principles:
                lines.append(f"- {p}")

        # Educational principles
        edu = [i.statement for i in self._immutable_intents.values()
               if i.category == "principle" and "edu:" in f"edu:{i.statement}"]
        if edu:
            lines.append(f"\n**Educational Principles:**")
            for e in edu:
                lines.append(f"- {e}")

        # Mutable intents
        mutable = list(self._intents.values())
        if mutable:
            lines.append(f"\n**Additional Intent:**")
            for m in mutable:
                lines.append(f"- {m.statement}")

        return "\n".join(lines)

    def check_against_intents(self, proposed_action: str) -> Tuple[bool, str]:
        """
        Check if a proposed action violates any intent.

        Returns (allowed, reason).
        """
        proposed_lower = proposed_action.lower()

        # Check anti-goals
        for intent in self._immutable_intents.values():
            if intent.category == "anti_goal":
                if intent.statement.lower() in proposed_lower:
                    return False, f"Action violates anti-goal: '{intent.statement}'"

        return True, "OK"

    def get_all_intents(self) -> Dict[str, List[IntentStatement]]:
        """Get all intents grouped by category."""
        result: Dict[str, List[IntentStatement]] = {}

        for intent in self._immutable_intents.values():
            result.setdefault(intent.category, []).append(intent)

        for intent in self._intents.values():
            result.setdefault(intent.category, []).append(intent)

        return result

    def get_core_values(self) -> List[str]:
        """Get core values."""
        return [i.statement for i in self._immutable_intents.values()
                if i.category == "value"]

    def get_anti_goals(self) -> List[str]:
        """Get anti-goals."""
        return [i.statement for i in self._immutable_intents.values()
                if i.category == "anti_goal"]

    def get_principles(self) -> List[str]:
        """Get engineering principles."""
        return [i.statement for i in self._immutable_intents.values()
                if i.category == "principle"]

    def is_immutable(self, statement: str, category: str = "principle") -> bool:
        """Check if an intent is immutable."""
        key = f"{category}:{statement}"
        return key in self._immutable_intents

    def get_stats(self) -> Dict[str, Any]:
        """Get intent preservation statistics."""
        return {
            "immutable_intents": len(self._immutable_intents),
            "mutable_intents": len(self._intents),
            "total_intents": len(self._immutable_intents) + len(self._intents),
            "categories": list(set(
                i.category for i in
                list(self._immutable_intents.values()) + list(self._intents.values())
            )),
        }
