"""
Trust sub-package for the Project Manager (Phase 11).

Adaptive transparency and trust stability:
  - transparency_contracts (P1): Explicit visibility contracts
  - visibility_guarantees (P2): Critical event invariants
  - adaptation_inspector (P3): Why surfaced/hidden/delayed
  - user_controlled_adaptivity (P4): Adjustable operational policy
  - trust_drift_detection (P5): Governance fatigue monitoring
  - explainability_compression (P6): Layered explanations
  - predictable_personality (P7): Stable operational identity
  - audit_visible_automation (P8): Visible replayable attributable
  - governance_pressure (P9): Fatigue and load metrics
  - simplicity_preservation (P10): Complexity budget
"""

from core.project_manager.runtime.trust.transparency_contracts import (
    TransparencyContractManager, TransparencyRule, TransparencyContractViolation,
    VisibilityAction, EventCategory, DEFAULT_TRANSPARENCY_CONTRACT,
)
from core.project_manager.runtime.trust.visibility_guarantees import (
    VisibilityGuaranteeEnforcer, VisibilityGuarantee, GuaranteeType, GuaranteeLevel,
    BUILTIN_GUARANTEES,
)
from core.project_manager.runtime.trust.adaptation_inspector import (
    RuntimeAdaptationInspector, AdaptationDecision, AdaptationType, AdaptationReason,
)
from core.project_manager.runtime.trust.user_controlled_adaptivity import (
    UserControlledAdaptivity, AdaptivitySettings, AdaptivityProfile, PROFILE_SETTINGS,
)
from core.project_manager.runtime.trust.trust_drift_detection import (
    TrustDriftDetector, TrustDriftEvent, TrustDriftType, TrustDriftSeverity,
    TrustDriftThreshold,
)
from core.project_manager.runtime.trust.explainability_compression import (
    ExplainabilityCompressor, LayeredExplanation, ExplanationLayer, ExplanationLevel,
)
from core.project_manager.runtime.trust.predictable_personality import (
    PredictableRuntimePersonality, PersonalityBounds, PersonalityChange,
    SignalingStyle, AlertSemantics,
)
from core.project_manager.runtime.trust.audit_visible_automation import (
    AuditVisibleAutomation, AutomationRecord, AutomationType, AutomationStatus,
)
from core.project_manager.runtime.trust.governance_pressure import (
    GovernancePressureMonitor, PressureReading, PressureType, PressureLevel,
    PressureThresholds,
)
from core.project_manager.runtime.trust.simplicity_preservation import (
    SimplicityPreservation, SubsystemCost, ComplexityBudget, ComplexityTier, CostType,
)

__all__ = [
    "TransparencyContractManager", "TransparencyRule", "TransparencyContractViolation",
    "VisibilityAction", "EventCategory",
    "VisibilityGuaranteeEnforcer", "VisibilityGuarantee", "GuaranteeType", "GuaranteeLevel",
    "RuntimeAdaptationInspector", "AdaptationDecision", "AdaptationType", "AdaptationReason",
    "UserControlledAdaptivity", "AdaptivitySettings", "AdaptivityProfile",
    "TrustDriftDetector", "TrustDriftEvent", "TrustDriftType", "TrustDriftSeverity",
    "TrustDriftThreshold",
    "ExplainabilityCompressor", "LayeredExplanation", "ExplanationLayer", "ExplanationLevel",
    "PredictableRuntimePersonality", "PersonalityBounds", "PersonalityChange",
    "AuditVisibleAutomation", "AutomationRecord", "AutomationType", "AutomationStatus",
    "GovernancePressureMonitor", "PressureReading", "PressureType", "PressureLevel",
    "PressureThresholds",
    "SimplicityPreservation", "SubsystemCost", "ComplexityBudget", "ComplexityTier",
]
