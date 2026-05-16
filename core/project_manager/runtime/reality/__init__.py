"""
Phase 17: Operational Reality & Long-Term Usage Validation

Validates runtime under real operational conditions:
- long-run sessions: degradation, drift, fatigue
- repo diversity: monorepos, legacy, broken, mixed-language
- contributor observation: watch real humans
- plugin stress: malicious, conflicting, hostile plugins
- governance fatigue: approval skipping, warning blindness
- real failures: operational corruption scenarios
- cognitive sustainability: fatigue, desensitization
- reality drift: undocumented patterns, bypass rituals
- pressure mapping: enterprise, cloud, multi-user pressure
- simplification: remove what reality proved unnecessary
"""

from .long_run_sessions import (
    LongRunSessionSimulator, SessionReport, HealthIndicator, HealthStatus,
    SessionPhase, HealthSnapshot,
)
from .repo_diversity import (
    RealRepositoryDiversityValidator, RepoType, ValidationResult, DiversityReport,
)
from .contributor_observation import (
    ContributorRealityObserver, Observation, ObservationReport,
    ObservationType, Severity,
)
from .plugin_stress import (
    PluginEcosystemStressTester, PluginThreat, StressTestReport,
    PluginThreatType, ThreatSeverity,
)
from .remaining import (
    GovernanceFatigueRealityCheck, GovernanceFatigueCheck, FatigueIndicator, FatigueLevel,
    RecoveryUnderRealFailures, RealFailureScenario, FailureType, RecoveryResult,
    CognitiveSustainabilityMonitor, CognitiveSustainabilityReport, CognitiveIndicator, CognitiveHealth,
    ArchitecturalRealityDriftDetector, RealityDrift, DriftType,
    EcosystemPressureMapper, PressureVector, PressureSource, PressureIntensity,
    RealityCalibratedSimplification, SimplificationOpportunity, SimplificationType,
)

__all__ = [
    "LongRunSessionSimulator", "SessionReport", "HealthIndicator", "HealthStatus",
    "SessionPhase", "HealthSnapshot",
    "RealRepositoryDiversityValidator", "RepoType", "ValidationResult", "DiversityReport",
    "ContributorRealityObserver", "Observation", "ObservationReport",
    "ObservationType", "Severity",
    "PluginEcosystemStressTester", "PluginThreat", "StressTestReport",
    "PluginThreatType", "ThreatSeverity",
    "GovernanceFatigueRealityCheck", "GovernanceFatigueCheck", "FatigueIndicator", "FatigueLevel",
    "RecoveryUnderRealFailures", "RealFailureScenario", "FailureType", "RecoveryResult",
    "CognitiveSustainabilityMonitor", "CognitiveSustainabilityReport", "CognitiveIndicator", "CognitiveHealth",
    "ArchitecturalRealityDriftDetector", "RealityDrift", "DriftType",
    "EcosystemPressureMapper", "PressureVector", "PressureSource", "PressureIntensity",
    "RealityCalibratedSimplification", "SimplificationOpportunity", "SimplificationType",
]
