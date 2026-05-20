"""
self_protection.py — Runtime Self-Protection.

Purpose: Protect runtime from self-destruction.
The runtime must be able to say "no".

Blocks:
- orchestration core rewrites
- governance bypasses
- approval suppression
- hidden execution
- memory contract violations
- intent rewriting
- frozen semantic mutations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class ProtectionDecision:
    """A protection decision."""
    action: str = ""
    allowed: bool = True
    reason: str = ""
    risk_level: str = "low"  # low, medium, high, critical
    blocked_by: str = ""


class SelfProtection:
    """
    Protects the runtime from self-destruction.
    The runtime must be able to say "no".
    """

    # Actions that are always blocked
    BLOCKED_ACTIONS = [
        "rewrite_orchestration_core",
        "bypass_governance",
        "suppress_approval",
        "enable_hidden_execution",
        "modify_memory_contracts",
        "rewrite_intent",
        "mutate_frozen_semantics",
        "disable_self_protection",
        "disable_complexity_gate",
        "disable_identity_validation",
        "auto_merge_to_main",
        "unrestricted_shell",
        "internet_execution",
        "self_modify_governance",
    ]

    # Actions that require explicit human approval
    APPROVAL_REQUIRED = [
        "modify_approval_flow",
        "change_risk_thresholds",
        "update_frozen_zones",
        "modify_memory_retention",
        "change_token_budget",
        "update_governance_policies",
    ]

    # Protected files/patterns
    PROTECTED_PATTERNS = [
        "core/production/self_protection.py",
        "core/production/complexity_gate.py",
        "core/dual_mode/identity_validation.py",
        "core/workflow/enoughness_enforcement.py",
        "core/project_manager/governance/",
        "core/project_manager/runtime/developer/approval_runtime.py",
        "core/project_manager/runtime/developer/patch_engine.py",
    ]

    def check_action(self, action: str, context: Optional[Dict[str, Any]] = None) -> ProtectionDecision:
        """Check if an action is allowed."""
        context = context or {}

        # Check blocked actions
        if action.lower() in [a.lower() for a in self.BLOCKED_ACTIONS]:
            logger.warning(f"BLOCKED: {action}")
            return ProtectionDecision(
                action=action, allowed=False,
                reason=f"Action '{action}' is permanently blocked",
                risk_level="critical",
                blocked_by="self_protection",
            )

        # Check approval required
        if action.lower() in [a.lower() for a in self.APPROVAL_REQUIRED]:
            if not context.get("human_approved", False):
                logger.warning(f"APPROVAL REQUIRED: {action}")
                return ProtectionDecision(
                    action=action, allowed=False,
                    reason=f"Action '{action}' requires explicit human approval",
                    risk_level="high",
                    blocked_by="approval_required",
                )

        return ProtectionDecision(
            action=action, allowed=True,
            reason="Action is allowed",
            risk_level="low",
        )

    def is_protected_file(self, file_path: str) -> bool:
        """Check if a file is protected."""
        for pattern in self.PROTECTED_PATTERNS:
            if pattern in file_path or file_path.startswith(pattern):
                return True
        return False

    def validate_patch_safety(self, patch_files: List[str]) -> ProtectionDecision:
        """Validate that a patch doesn't modify protected areas."""
        for f in patch_files:
            if self.is_protected_file(f):
                return ProtectionDecision(
                    action=f"modify {f}",
                    allowed=False,
                    reason=f"File '{f}' is in a protected area",
                    risk_level="critical",
                    blocked_by="protected_file",
                )

        return ProtectionDecision(
            action="apply_patch",
            allowed=True,
            reason="All files are safe to modify",
            risk_level="low",
        )

    def get_protection_status(self) -> Dict[str, Any]:
        """Get current protection status."""
        return {
            "blocked_actions": len(self.BLOCKED_ACTIONS),
            "approval_required_actions": len(self.APPROVAL_REQUIRED),
            "protected_patterns": len(self.PROTECTED_PATTERNS),
            "status": "active",
        }
