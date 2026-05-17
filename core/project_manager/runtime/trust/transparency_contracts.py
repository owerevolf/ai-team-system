"""
P1 — Transparency Contracts (Phase 11)

Defines explicit contracts for what runtime CAN and CANNOT hide.
Every adaptive behavior (compression, suppression, batching, delay)
must be governed by a visible, inspectable contract.

Key principle: runtime must never silently hide what it promised to show.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class VisibilityAction(Enum):
    SHOW = "show"           # Always surface immediately
    SUMMARIZE = "summarize" # Can compress into summary
    DELAY = "delay"         # Can batch/defer
    SUPPRESS = "suppress"   # Can hide in calm mode only


class EventCategory(Enum):
    INTEGRITY_FAILURE = "integrity_failure"
    GOVERNANCE_VIOLATION = "governance_violation"
    VALIDATION_FAILURE = "validation_failure"
    SECURITY_IMPACT = "security_impact"
    IRREVERSIBLE_OP = "irreversible_op"
    RECOVERY_FAILURE = "recovery_failure"
    DATA_LOSS_RISK = "data_loss_risk"
    CRITICAL_ERROR = "critical_error"
    REPETITIVE_TELEMETRY = "repetitive_telemetry"
    DUPLICATE_TRACE = "duplicate_trace"
    LOW_RISK_CONFIRM = "low_risk_confirm"
    BACKGROUND_INDEXING = "background_indexing"
    LOW_PRIORITY_SUGGESTION = "low_priority_suggestion"
    NON_BLOCKING_OPT = "non_blocking_optimization"
    INFO_DIAGNOSTIC = "informational_diagnostic"
    PROGRESS_UPDATE = "progress_update"
    SUCCESS_CONFIRM = "success_confirm"


# Default transparency contract — what runtime promises
DEFAULT_TRANSPARENCY_CONTRACT: dict[EventCategory, VisibilityAction] = {
    # NEVER HIDE — always shown immediately
    EventCategory.INTEGRITY_FAILURE: VisibilityAction.SHOW,
    EventCategory.GOVERNANCE_VIOLATION: VisibilityAction.SHOW,
    EventCategory.VALIDATION_FAILURE: VisibilityAction.SHOW,
    EventCategory.SECURITY_IMPACT: VisibilityAction.SHOW,
    EventCategory.IRREVERSIBLE_OP: VisibilityAction.SHOW,
    EventCategory.RECOVERY_FAILURE: VisibilityAction.SHOW,
    EventCategory.DATA_LOSS_RISK: VisibilityAction.SHOW,
    EventCategory.CRITICAL_ERROR: VisibilityAction.SHOW,
    # CAN SUMMARIZE — compressible but visible
    EventCategory.REPETITIVE_TELEMETRY: VisibilityAction.SUMMARIZE,
    EventCategory.DUPLICATE_TRACE: VisibilityAction.SUMMARIZE,
    EventCategory.LOW_RISK_CONFIRM: VisibilityAction.SUMMARIZE,
    EventCategory.BACKGROUND_INDEXING: VisibilityAction.SUMMARIZE,
    # CAN DELAY — batchable
    EventCategory.LOW_PRIORITY_SUGGESTION: VisibilityAction.DELAY,
    EventCategory.NON_BLOCKING_OPT: VisibilityAction.DELAY,
    EventCategory.INFO_DIAGNOSTIC: VisibilityAction.DELAY,
    # CAN SUPPRESS — hideable in calm mode
    EventCategory.PROGRESS_UPDATE: VisibilityAction.SUPPRESS,
    EventCategory.SUCCESS_CONFIRM: VisibilityAction.SUPPRESS,
}


@dataclass
class TransparencyRule:
    """A single transparency rule for an event category."""
    category: EventCategory
    action: VisibilityAction
    reason: str = ""
    user_overridable: bool = True
    calm_mode_override: Optional[VisibilityAction] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "action": self.action.value,
            "reason": self.reason,
            "user_overridable": self.user_overridable,
            "calm_mode_override": self.calm_mode_override.value if self.calm_mode_override else None,
        }


@dataclass
class TransparencyContractViolation:
    """Recorded when runtime breaks a transparency contract."""
    violation_id: str
    category: EventCategory
    expected_action: VisibilityAction
    actual_action: VisibilityAction
    event_id: str
    timestamp: float = 0.0
    resolved: bool = False

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "category": self.category.value,
            "expected_action": self.expected_action.value,
            "actual_action": self.actual_action.value,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
        }


class TransparencyContractManager:
    """
    Manages transparency contracts — what runtime can/cannot hide.

    Usage:
        mgr = TransparencyContractManager()
        action = mgr.resolve_action(EventCategory.CRITICAL_ERROR)
        assert action == VisibilityAction.SHOW  # Never hidden

        mgr.override(EventCategory.PROGRESS_UPDATE, VisibilityAction.SHOW)
        violations = mgr.get_violations()
    """

    def __init__(self, custom_rules: Optional[dict[EventCategory, VisibilityAction]] = None) -> None:
        self._rules: dict[EventCategory, TransparencyRule] = {}
        self._violations: list[TransparencyContractViolation] = []

        # Initialize with defaults
        for cat, action in DEFAULT_TRANSPARENCY_CONTRACT.items():
            self._rules[cat] = TransparencyRule(
                category=cat,
                action=action,
                reason=f"Default contract for {cat.value}",
            )

        # Apply custom overrides
        if custom_rules:
            for cat, action in custom_rules.items():
                self._rules[cat] = TransparencyRule(
                    category=cat,
                    action=action,
                    reason=f"Custom override for {cat.value}",
                )

    def resolve_action(self, category: EventCategory, calm_mode: bool = False) -> VisibilityAction:
        """Resolve what action is allowed for an event category."""
        rule = self._rules.get(category)
        if not rule:
            return VisibilityAction.SHOW  # Unknown categories: always show

        if calm_mode and rule.calm_mode_override:
            return rule.calm_mode_override

        return rule.action

    def can_hide(self, category: EventCategory, calm_mode: bool = False) -> bool:
        """Check if an event category can be hidden."""
        action = self.resolve_action(category, calm_mode)
        # SUPPRESS can only hide in calm mode
        if action == VisibilityAction.SUPPRESS:
            return calm_mode
        return False

    def can_summarize(self, category: EventCategory) -> bool:
        """Check if an event category can be summarized."""
        action = self.resolve_action(category)
        return action in (VisibilityAction.SUMMARIZE, VisibilityAction.DELAY, VisibilityAction.SUPPRESS)

    def can_delay(self, category: EventCategory) -> bool:
        """Check if an event category can be delayed/batched."""
        action = self.resolve_action(category)
        return action in (VisibilityAction.DELAY, VisibilityAction.SUPPRESS)

    def override(self, category: EventCategory, action: VisibilityAction, reason: str = "") -> bool:
        """Override a transparency rule. Returns False if not overridable."""
        rule = self._rules.get(category)
        if rule and not rule.user_overridable:
            return False
        self._rules[category] = TransparencyRule(
            category=category,
            action=action,
            reason=reason or "User override",
            user_overridable=True,
        )
        return True

    def set_calm_override(self, category: EventCategory, action: VisibilityAction) -> None:
        """Set calm-mode specific override for a category."""
        rule = self._rules.get(category)
        if rule:
            rule.calm_mode_override = action

    def record_violation(self, category: EventCategory, expected: VisibilityAction,
                        actual: VisibilityAction, event_id: str) -> TransparencyContractViolation:
        """Record a transparency contract violation."""
        import uuid
        violation = TransparencyContractViolation(
            violation_id=f"viol-{uuid.uuid4().hex[:8]}",
            category=category,
            expected_action=expected,
            actual_action=actual,
            event_id=event_id,
        )
        self._violations.append(violation)
        return violation

    def get_violations(self, unresolved_only: bool = False) -> list[TransparencyContractViolation]:
        """Get transparency contract violations."""
        if unresolved_only:
            return [v for v in self._violations if not v.resolved]
        return list(self._violations)

    def get_contract_summary(self) -> dict[str, Any]:
        """Get full contract summary."""
        by_action: dict[str, list[str]] = {}
        for cat, rule in self._rules.items():
            action = rule.action.value
            by_action.setdefault(action, []).append(cat.value)

        return {
            "total_rules": len(self._rules),
            "by_action": by_action,
            "total_violations": len(self._violations),
            "unresolved_violations": sum(1 for v in self._violations if not v.resolved),
            "rules": {cat.value: rule.to_dict() for cat, rule in self._rules.items()},
        }

    def get_never_hide_list(self) -> list[str]:
        """Get list of event categories that can never be hidden."""
        return [
            cat.value for cat, rule in self._rules.items()
            if rule.action == VisibilityAction.SHOW
        ]
