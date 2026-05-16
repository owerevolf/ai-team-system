"""
Phase 16: Stabilization, Consolidation & Operational Hardening

Stabilizes the system for long-term survival:
- consolidation: merge duplicates, collapse abstractions
- freeze zones: frozen semantics, stable contracts
- hardening: endurance validation
- contributor validation: measure real humans
- governance reduction: remove ceremonial approvals
- slimming: bounded runtime growth
- freeze review: define "done enough"
- meta-limiter: stop recursive governance
- ecosystem stability: preserve hackability
- enoughness: survivability > capability growth
"""

from .consolidation import (
    RuntimeConsolidationEngine, ConsolidationItem, ConsolidationReport,
    ConsolidationType, ConsolidationPriority,
)
from .freeze_zones import (
    ArchitectureFreezeZones, FrozenConcept, FreezeLevel,
)
from .hardening import (
    OperationalHardeningSuite, StressTest, HardeningReport,
    StressType, HardeningResult,
)
from .contributor_validation import (
    RealContributorValidator, ContributorMetric, ContributorValidationReport,
    ValidationMetric, MetricStatus,
)
from .governance_reduction import (
    GovernanceReductionPass, GovernanceIssue, GovernanceReductionReport,
    GovernanceIssueType, ReductionPriority,
)
from .slimming import (
    RuntimeSlimmingInitiative, SlimmingItem, SlimmingReport, SlimmingType,
)
from .freeze_review import (
    ArchitecturalFreezeReview, SubsystemSettlement, SettlementStatus,
)
from .meta_limiter import (
    MetaSystemLimiter, MetaSystemCheck, MetaLevel, LimiterAction,
)
from .ecosystem_stability import (
    EcosystemStabilityValidator, StabilityIndicator, StabilityReport,
    StabilityDimension, StabilityLevel,
)
from .enoughness import (
    EnoughnessEngine, EnoughnessAssessment, EnoughnessReport,
    EnoughnessQuestion, EnoughnessVerdict,
)

__all__ = [
    "RuntimeConsolidationEngine", "ConsolidationItem", "ConsolidationReport",
    "ConsolidationType", "ConsolidationPriority",
    "ArchitectureFreezeZones", "FrozenConcept", "FreezeLevel",
    "OperationalHardeningSuite", "StressTest", "HardeningReport",
    "StressType", "HardeningResult",
    "RealContributorValidator", "ContributorMetric", "ContributorValidationReport",
    "ValidationMetric", "MetricStatus",
    "GovernanceReductionPass", "GovernanceIssue", "GovernanceReductionReport",
    "GovernanceIssueType", "ReductionPriority",
    "RuntimeSlimmingInitiative", "SlimmingItem", "SlimmingReport", "SlimmingType",
    "ArchitecturalFreezeReview", "SubsystemSettlement", "SettlementStatus",
    "MetaSystemLimiter", "MetaSystemCheck", "MetaLevel", "LimiterAction",
    "EcosystemStabilityValidator", "StabilityIndicator", "StabilityReport",
    "StabilityDimension", "StabilityLevel",
    "EnoughnessEngine", "EnoughnessAssessment", "EnoughnessReport",
    "EnoughnessQuestion", "EnoughnessVerdict",
]
