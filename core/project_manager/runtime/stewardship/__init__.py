"""
Phase 18: Reduction, Settlement & Long-Term Stewardship

Final architectural phase — transition from construction to stewardship.
"""

from .retirement import (
    SubsystemRetirementFramework, RetirementCandidate, RetirementReport,
    RetirementStatus, RetirementReason,
)
from .semantic_settlement import (
    APISemanticSettlement, SemanticContract, StabilityLevel,
)
from .governance_settlement import (
    GovernanceSettlementReview, GovernanceItem, GovernanceEssentiality,
)
from .remaining import (
    RuntimeWeightIndex, WeightDimension, WeightStatus, WeightMeasurement,
    LongTermMaintainershipModel, MaintainershipProfile, MaintainershipRisk,
    PluginBoundaryFreezing, FrozenBoundary, BoundaryType,
    ConceptualCompressionPass, ConceptualCompression, CompressionType,
    EcosystemSustainabilityReview, SustainabilityAssessment, SustainabilityDimension, SustainabilityLevel,
    ArchitecturePreservationLayer, PreservedArtifact, PreservationType,
    StewardshipEngine, StewardshipAssessment, StewardshipVerdict, StewardshipQuestion,
)

__all__ = [
    "SubsystemRetirementFramework", "RetirementCandidate", "RetirementReport",
    "RetirementStatus", "RetirementReason",
    "APISemanticSettlement", "SemanticContract", "StabilityLevel",
    "GovernanceSettlementReview", "GovernanceItem", "GovernanceEssentiality",
    "RuntimeWeightIndex", "WeightDimension", "WeightStatus", "WeightMeasurement",
    "LongTermMaintainershipModel", "MaintainershipProfile", "MaintainershipRisk",
    "PluginBoundaryFreezing", "FrozenBoundary", "BoundaryType",
    "ConceptualCompressionPass", "ConceptualCompression", "CompressionType",
    "EcosystemSustainabilityReview", "SustainabilityAssessment", "SustainabilityDimension", "SustainabilityLevel",
    "ArchitecturePreservationLayer", "PreservedArtifact", "PreservationType",
    "StewardshipEngine", "StewardshipAssessment", "StewardshipVerdict", "StewardshipQuestion",
]
