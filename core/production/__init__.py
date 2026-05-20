"""
Phase 22 — Production Readiness, Real Repo Operations & Developer Trust.

Modules:
- developer_trust.py: explains all runtime actions
- session_continuity.py: survives restarts and long pauses
- complexity_gate.py: final defense against complexity creep
- noise_collapse.py: reduces runtime noise
- engineering_metrics.py: measures real utility

Principle: TRUST IS THE PRODUCT
"""

from .developer_trust import DeveloperTrust, TrustExplanation
from .session_continuity import SessionContinuity, SessionState
from .complexity_gate import ComplexityGate, GateDecision
from .noise_collapse import NoiseCollapse, NoiseRule
from .engineering_metrics import EngineeringMetrics, MetricSnapshot

__all__ = [
    "DeveloperTrust", "TrustExplanation",
    "SessionContinuity", "SessionState",
    "ComplexityGate", "GateDecision",
    "NoiseCollapse", "NoiseRule",
    "EngineeringMetrics", "MetricSnapshot",
]
