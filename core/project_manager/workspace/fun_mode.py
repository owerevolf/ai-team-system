"""
Keep It Fun Module (P20) — Phase 8

Ensures the project stays interesting, experimental, educational,
hacker-friendly, and approachable.

Anti-goals:
  - NOT a corporate nightmare
  - NOT an enterprise bureaucracy simulator
  - NOT an over-governed platform monster

The system should feel like a helpful tool, not a burden.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Fun touches: Easter eggs, tips, encouragements
# ---------------------------------------------------------------------------

# Shown after successful operations
SUCCESS_MESSAGES = [
    "Done! Your project thanks you.",
    "All clean. Like a fresh git init.",
    "Fixed! That wasn't so bad, was it?",
    "Ship it! (after testing, of course)",
    "Another one bites the dust. Bugs: 0, You: 1",
    "Clean code, clear mind.",
    "Refactoring complete. Your future self will thank you.",
    "That's the spirit! Keep shipping.",
    "Nice work. The code is happier now.",
    "Operation successful. No computers were harmed.",
]

# Shown when things go wrong (to lighten the mood)
FAILURE_MESSAGES = [
    "Well, that didn't work. But we'll figure it out.",
    "Houston, we have a problem. But it's fixable.",
    "That's not a bug, it's an undocumented feature. Wait, no, it's a bug.",
    "Don't worry. Every great developer breaks things daily.",
    "This is fine. (It's actually fine, we have rollback.)",
    "Error? What error? Oh, that one. Let's fix it.",
    "The code is testing your patience. Stay strong.",
    "Plot twist: the code had other plans. Let's redirect.",
]

# Shown during long operations
WAIT_MESSAGES = [
    "Working on this... good things take time.",
    "Analyzing... (this is the thinking part)",
    "Crunching code... almost there.",
    "Reading files... so many files.",
    "Building the plan... strategy is important.",
    "Scanning... looking for trouble.",
    "Processing... the machines are working.",
    "Hold on... doing the thing.",
]

# Educational tips shown occasionally
DEV_TIPS = [
    "Tip: Small commits are easier to rollback. Commit early, commit often.",
    "Tip: Write tests before fixing bugs. It's like setting a trap.",
    "Tip: Read the error message. It usually tells you what's wrong.",
    "Tip: git diff before git commit. Always.",
    "Tip: If it works, don't touch it. If it doesn't, write a test first.",
    "Tip: Rubber duck debugging works. Explain the problem to a duck.",
    "Tip: Take breaks. Fresh eyes catch bugs faster.",
    "Tip: Read other people's code. You'll learn new patterns.",
    "Tip: Keep a dev journal. Future you will be grateful.",
    "Tip: Automate repetitive tasks. That's what computers are for.",
    "Tip: Learn your keyboard shortcuts. Your mouse is slow.",
    "Tip: Comment WHY, not WHAT. The code shows what.",
    "Tip: One thing at a time. Multitasking is a myth.",
    "Tip: Sleep on hard problems. Your brain works while you rest.",
    "Tip: It's okay to delete code. Less code = less bugs.",
]

# Fun facts about the system
SYSTEM_FACTS = [
    "This system has processed thousands of files without complaining.",
    "The PM never sleeps. It's always ready to help.",
    "Your project is one of a kind. Just like every other project.",
    "The sandbox has saved countless projects from accidental damage.",
    "Every rollback is a lesson learned. Or a mistake repeated.",
    "The traceability log remembers everything. Even that typo from 3am.",
    "The health dashboard judges your code. But it's a friendly judge.",
    "This system runs on electricity and determination.",
]


@dataclass
class FunConfig:
    """Configuration for fun mode."""
    enabled: bool = True
    show_success_messages: bool = True
    show_failure_messages: bool = True
    show_wait_messages: bool = True
    show_tips: bool = True
    show_facts: bool = False
    tip_frequency: float = 0.3     # 0-1, how often to show tips
    message_style: str = "friendly"  # friendly | minimal | hacker

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "show_success_messages": self.show_success_messages,
            "show_failure_messages": self.show_failure_messages,
            "show_wait_messages": self.show_wait_messages,
            "show_tips": self.show_tips,
            "show_facts": self.show_facts,
            "tip_frequency": self.tip_frequency,
            "message_style": self.message_style,
        }


class FunMode:
    """
    Manages the fun/approachable aspects of the system.

    Usage:
        fun = FunMode()
        msg = fun.get_success_message()
        tip = fun.get_tip()
    """

    def __init__(self, config: Optional[FunConfig] = None) -> None:
        self.config = config or FunConfig()

    def get_success_message(self) -> str:
        """Get a random success message."""
        if not self.config.enabled or not self.config.show_success_messages:
            return "Done."
        return random.choice(SUCCESS_MESSAGES)

    def get_failure_message(self) -> str:
        """Get a random failure-comfort message."""
        if not self.config.enabled or not self.config.show_failure_messages:
            return "Something went wrong."
        return random.choice(FAILURE_MESSAGES)

    def get_wait_message(self) -> str:
        """Get a random wait message."""
        if not self.config.enabled or not self.config.show_wait_messages:
            return "Working..."
        return random.choice(WAIT_MESSAGES)

    def get_tip(self) -> str:
        """Get a random development tip (based on frequency)."""
        if not self.config.enabled or not self.config.show_tips:
            return ""
        if random.random() < self.config.tip_frequency:
            return random.choice(DEV_TIPS)
        return ""

    def get_fact(self) -> str:
        """Get a random system fact."""
        if not self.config.enabled or not self.config.show_facts:
            return ""
        return random.choice(SYSTEM_FACTS)

    def format_success(self, operation: str, details: str = "") -> str:
        """Format a success message for display."""
        msg = self.get_success_message()
        parts = [f"  {msg}", f"  Operation: {operation}"]
        if details:
            parts.append(f"  {details}")
        tip = self.get_tip()
        if tip:
            parts.append(f"  {tip}")
        return "\n".join(parts)

    def format_failure(self, operation: str, error: str = "") -> str:
        """Format a failure message for display."""
        msg = self.get_failure_message()
        parts = [f"  {msg}", f"  Operation: {operation}"]
        if error:
            parts.append(f"  Error: {error}")
        parts.append("  Don't worry — we can fix this.")
        return "\n".join(parts)

    def format_wait(self, operation: str) -> str:
        """Format a wait message for display."""
        msg = self.get_wait_message()
        return f"  {msg}\n  ({operation})"

    def get_fun_status(self) -> dict[str, Any]:
        """Get the current fun mode status."""
        return {
            "fun_mode": self.config.enabled,
            "config": self.config.to_dict(),
            "available_messages": {
                "success": len(SUCCESS_MESSAGES),
                "failure": len(FAILURE_MESSAGES),
                "wait": len(WAIT_MESSAGES),
                "tips": len(DEV_TIPS),
                "facts": len(SYSTEM_FACTS),
            },
        }
