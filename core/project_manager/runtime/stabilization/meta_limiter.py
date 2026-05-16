"""
Phase 16, P8: Meta-System Limiter

Detects and prevents recursive governance:
- systems that manage systems that manage systems
- meta-observability layers
- orchestration-over-orchestration
- policy-for-policy systems

Principle: Stop expansion early. Anti-enterprise-monster mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MetaLevel(Enum):
    CORE = "core"                  # Direct runtime functionality
    GOVERNANCE = "governance"      # Governs core
    META_GOVERNANCE = "meta"       # Governs governance
    META_META = "meta_meta"        # Governs meta-governance — DANGEROUS


class LimiterAction(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class MetaSystemCheck:
    """Result of a meta-system check."""
    name: str
    meta_level: MetaLevel
    action: LimiterAction
    reason: str


class MetaSystemLimiter:
    """
    Prevents recursive governance and meta-system explosion.
    Keeps the system from becoming a bureaucracy of systems.
    """

    # Maximum allowed meta-level
    MAX_META_LEVEL: MetaLevel = MetaLevel.META_GOVERNANCE

    # Known meta-system patterns to watch for
    DANGEROUS_PATTERNS: list[dict] = [
        {
            "name": "governance_for_governance",
            "description": "A system that governs how governance systems are governed",
            "level": MetaLevel.META_META,
            "action": LimiterAction.BLOCK,
        },
        {
            "name": "observability_for_observability",
            "description": "Meta-observability that observes the observability system",
            "level": MetaLevel.META_META,
            "action": LimiterAction.BLOCK,
        },
        {
            "name": "orchestration_for_orchestration",
            "description": "Orchestrator that manages orchestrators",
            "level": MetaLevel.META_META,
            "action": LimiterAction.BLOCK,
        },
        {
            "name": "policy_for_policies",
            "description": "Policy system that manages other policy systems",
            "level": MetaLevel.META_META,
            "action": LimiterAction.BLOCK,
        },
        {
            "name": "compression_for_compression",
            "description": "System that compresses compression systems",
            "level": MetaLevel.META_META,
            "action": LimiterAction.BLOCK,
        },
    ]

    def __init__(self) -> None:
        self._patterns: dict[str, dict] = {
            p["name"]: p for p in self.DANGEROUS_PATTERNS
        }

    def check_system(self, name: str, meta_level: MetaLevel) -> MetaSystemCheck:
        """Check if a system at a given meta-level should be allowed."""
        if meta_level == MetaLevel.META_META:
            return MetaSystemCheck(
                name=name,
                meta_level=meta_level,
                action=LimiterAction.BLOCK,
                reason=(
                    f"System '{name}' is at META_META level. "
                    f"This is the maximum allowed level. "
                    f"Consider flattening the architecture instead."
                ),
            )
        elif meta_level == MetaLevel.META_GOVERNANCE:
            return MetaSystemCheck(
                name=name,
                meta_level=meta_level,
                action=LimiterAction.WARN,
                reason=(
                    f"System '{name}' is at META_GOVERNANCE level. "
                    f"This is acceptable but watch for further expansion."
                ),
            )
        else:
            return MetaSystemCheck(
                name=name,
                meta_level=meta_level,
                action=LimiterAction.ALLOW,
                reason=f"System '{name}' is at {meta_level.value} level — acceptable.",
            )

    def check_pattern(self, pattern_name: str) -> Optional[MetaSystemCheck]:
        """Check if a known dangerous pattern is being used."""
        pattern = self._patterns.get(pattern_name)
        if not pattern:
            return None
        return MetaSystemCheck(
            name=pattern_name,
            meta_level=pattern["level"],
            action=pattern["action"],
            reason=pattern["description"],
        )

    def get_dangerous_patterns(self) -> list[str]:
        """Get list of dangerous meta-system patterns."""
        return list(self._patterns.keys())

    @property
    def max_meta_level(self) -> MetaLevel:
        return self.MAX_META_LEVEL
