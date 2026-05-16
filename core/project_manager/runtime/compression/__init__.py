"""
Phase 12: Minimal Surface & System Compression

After 11 phases, the system has accumulated significant capability.
Now the focus shifts from capability growth to operational minimalism.

Subpackages:
- surface_audit: Measures complete operational surface
- workflow_compression: Analyzes and compresses workflow paths
- governance_simplification: Detects governance entropy
- dead_system_detection: Finds unused/unreachable subsystems
- latency_reduction: Measures and minimizes operational latency
- interaction_minimalism: Eliminates unnecessary interactions
- progressive_disclosure: Reveals complexity only on demand
- operational_calm: Measures psychological sustainability
- architecture_compression: Finds subsystem overlap
- do_less: Central restraint engine — "restraint as architecture"

Principle: Every subsystem must continuously justify its existence.
"""

from .surface_audit import SurfaceAreaAuditor, SurfaceReport, SurfaceItem, SurfaceType
from .workflow_compression import WorkflowPathCompressor, WorkflowPath, WorkflowStep, CompressionResult
from .governance_simplification import GovernanceSimplifier, GovernanceItem, GovernanceSimplificationReport
from .dead_system_detection import DeadSystemDetector, DeadItem, DeadSystemReport
from .latency_reduction import RuntimeLatencyReducer, LatencyMeasurement, LatencyReport
from .interaction_minimalism import InteractionMinimalismLayer, InteractionEvent, MinimalInteractionPolicy
from .progressive_disclosure import ProgressiveDisclosureEngine, DisclosureItem, DisclosureProfile
from .operational_calm import OperationalCalmMetrics, CalmReading, CalmReport, CalmDimension
from .architecture_compression import ArchitectureCompressor, OverlapFinding, CompressionPlan
from .do_less import DoLessRuntime, ProposedAction, RestraintDecision, DoLessReport

__all__ = [
    "SurfaceAreaAuditor", "SurfaceReport", "SurfaceItem", "SurfaceType",
    "WorkflowPathCompressor", "WorkflowPath", "WorkflowStep", "CompressionResult",
    "GovernanceSimplifier", "GovernanceItem", "GovernanceSimplificationReport",
    "DeadSystemDetector", "DeadItem", "DeadSystemReport",
    "RuntimeLatencyReducer", "LatencyMeasurement", "LatencyReport",
    "InteractionMinimalismLayer", "InteractionEvent", "MinimalInteractionPolicy",
    "ProgressiveDisclosureEngine", "DisclosureItem", "DisclosureProfile",
    "OperationalCalmMetrics", "CalmReading", "CalmReport", "CalmDimension",
    "ArchitectureCompressor", "OverlapFinding", "CompressionPlan",
    "DoLessRuntime", "ProposedAction", "RestraintDecision", "DoLessReport",
]
