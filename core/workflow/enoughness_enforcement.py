"""
enoughness_enforcement.py — Enoughness Enforcement.

The most important module of Phase 21.

Purpose: Stop unnecessary system growth.
Every new idea must pass the enoughness check.

Critical rule: NEW MODULES MUST BECOME RARE.

Blocks:
- orchestration bloat
- subsystem inflation
- AGI drift
- enterprise creep
- unnecessary abstractions
- recursive complexity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EnoughnessCheck:
    """Result of an enoughness check."""
    idea: str
    passed: bool
    score: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class EnoughnessEnforcement:
    """
    Enforces enoughness — stops unnecessary growth.
    Every new feature/module must pass this check.
    """

    # Questions that must be answered YES for any new addition
    ESSENTIAL_QUESTIONS = [
        "does_it_reduce_friction",
        "does_it_improve_survivability",
        "does_it_improve_usability",
        "does_it_improve_learning",
        "does_it_improve_maintainability",
    ]

    # Red flags that automatically block
    RED_FLAGS = [
        "autonomous agent",
        "recursive orchestration",
        "self-modifying",
        "AGI planning",
        "hidden execution",
        "auto architecture",
        "enterprise SaaS",
        "multi-tenant",
        "billing system",
        "user management",
        "team collaboration",
        "real-time sync",
        "blockchain",
        "machine learning model",
        "neural network",
        "deep learning",
    ]

    # Complexity budget — max new modules per phase
    MAX_NEW_MODULES_PER_PHASE = 3

    def __init__(self):
        self._phase_modules: Dict[str, List[str]] = {}
        self._checks: List[EnoughnessCheck] = []

    def check_idea(self, idea: str, context: Optional[Dict[str, Any]] = None) -> EnoughnessCheck:
        """
        Check if a new idea should be implemented.

        Returns EnoughnessCheck with passed=True if the idea is worth pursuing.
        """
        context = context or {}
        reasons = []
        suggestions = []
        score = 0.0

        # Check red flags
        idea_lower = idea.lower()
        for flag in self.RED_FLAGS:
            if flag in idea_lower:
                reasons.append(f"RED FLAG: '{flag}' detected")
                score -= 0.3

        # Check essential questions
        for question in self.ESSENTIAL_QUESTIONS:
            answer = context.get(question, False)
            if answer:
                score += 0.2
                reasons.append(f"PASS: {question}")
            else:
                reasons.append(f"FAIL: {question}")
                suggestions.append(f"Consider how this {question.replace('does_it_', '')}")

        # Normalize score: start at 0.3, each YES adds 0.2, max 1.0
        score = min(1.0, score + 0.3)

        # Check complexity budget
        phase = context.get("phase", "current")
        current_modules = self._phase_modules.get(phase, [])
        if len(current_modules) >= self.MAX_NEW_MODULES_PER_PHASE:
            reasons.append(f"Complexity budget exceeded: {len(current_modules)}/{self.MAX_NEW_MODULES_PER_PHASE} modules this phase")
            score -= 0.5
            suggestions.append("Wait for next phase or replace an existing module")

        # Final score
        score = max(0.0, min(1.0, score))

        passed = score >= 0.6 and not any("RED FLAG" in r for r in reasons)

        check = EnoughnessCheck(
            idea=idea, passed=passed, score=score,
            reasons=reasons, suggestions=suggestions,
        )
        self._checks.append(check)

        return check

    def register_module(self, phase: str, module_name: str) -> None:
        """Register a new module for a phase."""
        if phase not in self._phase_modules:
            self._phase_modules[phase] = []
        self._phase_modules[phase].append(module_name)

    def get_phase_stats(self, phase: str = "current") -> Dict[str, Any]:
        """Get enoughness stats for a phase."""
        modules = self._phase_modules.get(phase, [])
        phase_checks = [c for c in self._checks if phase in c.idea.lower()]
        passed = sum(1 for c in phase_checks if c.passed)

        return {
            "phase": phase,
            "modules_created": len(modules),
            "modules_remaining": max(0, self.MAX_NEW_MODULES_PER_PHASE - len(modules)),
            "ideas_checked": len(phase_checks),
            "ideas_passed": passed,
            "ideas_blocked": len(phase_checks) - passed,
            "budget_exhausted": len(modules) >= self.MAX_NEW_MODULES_PER_PHASE,
        }

    def get_all_checks(self) -> List[EnoughnessCheck]:
        """Get all enoughness checks."""
        return list(self._checks)

    def should_stop(self, phase: str = "current") -> Tuple[bool, str]:
        """
        Check if the system should stop growing.

        Returns (should_stop, reason).
        """
        stats = self.get_phase_stats(phase)

        if stats["budget_exhausted"]:
            return True, f"Complexity budget exhausted: {stats['modules_created']}/{self.MAX_NEW_MODULES_PER_PHASE} modules"

        if stats["ideas_blocked"] > stats["ideas_passed"] * 2 and stats["ideas_checked"] > 5:
            return True, f"Too many ideas blocked: {stats['ideas_blocked']} blocked vs {stats['ideas_passed']} passed"

        return False, "System growth is healthy"
