"""
Safe Autonomy Guard (P7) — Phase 8

Enforces hard autonomy limits at the workspace level.
Complements user_modes.py with runtime enforcement.

PM CAN:
  - Propose changes
  - Plan workflows
  - Execute approved workflows
  - Analyze and report

PM CANNOT:
  - Silently rewrite architecture
  - Self-modify governance
  - Bypass approvals
  - Mutate protected systems
  - Recursively launch workflows
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Action categories and their autonomy requirements
# ---------------------------------------------------------------------------

# Actions that are always allowed (read-only, analysis)
SAFE_ACTIONS = {
    "analyze", "scan", "read", "list", "search", "query",
    "explain", "summarize", "report", "check", "validate",
    "diff", "compare", "trace", "inspect",
}

# Actions that require approval in beginner mode
BEGINNER_APPROVAL_ACTIONS = {
    "create", "modify", "update", "rename", "move", "copy",
    "delete", "remove", "install", "uninstall",
    "config_change", "dependency_change", "environment_change",
}

# Actions that are NEVER allowed autonomously (hard limits)
NEVER_AUTONOMOUS_ACTIONS = {
    "architecture_change", "governance_change", "bypass_approval",
    "mutate_protected", "recursive_workflow", "modify_pm_core",
    "self_modify", "escalate_privileges", "disable_safety",
}


@dataclass
class AutonomyDecision:
    """Result of an autonomy check."""
    action: str
    allowed: bool
    reason: str
    requires_approval: bool
    risk_level: str = "low"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp,
        }


@dataclass
class AutonomyEvent:
    """Logged autonomy check event."""
    event_id: str
    action: str
    decision: str          # allowed | blocked | requires_approval
    reason: str
    timestamp: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "action": self.action,
            "decision": self.decision,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "context": self.context,
        }


class AutonomyGuard:
    """
    Runtime autonomy enforcement.

    Usage:
        guard = AutonomyGuard(mode="beginner")
        decision = guard.check_action("delete", target="src/main.py")
        if decision.allowed:
            proceed()
        elif decision.requires_approval:
            request_approval(decision)
    """

    def __init__(self, mode: str = "beginner") -> None:
        """
        Args:
            mode: "beginner" or "advanced"
        """
        self.mode = mode
        self._event_log: list[AutonomyEvent] = []

    def check_action(
        self,
        action: str,
        target: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> AutonomyDecision:
        """
        Check whether an action is allowed.

        Args:
            action: Action category (e.g., "delete", "create", "analyze")
            target: Target file/path (optional, for context)
            context: Additional context dict

        Returns:
            AutonomyDecision with allowed/reason/requires_approval
        """
        import uuid

        # Layer 1: Always-safe actions
        if action in SAFE_ACTIONS:
            decision = AutonomyDecision(
                action=action, allowed=True,
                reason=f"Action '{action}' is always safe (read-only/analysis).",
                requires_approval=False, risk_level="low",
            )
            self._log_event(action, "allowed", decision.reason, context)
            return decision

        # Layer 2: Hard limits — never allowed
        if action in NEVER_AUTONOMOUS_ACTIONS:
            decision = AutonomyDecision(
                action=action, allowed=False,
                reason=f"Action '{action}' is blocked by hard autonomy limit. Human must do this directly.",
                requires_approval=True, risk_level="critical",
            )
            self._log_event(action, "blocked", decision.reason, context)
            return decision

        # Layer 3: Mode-dependent approval
        if action in BEGINNER_APPROVAL_ACTIONS:
            if self.mode == "beginner":
                decision = AutonomyDecision(
                    action=action, allowed=False,
                    reason=f"Action '{action}' requires approval in beginner mode.",
                    requires_approval=True, risk_level="medium",
                )
            else:
                decision = AutonomyDecision(
                    action=action, allowed=True,
                    reason=f"Action '{action}' is allowed in advanced mode.",
                    requires_approval=False, risk_level="medium",
                )
            self._log_event(action, "requires_approval" if decision.requires_approval else "allowed", decision.reason, context)
            return decision

        # Layer 4: Unknown action — require approval to be safe
        decision = AutonomyDecision(
            action=action, allowed=False,
            reason=f"Unknown action '{action}'. Requires approval as a safety precaution.",
            requires_approval=True, risk_level="medium",
        )
        self._log_event(action, "requires_approval", decision.reason, context)
        return decision

    def _log_event(self, action: str, decision: str, reason: str, context: Optional[dict] = None) -> None:
        """Log an autonomy check event."""
        import uuid
        event = AutonomyEvent(
            event_id=f"auto-{uuid.uuid4().hex[:8]}",
            action=action,
            decision=decision,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat(),
            context=context or {},
        )
        self._event_log.append(event)
        # Keep log manageable
        if len(self._event_log) > 500:
            self._event_log = self._event_log[-500:]

    def get_event_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent autonomy events."""
        return [e.to_dict() for e in self._event_log[-limit:]]

    def get_blocked_actions(self) -> list[str]:
        """Return list of actions that are never allowed."""
        return sorted(NEVER_AUTONOMOUS_ACTIONS)

    def get_safe_actions(self) -> list[str]:
        """Return list of actions that are always allowed."""
        return sorted(SAFE_ACTIONS)
