"""
User Mode System — Phase 8: Human-First Execution (P13), Beginner Safe Mode (P17),
Advanced User Mode (P18).

Defines per-mode configuration, hard autonomy boundaries, and a manager that
answers "is this action allowed?" for any given action + risk level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Mode presets
# ---------------------------------------------------------------------------

BEGINNER_MODE = "beginner"
ADVANCED_MODE = "advanced"
SUPPORTED_MODES = {BEGINNER_MODE, ADVANCED_MODE}

RISK_LEVELS = {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# ModeConfig
# ---------------------------------------------------------------------------

@dataclass
class ModeConfig:
    """Configuration for a single user mode.

    Attributes:
        max_autonomous_files: Max files the agent may touch without asking.
        require_approval_for: Action categories that always need approval.
        explain_before_action: Whether the agent must explain before acting.
        show_detailed_explanations: Whether to include verbose reasoning.
        guided_workflows_only: Restrict to pre-defined guided workflows.
        batch_approvals: Allow batching multiple approvals into one prompt.
        max_workflow_steps: Max steps a single workflow may contain.
        show_tips: Display helpful tips and suggestions.
        risk_threshold: Highest risk level the agent may act on autonomously.
    """

    max_autonomous_files: int = 1
    require_approval_for: list[str] = field(default_factory=list)
    explain_before_action: bool = True
    show_detailed_explanations: bool = True
    guided_workflows_only: bool = True
    batch_approvals: bool = False
    max_workflow_steps: int = 3
    show_tips: bool = True
    risk_threshold: str = "low"

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict snapshot of this config."""
        return {
            "max_autonomous_files": self.max_autonomous_files,
            "require_approval_for": list(self.require_approval_for),
            "explain_before_action": self.explain_before_action,
            "show_detailed_explanations": self.show_detailed_explanations,
            "guided_workflows_only": self.guided_workflows_only,
            "batch_approvals": self.batch_approvals,
            "max_workflow_steps": self.max_workflow_steps,
            "show_tips": self.show_tips,
            "risk_threshold": self.risk_threshold,
        }


# Predefined mode configs
MODE_CONFIGS: dict[str, ModeConfig] = {
    BEGINNER_MODE: ModeConfig(
        max_autonomous_files=1,
        require_approval_for=[
            "delete",
            "rename",
            "move",
            "config_change",
            "dependency_change",
            "architecture_change",
        ],
        explain_before_action=True,
        show_detailed_explanations=True,
        guided_workflows_only=True,
        batch_approvals=False,
        max_workflow_steps=3,
        show_tips=True,
        risk_threshold="low",
    ),
    ADVANCED_MODE: ModeConfig(
        max_autonomous_files=10,
        require_approval_for=[
            "delete",
            "architecture_change",
            "governance_change",
        ],
        explain_before_action=False,
        show_detailed_explanations=False,
        guided_workflows_only=False,
        batch_approvals=True,
        max_workflow_steps=20,
        show_tips=False,
        risk_threshold="medium",
    ),
}


# ---------------------------------------------------------------------------
# AutonomyLimits — hard boundaries that NEVER change regardless of mode
# ---------------------------------------------------------------------------

@dataclass
class AutonomyLimits:
    """Hard autonomy boundaries that apply in EVERY mode.

    These are invariant — no mode, flag, or prompt may override them.
    """

    can_silently_rewrite_architecture: bool = False
    can_self_modify_governance: bool = False
    can_bypass_approvals: bool = False
    can_mutate_protected_systems: bool = False
    can_recursively_launch_workflows: bool = False
    can_delete_without_approval: bool = False
    can_modify_pm_core: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict snapshot of these limits."""
        return {
            "can_silently_rewrite_architecture": self.can_silently_rewrite_architecture,
            "can_self_modify_governance": self.can_self_modify_governance,
            "can_bypass_approvals": self.can_bypass_approvals,
            "can_mutate_protected_systems": self.can_mutate_protected_systems,
            "can_recursively_launch_workflows": self.can_recursively_launch_workflows,
            "can_delete_without_approval": self.can_delete_without_approval,
            "can_modify_pm_core": self.can_modify_pm_core,
        }


# Singleton instance — shared across the process
GLOBAL_AUTONOMY_LIMITS = AutonomyLimits()


# ---------------------------------------------------------------------------
# UserModeManager
# ---------------------------------------------------------------------------

class UserModeManager:
    """Manages the active user mode and answers permission queries.

    Usage:
        mgr = UserModeManager("beginner")
        result = mgr.is_action_allowed("delete", "low")
        # {"allowed": False, "reason": "...", "requires_approval": True}
    """

    # Ordered risk levels for comparison (low < medium < high < critical)
    _RISK_ORDER = ("low", "medium", "high", "critical")

    def __init__(self, mode: str = BEGINNER_MODE) -> None:
        """Initialize with the given mode.

        Args:
            mode: One of "beginner" or "advanced".

        Raises:
            ValueError: If *mode* is not a supported mode name.
        """
        self.set_mode(mode)

    # -- public API ---------------------------------------------------------

    def get_mode_config(self) -> dict[str, Any]:
        """Return the current mode's configuration as a dict."""
        return self._config.to_dict()

    def is_action_allowed(self, action: str, risk_level: str) -> dict[str, Any]:
        """Check whether *action* is allowed at *risk_level* in the current mode.

        The decision considers three layers:
        1. **Hard autonomy limits** — always enforced, never overridable.
        2. **Mode-specific approval list** — actions that require approval.
        3. **Risk threshold** — actions above the mode's threshold need approval.

        Args:
            action:      Action category (e.g. "delete", "rename", "create").
            risk_level:  One of "low", "medium", "high", "critical".

        Returns:
            A dict with keys:
                - ``allowed`` (bool): Whether the action may proceed autonomously.
                - ``reason`` (str): Human-readable explanation.
                - ``requires_approval`` (bool): Whether human approval is needed.
        """
        # --- Layer 1: hard autonomy limits --------------------------------
        hard_block = self._check_hard_limits(action)
        if hard_block is not None:
            return hard_block

        # --- Layer 2: mode-specific approval list -------------------------
        if action in self._config.require_approval_for:
            return {
                "allowed": False,
                "reason": (
                    f"Action '{action}' requires approval in {self._mode} mode. "
                    f"Add it to the approval queue."
                ),
                "requires_approval": True,
            }

        # --- Layer 3: risk threshold --------------------------------------
        if self._risk_exceeds_threshold(risk_level):
            return {
                "allowed": False,
                "reason": (
                    f"Risk level '{risk_level}' exceeds the {self._mode} mode "
                    f"threshold of '{self._config.risk_threshold}'. "
                    f"Approval required."
                ),
                "requires_approval": True,
            }

        # --- All clear ----------------------------------------------------
        return {
            "allowed": True,
            "reason": f"Action '{action}' at risk '{risk_level}' is permitted.",
            "requires_approval": False,
        }

    def get_autonomy_limits(self) -> dict[str, Any]:
        """Return the global hard autonomy limits as a dict."""
        return GLOBAL_AUTONOMY_LIMITS.to_dict()

    def set_mode(self, mode: str) -> None:
        """Switch to a different user mode.

        Args:
            mode: One of "beginner" or "advanced".

        Raises:
            ValueError: If *mode* is not supported.
        """
        mode = mode.lower().strip()
        if mode not in SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported mode '{mode}'. Choose from: {sorted(SUPPORTED_MODES)}"
            )
        self._mode = mode
        self._config = MODE_CONFIGS[mode]

    def get_mode(self) -> str:
        """Return the active mode name."""
        return self._mode

    # -- internals ---------------------------------------------------------

    def _check_hard_limits(self, action: str) -> dict[str, Any] | None:
        """Return a block dict if *action* violates a hard limit, else None."""
        HARD_LIMIT_ACTION_MAP: dict[str, str] = {
            "architecture_change": "can_silently_rewrite_architecture",
            "governance_change": "can_self_modify_governance",
            "delete": "can_delete_without_approval",
            "bypass_approval": "can_bypass_approvals",
            "mutate_protected": "can_mutate_protected_systems",
            "recursive_workflow": "can_recursively_launch_workflows",
            "modify_pm_core": "can_modify_pm_core",
        }

        limit_attr = HARD_LIMIT_ACTION_MAP.get(action)
        if limit_attr is not None:
            if not getattr(GLOBAL_AUTONOMY_LIMITS, limit_attr, False):
                return {
                    "allowed": False,
                    "reason": (
                        f"Action '{action}' is blocked by hard autonomy limit "
                        f"'{limit_attr}'. This cannot be overridden by any mode."
                    ),
                    "requires_approval": True,
                }
        return None

    def _risk_exceeds_threshold(self, risk_level: str) -> bool:
        """Return True if *risk_level* is above the mode's threshold."""
        threshold = self._config.risk_threshold
        try:
            return self._RISK_ORDER.index(risk_level) > self._RISK_ORDER.index(
                threshold
            )
        except ValueError:
            # Unknown risk level → treat as exceeding
            return True
