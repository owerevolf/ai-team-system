"""
Phase 15: Ecosystem Sustainability & Contributor Scalability

Ensures the project can grow as an ecosystem without losing runtime identity,
architectural coherence, or burning out maintainers.

Subpackages:
- onboarding: Progressive contributor onboarding (5 levels)
- learning_paths: Structured subsystem learning paths
- experimentation: Safe experimentation framework (sandbox, feature flags)
- fork_drift: Fork drift analysis (semantic/governance divergence)
- plugin_governance: Plugin ecosystem governance (capability contracts)
- maintainer_load: Maintainer load protection (burnout prevention)
- succession: Architectural succession planning (knowledge transfer)
- ecosystem_coherence: Ecosystem coherence metrics (plugin conflicts)
- contributor_ergonomics: Contributor ergonomics (friction reduction)
- identity: Core identity preservation (resist pressure)
"""

from .onboarding import (
    ContributorOnboardingCompressor, LearningModule, ContributorPath,
    OnboardingLevel,
)
from .learning_paths import (
    ArchitecturalLearningPaths, LearningPath, LearningStep, LearningPathType,
)
from .experimentation import (
    SafeExperimentationFramework, ExperimentDefinition, FeatureFlag,
    ExperimentZone, ExperimentRisk,
)
from .fork_drift import (
    ForkDriftAnalyzer, ForkDriftReport, DriftDimension, DriftLevel,
)
from .plugin_governance import (
    PluginEcosystemGovernance, ExtensionContract, CapabilityType, CapabilityRisk,
    PluginGovernanceReport,
)
from .maintainer_load import (
    MaintainerLoadProtector, MaintainerLoad, LoadProtectionReport,
    LoadType, LoadLevel,
)
from .succession import (
    ArchitecturalSuccessionPlanner, SubsystemKnowledge, SuccessionReadiness,
)
from .ecosystem_coherence import (
    EcosystemCoherenceMetrics, EcosystemCoherenceReport, EcosystemIssue,
    EcosystemDimension, EcosystemHealth,
)
from .contributor_ergonomics import (
    ContributorErgonomics, FrictionPoint, ErgonomicsReport,
    FrictionType, FrictionLevel,
)
from .identity import (
    CoreIdentityPreservation, IdentityStatement, PressureAssessment,
    IdentityAspect, PressureType,
)

__all__ = [
    "ContributorOnboardingCompressor", "LearningModule", "ContributorPath",
    "OnboardingLevel",
    "ArchitecturalLearningPaths", "LearningPath", "LearningStep", "LearningPathType",
    "SafeExperimentationFramework", "ExperimentDefinition", "FeatureFlag",
    "ExperimentZone", "ExperimentRisk",
    "ForkDriftAnalyzer", "ForkDriftReport", "DriftDimension", "DriftLevel",
    "PluginEcosystemGovernance", "ExtensionContract", "CapabilityType", "CapabilityRisk",
    "PluginGovernanceReport",
    "MaintainerLoadProtector", "MaintainerLoad", "LoadProtectionReport",
    "LoadType", "LoadLevel",
    "ArchitecturalSuccessionPlanner", "SubsystemKnowledge", "SuccessionReadiness",
    "EcosystemCoherenceMetrics", "EcosystemCoherenceReport", "EcosystemIssue",
    "EcosystemDimension", "EcosystemHealth",
    "ContributorErgonomics", "FrictionPoint", "ErgonomicsReport",
    "FrictionType", "FrictionLevel",
    "CoreIdentityPreservation", "IdentityStatement", "PressureAssessment",
    "IdentityAspect", "PressureType",
]
