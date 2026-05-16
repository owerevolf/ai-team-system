"""
Phase 13: Architectural Coherence & Evolution Control

Ensures the runtime remains internally coherent, semantic-consistent,
and evolution-safe as it continues to grow.

Subpackages:
- vocabulary: Canonical definitions for shared concepts
- contract_validation: Cross-subsystem contract compatibility
- ontology_drift: Semantic divergence detection
- boundary_enforcement: Architectural boundary violation detection
- dependency_gravity: Dependency chokepoint analysis
- evolution_safety: Change risk classification
- semantic_compression: Conceptual overlap unification
- decision_traceability: Architectural decision preservation
- controlled_evolution: Governed architecture changes
- coherence_engine: Continuous coherence monitoring
"""

from .vocabulary import (
    RuntimeVocabularyRegistry, ConceptDefinition,
    CanonicalPriority, CanonicalStateTier, CanonicalEventType,
    CanonicalApprovalRisk, CanonicalApprovalStatus,
    CanonicalExplanationLevel, CanonicalVisibility,
    CalmDimension,
)
from .contract_validation import (
    CrossSubsystemContractValidator, ContractRequirement,
    ContractValidation, ContractReport, ContractType, ContractStatus,
)
from .ontology_drift import (
    OntologyDriftDetector, DriftFinding, DriftReport,
    DriftType, DriftSeverity,
)
from .boundary_enforcement import (
    ArchitecturalBoundaryEnforcer, BoundaryViolation, BoundaryReport,
    ViolationType, ViolationSeverity,
)
from .dependency_gravity import (
    DependencyGravityAnalyzer, ModuleGravity, GravityReport, GravityLevel,
)
from .evolution_safety import (
    EvolutionSafetyRules, ChangeCategory, ChangeRisk, ChangeClassification,
)
from .semantic_compression import (
    SemanticCompressor, ConceptualOverlap, SemanticCompressionPlan, CompressionTarget,
)
from .decision_traceability import (
    DecisionTraceabilityRegistry, ArchitecturalDecision,
    DecisionType, DecisionScope,
)
from .controlled_evolution import (
    ControlledEvolutionFramework, ArchitectureChange, ChangeStatus,
)
from .coherence_engine import (
    CoherencePreservationEngine, CoherenceCheck, CoherenceReport,
    CoherenceDimension, CoherenceStatus,
)

__all__ = [
    "RuntimeVocabularyRegistry", "ConceptDefinition",
    "CanonicalPriority", "CanonicalStateTier", "CanonicalEventType",
    "CanonicalApprovalRisk", "CanonicalApprovalStatus",
    "CanonicalExplanationLevel", "CanonicalVisibility",
    "CalmDimension",
    "CrossSubsystemContractValidator", "ContractRequirement",
    "ContractValidation", "ContractReport", "ContractType", "ContractStatus",
    "OntologyDriftDetector", "DriftFinding", "DriftReport",
    "DriftType", "DriftSeverity",
    "ArchitecturalBoundaryEnforcer", "BoundaryViolation", "BoundaryReport",
    "ViolationType", "ViolationSeverity",
    "DependencyGravityAnalyzer", "ModuleGravity", "GravityReport", "GravityLevel",
    "EvolutionSafetyRules", "ChangeCategory", "ChangeRisk", "ChangeClassification",
    "SemanticCompressor", "ConceptualOverlap", "SemanticCompressionPlan", "CompressionTarget",
    "DecisionTraceabilityRegistry", "ArchitecturalDecision",
    "DecisionType", "DecisionScope",
    "ControlledEvolutionFramework", "ArchitectureChange", "ChangeStatus",
    "CoherencePreservationEngine", "CoherenceCheck", "CoherenceReport",
    "CoherenceDimension", "CoherenceStatus",
]
