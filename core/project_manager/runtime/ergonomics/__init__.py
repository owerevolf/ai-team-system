"""
Ergonomics sub-package for the Project Manager (Phase 10).

Operational ergonomics and human scaling:
  - workflow_compression (P1): Collapse runtime graph into digestible views
  - attention_management (P2): Runtime understands what's important now
  - approval_intelligence (P3): Smart batching, grouping, risk-tiering
  - noise_reduction (P4): Suppress redundant explanations/telemetry/alerts
  - calm_mode (P5): Minimal operational mode
  - intent_centric_ux (P6): What do you want to do vs manage runtime
  - human_time_protection (P7): Minimize context switching, interruptions
"""

from core.project_manager.runtime.ergonomics.workflow_compression import (
    WorkflowCompressor, CompressionLevel, CompressedStep, CompressedView,
)
from core.project_manager.runtime.ergonomics.attention_management import (
    AttentionManager, AttentionItem, AttentionCategory, AttentionPriority,
    AttentionSnapshot,
)
from core.project_manager.runtime.ergonomics.approval_intelligence import (
    ApprovalIntelligence, ApprovalItem, ApprovalBatch, ApprovalRisk,
    ApprovalStatus,
)
from core.project_manager.runtime.ergonomics.noise_reduction import (
    NoiseReducer, NoiseEvent, NoiseType, NoiseReport,
)
from core.project_manager.runtime.ergonomics.calm_mode import (
    CalmMode, CalmLevel, CalmPolicy,
)
from core.project_manager.runtime.ergonomics.intent_centric_ux import (
    IntentCentricUX, Intent, IntentAction, UserIntent, IntentConfidence,
)
from core.project_manager.runtime.ergonomics.human_time_protection import (
    HumanTimeProtection, Interruption, InterruptionType, InterruptionUrgency,
    FocusBlock, InterruptionBatch,
)

__all__ = [
    "WorkflowCompressor", "CompressionLevel", "CompressedStep", "CompressedView",
    "AttentionManager", "AttentionItem", "AttentionCategory", "AttentionPriority",
    "AttentionSnapshot",
    "ApprovalIntelligence", "ApprovalItem", "ApprovalBatch", "ApprovalRisk",
    "ApprovalStatus",
    "NoiseReducer", "NoiseEvent", "NoiseType", "NoiseReport",
    "CalmMode", "CalmLevel", "CalmPolicy",
    "IntentCentricUX", "Intent", "IntentAction", "UserIntent", "IntentConfidence",
    "HumanTimeProtection", "Interruption", "InterruptionType", "InterruptionUrgency",
    "FocusBlock", "InterruptionBatch",
]
