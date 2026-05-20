"""
complexity_gate.py — Final Complexity Gate.

Purpose: Stop the system from becoming a monster-platform.
This is the LAST line of defense against complexity creep.

Blocks:
- enterprise drift
- AGI drift
- orchestration addiction
- subsystem inflation
- recursive abstractions
- unnecessary automation

Allows ONLY what:
- improves usability
- improves trust
- improves survivability
- improves learning
- improves repairability
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class GateDecision:
    """Decision from the complexity gate."""
    idea: str
    allowed: bool
    score: float  # 0.0 to 1.0
    category: str = ""  # trust, usability, survivability, learning, repairability, blocked
    reasons: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ComplexityGate:
    """
    Final complexity gate.
    Last line of defense against complexity creep.
    """

    # Absolute blocks — never allowed
    ABSOLUTE_BLOCKS = [
        "autonomous coding swarm",
        "recursive self-improvement",
        "hidden execution",
        "self-rewriting architecture",
        "agi planning core",
        "cloud lock-in",
        "enterprise permission system",
        "auto merge to main",
        "multi-tenant",
        "billing system",
        "user management system",
        "team collaboration platform",
        "real-time sync",
        "blockchain",
        "neural network training",
        "deep learning model",
        "large language model fine-tuning",
        "vector database",
        "embedding service",
        "kubernetes deployment",
        "microservices architecture",
        "event sourcing",
        "cqrs",
        "graphql federation",
        "oauth provider",
        "sso integration",
        "audit logging system",
        "compliance framework",
        "data pipeline",
        "etl process",
        "data warehouse",
        "analytics dashboard",
        "a/b testing",
        "feature flags",
        "canary deployment",
        "blue-green deployment",
    ]

    # Categories that are allowed (with scrutiny)
    ALLOWED_CATEGORIES = [
        "trust",
        "usability",
        "survivability",
        "learning",
        "repairability",
    ]

    # Maximum counts per category
    MAX_MODULES = {
        "total": 350,  # Hard limit on total modules
        "per_phase": 5,  # Max new modules per phase
        "per_category": 50,  # Max modules per category
    }

    def __init__(self):
        self._decisions: List[GateDecision] = []
        self._module_count = 0
        self._phase_modules: Dict[str, int] = {}

    def evaluate(self, idea: str, category: str = "",
                  context: Optional[Dict[str, Any]] = None) -> GateDecision:
        """
        Evaluate a new idea against the complexity gate.

        Returns GateDecision with allowed=True only if the idea passes all checks.
        """
        context = context or {}
        reasons = []
        suggestions = []
        score = 0.5  # Start neutral

        # Check absolute blocks
        idea_lower = idea.lower()
        for block in self.ABSOLUTE_BLOCKS:
            if block in idea_lower:
                reasons.append(f"BLOCKED: '{block}' is absolutely prohibited")
                score = 0.0
                return GateDecision(
                    idea=idea, allowed=False, score=0.0,
                    category="blocked", reasons=reasons,
                    suggestions=["This type of feature is not aligned with project goals"],
                )

        # Check category
        if category and category in self.ALLOWED_CATEGORIES:
            score += 0.2
            reasons.append(f"Category '{category}' is allowed")
        elif category:
            score -= 0.1
            reasons.append(f"Category '{category}' is not in allowed list")
            suggestions.append(f"Consider categorizing as one of: {', '.join(self.ALLOWED_CATEGORIES)}")

        # Check module budget
        phase = context.get("phase", "current")
        phase_count = self._phase_modules.get(phase, 0)
        if phase_count >= self.MAX_MODULES["per_phase"]:
            reasons.append(f"Phase budget exceeded: {phase_count}/{self.MAX_MODULES['per_phase']}")
            score -= 0.3
            suggestions.append("Wait for next phase or refactor existing module")
        else:
            score += 0.1
            reasons.append(f"Phase budget OK: {phase_count}/{self.MAX_MODULES['per_phase']}")

        # Check total module count
        if self._module_count >= self.MAX_MODULES["total"]:
            reasons.append(f"Total module limit reached: {self._module_count}/{self.MAX_MODULES['total']}")
            score -= 0.5
            suggestions.append("Remove unused modules before adding new ones")
        else:
            score += 0.1

        # Check value alignment
        value_score = self._check_value_alignment(idea, context)
        score += value_score
        if value_score > 0:
            reasons.append("Aligns with project values")
        elif value_score < 0:
            reasons.append("Does not clearly align with project values")
            suggestions.append("Explain how this improves trust, usability, survivability, learning, or repairability")

        # Normalize
        score = max(0.0, min(1.0, score))

        allowed = score >= 0.6 and not any("BLOCKED" in r for r in reasons)

        decision = GateDecision(
            idea=idea, allowed=allowed, score=score,
            category=category, reasons=reasons, suggestions=suggestions,
        )
        self._decisions.append(decision)

        if not allowed:
            logger.warning(f"Complexity gate blocked: {idea} (score: {score:.2f})")

        return decision

    def _check_value_alignment(self, idea: str, context: Dict[str, Any]) -> float:
        """Check if the idea aligns with project values."""
        score = 0.0
        idea_lower = idea.lower()

        # Positive signals
        positive_signals = [
            ("simplify", 0.2), ("reduce", 0.1), ("clarify", 0.2),
            ("explain", 0.2), ("repair", 0.2), ("recover", 0.2),
            ("calm", 0.2), ("quiet", 0.1), ("clean", 0.1),
            ("understand", 0.2), ("trust", 0.2), ("safe", 0.2),
            ("beginner", 0.1), ("learn", 0.1), ("teach", 0.1),
        ]

        for signal, value in positive_signals:
            if signal in idea_lower:
                score += value

        # Negative signals
        negative_signals = [
            ("automate", -0.1), ("autonomous", -0.3), ("ai", -0.05),
            ("smart", -0.05), ("intelligent", -0.05), ("platform", -0.2),
            ("enterprise", -0.3), ("scale", -0.1), ("distributed", -0.2),
            ("cloud", -0.1), ("microservice", -0.2), ("blockchain", -0.3),
        ]

        for signal, value in negative_signals:
            if signal in idea_lower:
                score += value

        return max(-0.5, min(0.5, score))

    def register_module(self, phase: str = "current") -> None:
        """Register a new module."""
        self._module_count += 1
        self._phase_modules[phase] = self._phase_modules.get(phase, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get gate statistics."""
        return {
            "total_modules": self._module_count,
            "total_limit": self.MAX_MODULES["total"],
            "remaining": max(0, self.MAX_MODULES["total"] - self._module_count),
            "phase_modules": dict(self._phase_modules),
            "total_decisions": len(self._decisions),
            "allowed": sum(1 for d in self._decisions if d.allowed),
            "blocked": sum(1 for d in self._decisions if not d.allowed),
        }

    def get_decisions(self, limit: int = 20) -> List[GateDecision]:
        """Get recent decisions."""
        return self._decisions[-limit:]

    def is_healthy(self) -> Tuple[bool, str]:
        """Check if the system is healthy."""
        stats = self.get_stats()

        if stats["total_modules"] >= stats["total_limit"] * 0.9:
            return False, f"Module count critical: {stats['total_modules']}/{stats['total_limit']}"

        if stats["blocked"] > stats["allowed"] * 3 and stats["total_decisions"] > 10:
            return False, f"Too many blocked ideas: {stats['blocked']} vs {stats['allowed']}"

        return True, "System is healthy"
