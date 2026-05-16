"""
P4 — User-Controlled Adaptivity (Phase 11)

Adaptivity is NOT invisible intelligence. It's adjustable operational policy.
User chooses the mode, runtime adapts within bounded constraints.

Key principle: user controls the knobs, runtime stays within bounds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class AdaptivityProfile(Enum):
    BEGINNER = "beginner"
    FOCUSED = "focused"
    EXPERT = "expert"
    RECOVERY = "recovery"


@dataclass
class AdaptivitySettings:
    """Settings for a given adaptivity profile."""
    # Compression
    compression_level: str = "standard"  # minimal | standard | detailed
    # Calm mode
    calm_level: str = "calm"  # full | reduced | calm | silent
    # Attention
    max_attention_items: int = 10
    group_similar: bool = True
    # Approval
    auto_apply_low_risk: bool = False
    batch_approvals: bool = True
    # Noise reduction
    dedup_enabled: bool = True
    suppress_repetitive: bool = True
    # Explanations
    explanation_level: str = "summary"  # summary | reasoning | full_trace
    # Focus
    focus_blocks_enabled: bool = True
    batch_interruptions: bool = True
    # Transparency
    show_adaptation_decisions: bool = True
    show_hidden_count: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "compression_level": self.compression_level,
            "calm_level": self.calm_level,
            "max_attention_items": self.max_attention_items,
            "group_similar": self.group_similar,
            "auto_apply_low_risk": self.auto_apply_low_risk,
            "batch_approvals": self.batch_approvals,
            "dedup_enabled": self.dedup_enabled,
            "suppress_repetitive": self.suppress_repetitive,
            "explanation_level": self.explanation_level,
            "focus_blocks_enabled": self.focus_blocks_enabled,
            "batch_interruptions": self.batch_interruptions,
            "show_adaptation_decisions": self.show_adaptation_decisions,
            "show_hidden_count": self.show_hidden_count,
        }


# Built-in profiles — these are SAFE DEFAULTS, not hidden intelligence
PROFILE_SETTINGS: dict[AdaptivityProfile, AdaptivitySettings] = {
    AdaptivityProfile.BEGINNER: AdaptivitySettings(
        compression_level="minimal",
        calm_level="reduced",
        max_attention_items=5,
        group_similar=True,
        auto_apply_low_risk=False,
        batch_approvals=False,
        dedup_enabled=True,
        suppress_repetitive=False,
        explanation_level="reasoning",
        focus_blocks_enabled=False,
        batch_interruptions=False,
        show_adaptation_decisions=True,
        show_hidden_count=True,
    ),
    AdaptivityProfile.FOCUSED: AdaptivitySettings(
        compression_level="standard",
        calm_level="calm",
        max_attention_items=10,
        group_similar=True,
        auto_apply_low_risk=True,
        batch_approvals=True,
        dedup_enabled=True,
        suppress_repetitive=True,
        explanation_level="summary",
        focus_blocks_enabled=True,
        batch_interruptions=True,
        show_adaptation_decisions=False,
        show_hidden_count=True,
    ),
    AdaptivityProfile.EXPERT: AdaptivitySettings(
        compression_level="detailed",
        calm_level="full",
        max_attention_items=50,
        group_similar=False,
        auto_apply_low_risk=False,
        batch_approvals=False,
        dedup_enabled=False,
        suppress_repetitive=False,
        explanation_level="full_trace",
        focus_blocks_enabled=False,
        batch_interruptions=False,
        show_adaptation_decisions=True,
        show_hidden_count=True,
    ),
    AdaptivityProfile.RECOVERY: AdaptivitySettings(
        compression_level="detailed",
        calm_level="full",
        max_attention_items=20,
        group_similar=False,
        auto_apply_low_risk=False,
        batch_approvals=False,
        dedup_enabled=False,
        suppress_repetitive=False,
        explanation_level="full_trace",
        focus_blocks_enabled=False,
        batch_interruptions=False,
        show_adaptation_decisions=True,
        show_hidden_count=True,
    ),
}


class UserControlledAdaptivity:
    """
    Manages user-controlled adaptivity profiles.

    Usage:
        ctrl = UserControlledAdaptivity(AdaptivityProfile.BEGINNER)
        settings = ctrl.get_settings()
        ctrl.set_profile(AdaptivityProfile.FOCUSED)
        ctrl.customize("compression_level", "minimal")
    """

    def __init__(self, profile: AdaptivityProfile = AdaptivityProfile.BEGINNER) -> None:
        self._profile = profile
        self._settings = AdaptivitySettings(**PROFILE_SETTINGS[profile].to_dict())
        self._customizations: dict[str, Any] = {}

    @property
    def profile(self) -> AdaptivityProfile:
        return self._profile

    def set_profile(self, profile: AdaptivityProfile) -> None:
        """Switch to a different profile. Resets customizations."""
        self._profile = profile
        self._settings = AdaptivitySettings(**PROFILE_SETTINGS[profile].to_dict())
        self._customizations.clear()

    def get_settings(self) -> AdaptivitySettings:
        """Get current settings."""
        return self._settings

    def customize(self, key: str, value: Any) -> bool:
        """Customize a specific setting. Returns False if key invalid."""
        if not hasattr(self._settings, key):
            return False
        setattr(self._settings, key, value)
        self._customizations[key] = value
        return True

    def reset_to_profile_defaults(self) -> None:
        """Reset all settings to profile defaults."""
        self._settings = AdaptivitySettings(**PROFILE_SETTINGS[self._profile].to_dict())
        self._customizations.clear()

    def get_customizations(self) -> dict[str, Any]:
        """Get user customizations (deviations from profile defaults)."""
        return dict(self._customizations)

    def get_available_profiles(self) -> list[dict[str, Any]]:
        """Get all available profiles with their settings."""
        return [
            {"profile": p.value, "settings": s.to_dict()}
            for p, s in PROFILE_SETTINGS.items()
        ]

    def get_profile_description(self, profile: AdaptivityProfile) -> str:
        """Get human-readable description of a profile."""
        descriptions = {
            AdaptivityProfile.BEGINNER: "High visibility, guided explanations, minimal suppression",
            AdaptivityProfile.FOCUSED: "Compressed workflows, batched approvals, calm telemetry",
            AdaptivityProfile.EXPERT: "Raw traces, low abstraction, direct runtime visibility",
            AdaptivityProfile.RECOVERY: "Aggressive surfacing, validation detail, diagnostic priority",
        }
        return descriptions.get(profile, "Unknown profile")

    def get_status(self) -> dict[str, Any]:
        """Get current adaptivity status."""
        return {
            "profile": self._profile.value,
            "settings": self._settings.to_dict(),
            "customizations": self._customizations,
            "description": self.get_profile_description(self._profile),
        }
