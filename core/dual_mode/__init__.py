"""
Phase 23 — Dual-Mode Runtime Integration & True AI Engineering Workspace.

Modules:
- dual_identity.py: one system, two modes (learning/engineering)
- intent_switching.py: detects user intent and switches mode accordingly
- identity_validation.py: checks if the system has lost its soul

Principle: ONE AND THE SAME RUNTIME works as teacher, teamlead, engineering orchestrator.
"""

from .dual_identity import DualIdentity, ModeConfig, RuntimeMode
from .intent_switching import IntentSwitching, IntentAnalysis, IntentType
from .identity_validation import IdentityValidation, IdentityReport, IdentityCheck

__all__ = [
    "DualIdentity", "ModeConfig", "RuntimeMode",
    "IntentSwitching", "IntentAnalysis", "IntentType",
    "IdentityValidation", "IdentityReport", "IdentityCheck",
]
