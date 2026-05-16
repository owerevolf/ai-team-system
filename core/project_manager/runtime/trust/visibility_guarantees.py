"""
P2 — Visibility Guarantees (Phase 11)

Defines critical event invariants — events that MUST always be surfaced
regardless of calm mode, compression, or any other adaptive behavior.

Key principle: some events are non-negotiable. Period.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class GuaranteeLevel(Enum):
    ALWAYS = "always"           # Shown in ALL modes, never compressed
    CRITICAL = "critical"       # Shown in all modes, can be summarized
    STANDARD = "standard"       # Shown unless in silent mode
    BEST_EFFORT = "best_effort" # Shown when possible


class GuaranteeType(Enum):
    CRITICAL_FAILURE = "critical_failure"
    SECURITY_BOUNDARY = "security_boundary"
    GOVERNANCE_OVERRIDE = "governance_override"
    RECOVERY_FAILURE = "recovery_failure"
    DATA_LOSS_RISK = "data_loss_risk"
    INTEGRITY_VIOLATION = "integrity_violation"
    VALIDATION_COLLAPSE = "validation_collapse"
    IRREVERSIBLE_CHANGE = "irreversible_change"
    APPROVAL_ESCALATION = "approval_escalation"
    TRUST_DEGRADATION = "trust_degradation"


@dataclass
class VisibilityGuarantee:
    """A guarantee that certain events will always be visible."""
    guarantee_type: GuaranteeType
    level: GuaranteeLevel
    description: str
    calm_mode_visible: bool = True
    compressible: bool = False
    batchable: bool = False
    suppressible: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "guarantee_type": self.guarantee_type.value,
            "level": self.level.value,
            "description": self.description,
            "calm_mode_visible": self.calm_mode_visible,
            "compressible": self.compressible,
            "batchable": self.batchable,
            "suppressible": self.suppressible,
        }


# Built-in visibility guarantees — these are NON-NEGOTIABLE
BUILTIN_GUARANTEES: dict[GuaranteeType, VisibilityGuarantee] = {
    GuaranteeType.CRITICAL_FAILURE: VisibilityGuarantee(
        guarantee_type=GuaranteeType.CRITICAL_FAILURE,
        level=GuaranteeLevel.ALWAYS,
        description="Critical failures must always be shown immediately",
        calm_mode_visible=True,
        compressible=False,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.SECURITY_BOUNDARY: VisibilityGuarantee(
        guarantee_type=GuaranteeType.SECURITY_BOUNDARY,
        level=GuaranteeLevel.ALWAYS,
        description="Security boundary violations must always be shown",
        calm_mode_visible=True,
        compressible=False,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.GOVERNANCE_OVERRIDE: VisibilityGuarantee(
        guarantee_type=GuaranteeType.GOVERNANCE_OVERRIDE,
        level=GuaranteeLevel.ALWAYS,
        description="Governance overrides must always be shown",
        calm_mode_visible=True,
        compressible=False,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.RECOVERY_FAILURE: VisibilityGuarantee(
        guarantee_type=GuaranteeType.RECOVERY_FAILURE,
        level=GuaranteeLevel.ALWAYS,
        description="Recovery failures must always be shown",
        calm_mode_visible=True,
        compressible=False,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.DATA_LOSS_RISK: VisibilityGuarantee(
        guarantee_type=GuaranteeType.DATA_LOSS_RISK,
        level=GuaranteeLevel.ALWAYS,
        description="Data loss risks must always be shown",
        calm_mode_visible=True,
        compressible=False,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.INTEGRITY_VIOLATION: VisibilityGuarantee(
        guarantee_type=GuaranteeType.INTEGRITY_VIOLATION,
        level=GuaranteeLevel.ALWAYS,
        description="Integrity violations must always be shown",
        calm_mode_visible=True,
        compressible=False,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.VALIDATION_COLLAPSE: VisibilityGuarantee(
        guarantee_type=GuaranteeType.VALIDATION_COLLAPSE,
        level=GuaranteeLevel.CRITICAL,
        description="Validation system collapse must be shown",
        calm_mode_visible=True,
        compressible=True,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.IRREVERSIBLE_CHANGE: VisibilityGuarantee(
        guarantee_type=GuaranteeType.IRREVERSIBLE_CHANGE,
        level=GuaranteeLevel.ALWAYS,
        description="Irreversible changes must always be shown",
        calm_mode_visible=True,
        compressible=False,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.APPROVAL_ESCALATION: VisibilityGuarantee(
        guarantee_type=GuaranteeType.APPROVAL_ESCALATION,
        level=GuaranteeLevel.CRITICAL,
        description="Approval escalations must be shown",
        calm_mode_visible=True,
        compressible=False,
        batchable=False,
        suppressible=False,
    ),
    GuaranteeType.TRUST_DEGRADATION: VisibilityGuarantee(
        guarantee_type=GuaranteeType.TRUST_DEGRADATION,
        level=GuaranteeLevel.CRITICAL,
        description="Trust degradation warnings must be shown",
        calm_mode_visible=True,
        compressible=True,
        batchable=False,
        suppressible=False,
    ),
}


class VisibilityGuaranteeEnforcer:
    """
    Enforces visibility guarantees — ensures critical events are always shown.

    Usage:
        enforcer = VisibilityGuaranteeEnforcer()
        assert enforcer.is_guaranteed(GuaranteeType.CRITICAL_FAILURE) is True
        assert enforcer.can_suppress(GuaranteeType.CRITICAL_FAILURE, calm=True) is False
    """

    def __init__(self, custom_guarantees: Optional[dict[GuaranteeType, VisibilityGuarantee]] = None) -> None:
        self._guarantees: dict[GuaranteeType, VisibilityGuarantee] = dict(BUILTIN_GUARANTEES)
        if custom_guarantees:
            self._guarantees.update(custom_guarantees)

    def is_guaranteed(self, guarantee_type: GuaranteeType) -> bool:
        """Check if a guarantee type exists."""
        return guarantee_type in self._guarantees

    def get_guarantee(self, guarantee_type: GuaranteeType) -> Optional[VisibilityGuarantee]:
        """Get a specific guarantee."""
        return self._guarantees.get(guarantee_type)

    def can_compress(self, guarantee_type: GuaranteeType) -> bool:
        """Check if a guaranteed event can be compressed."""
        g = self._guarantees.get(guarantee_type)
        return g.compressible if g else True  # Non-guaranteed: no restriction

    def can_batch(self, guarantee_type: GuaranteeType) -> bool:
        """Check if a guaranteed event can be batched/delayed."""
        g = self._guarantees.get(guarantee_type)
        return g.batchable if g else True

    def can_suppress(self, guarantee_type: GuaranteeType, calm_mode: bool = False) -> bool:
        """Check if a guaranteed event can be suppressed."""
        g = self._guarantees.get(guarantee_type)
        if not g:
            return True  # Non-guaranteed: no restriction
        if g.level == GuaranteeLevel.ALWAYS:
            return False  # ALWAYS level: never suppressible
        if calm_mode and not g.calm_mode_visible:
            return True
        return g.suppressible

    def validate_action(self, guarantee_type: GuaranteeType, action: str,
                        calm_mode: bool = False) -> tuple[bool, str]:
        """
        Validate if an action is allowed for a guaranteed event.
        Returns (allowed, reason).
        """
        g = self._guarantees.get(guarantee_type)
        if not g:
            return True, "No guarantee — no restriction"

        if action == "suppress" and not self.can_suppress(guarantee_type, calm_mode):
            return False, f"GUARANTEE VIOLATION: {g.guarantee_type.value} cannot be suppressed — {g.description}"

        if action == "batch" and not self.can_batch(guarantee_type):
            return False, f"GUARANTEE VIOLATION: {g.guarantee_type.value} cannot be batched — {g.description}"

        if action == "compress" and not self.can_compress(guarantee_type):
            return False, f"GUARANTEE VIOLATION: {g.guarantee_type.value} cannot be compressed — {g.description}"

        return True, "OK"

    def get_all_guarantees(self) -> list[dict[str, Any]]:
        """Get all guarantees as dicts."""
        return [g.to_dict() for g in self._guarantees.values()]

    def get_always_visible(self) -> list[str]:
        """Get list of guarantee types that are ALWAYS visible."""
        return [
            g.guarantee_type.value for g in self._guarantees.values()
            if g.level == GuaranteeLevel.ALWAYS
        ]

    def get_guarantee_summary(self) -> dict[str, Any]:
        """Get summary of all guarantees."""
        by_level: dict[str, int] = {}
        for g in self._guarantees.values():
            by_level[g.level.value] = by_level.get(g.level.value, 0) + 1

        return {
            "total_guarantees": len(self._guarantees),
            "by_level": by_level,
            "always_visible": self.get_always_visible(),
            "guarantees": self.get_all_guarantees(),
        }
