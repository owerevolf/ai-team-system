"""
P7 — Predictable Runtime Personality (Phase 11)

Runtime must have a stable operational identity. Consistent signaling style,
stable alert semantics, predictable interaction rhythm, bounded adaptivity.

Key principle: runtime should feel like a reliable colleague, not a moody assistant.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class SignalingStyle(Enum):
    CONSISTENT = "consistent"   # Same signal always means same thing
    ADAPTIVE = "adaptive"       # Signal meaning can shift with context
    ESCALATING = "escalating"   # Signal intensity increases over time


class AlertSemantics(Enum):
    STABLE = "stable"           # Alert types have fixed meanings
    CONTEXTUAL = "contextual"   # Alert meaning depends on context


@dataclass
class PersonalityBounds:
    """Bounds for runtime personality consistency."""
    # How much can signal frequency vary (0-1, 0 = perfectly stable)
    max_frequency_variance: float = 0.3
    # How much can alert severity drift (0-1, 0 = no drift)
    max_severity_drift: float = 0.2
    # Minimum time between signaling style changes (seconds)
    min_style_stability_seconds: float = 300.0
    # Maximum number of personality changes per hour
    max_changes_per_hour: int = 3
    # Whether alert semantics are fixed
    fixed_alert_semantics: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_frequency_variance": self.max_frequency_variance,
            "max_severity_drift": self.max_severity_drift,
            "min_style_stability_seconds": self.min_style_stability_seconds,
            "max_changes_per_hour": self.max_changes_per_hour,
            "fixed_alert_semantics": self.fixed_alert_semantics,
        }


@dataclass
class PersonalityChange:
    """A recorded change in runtime personality."""
    change_id: str
    aspect: str  # What changed: "frequency", "severity", "style", "semantics"
    old_value: str
    new_value: str
    reason: str
    timestamp: float = 0.0
    user_initiated: bool = False

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "aspect": self.aspect,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "user_initiated": self.user_initiated,
        }


class PredictableRuntimePersonality:
    """
    Ensures runtime has a stable, predictable operational personality.

    Usage:
        personality = PredictableRuntimePersonality()
        assert personality.can_change("frequency") is True
        personality.record_change("frequency", "low", "medium", "User request")
        status = personality.get_personality_status()
    """

    def __init__(self, bounds: Optional[PersonalityBounds] = None) -> None:
        self._bounds = bounds or PersonalityBounds()
        self._changes: list[PersonalityChange] = []
        self._current_state: dict[str, str] = {
            "signaling_style": SignalingStyle.CONSISTENT.value,
            "alert_semantics": AlertSemantics.STABLE.value,
            "frequency": "normal",
            "severity_calibration": "standard",
            "interaction_rhythm": "steady",
        }
        self._last_style_change: float = 0.0

    def can_change(self, aspect: str, new_value: str = "") -> tuple[bool, str]:
        """Check if a personality change is allowed. Returns (allowed, reason)."""
        now = time.time()

        # Check style stability
        if aspect == "signaling_style":
            elapsed = now - self._last_style_change
            if elapsed < self._bounds.min_style_stability_seconds:
                remaining = self._bounds.min_style_stability_seconds - elapsed
                return False, f"Style change too frequent. Wait {remaining:.0f}s more."

        # Check changes per hour
        one_hour_ago = now - 3600
        recent_changes = sum(1 for c in self._changes if c.timestamp > one_hour_ago)
        if recent_changes >= self._bounds.max_changes_per_hour:
            return False, f"Too many personality changes ({recent_changes}/{self._bounds.max_changes_per_hour} per hour)"

        # Check alert semantics
        if aspect == "alert_semantics" and self._bounds.fixed_alert_semantics:
            return False, "Alert semantics are fixed and cannot change"

        return True, "OK"

    def record_change(self, aspect: str, old_value: str, new_value: str,
                      reason: str, user_initiated: bool = False) -> Optional[PersonalityChange]:
        """Record a personality change. Returns None if not allowed."""
        allowed, msg = self.can_change(aspect, new_value)
        if not allowed:
            return None

        import uuid
        change = PersonalityChange(
            change_id=f"pers-{uuid.uuid4().hex[:8]}",
            aspect=aspect,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            user_initiated=user_initiated,
        )
        self._changes.append(change)
        self._current_state[aspect] = new_value

        if aspect == "signaling_style":
            self._last_style_change = change.timestamp

        return change

    def get_current_state(self) -> dict[str, str]:
        """Get current personality state."""
        return dict(self._current_state)

    def get_changes(self, limit: int = 20) -> list[PersonalityChange]:
        """Get recent personality changes."""
        sorted_changes = sorted(self._changes, key=lambda c: c.timestamp, reverse=True)
        return sorted_changes[:limit]

    def get_personality_status(self) -> dict[str, Any]:
        """Get personality stability status."""
        now = time.time()
        one_hour_ago = now - 3600
        recent_changes = [c for c in self._changes if c.timestamp > one_hour_ago]

        # Check stability
        is_stable = len(recent_changes) < self._bounds.max_changes_per_hour
        style_stable = (now - self._last_style_change) >= self._bounds.min_style_stability_seconds

        return {
            "current_state": self._current_state,
            "is_stable": is_stable and style_stable,
            "recent_changes_count": len(recent_changes),
            "max_changes_per_hour": self._bounds.max_changes_per_hour,
            "style_stable": style_stable,
            "bounds": self._bounds.to_dict(),
        }

    def get_stability_score(self) -> float:
        """Compute personality stability score (0-100)."""
        now = time.time()
        one_hour_ago = now - 3600
        recent_changes = sum(1 for c in self._changes if c.timestamp > one_hour_ago)

        score = 100.0
        score -= recent_changes * 15  # Each change reduces score
        if not self._bounds.fixed_alert_semantics:
            score -= 20  # Unstable alert semantics
        return max(0.0, score)
