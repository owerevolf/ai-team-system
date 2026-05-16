"""
Phase 15, P2: Architectural Learning Paths

Structured subsystem learning paths for deep knowledge.
Each path covers one area: recovery, governance, observability, execution, plugin boundaries.

Principle: Knowledge must be navigable, incremental, operational.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LearningPathType(Enum):
    RECOVERY = "recovery"
    GOVERNANCE = "governance"
    OBSERVABILITY = "observability"
    EXECUTION = "execution"
    PLUGIN = "plugin"
    TRUST = "trust"
    COMPRESSION = "compression"
    COHERENCE = "coherence"


@dataclass
class LearningStep:
    """A single step in a learning path."""
    order: int
    title: str
    description: str
    module: str                    # Which runtime module to study
    key_classes: list[str]         # Key classes to understand
    key_concepts: list[str]
    verification: str              # How to verify understanding
    estimated_minutes: int


@dataclass
class LearningPath:
    """A complete learning path for one area."""
    path_type: LearningPathType
    title: str
    description: str
    target_audience: str
    steps: list[LearningStep] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        return sum(s.estimated_minutes for s in self.steps)

    @property
    def total_steps(self) -> int:
        return len(self.steps)


class ArchitecturalLearningPaths:
    """
    Manages structured learning paths for runtime subsystems.
    Each path is a guided tour through one area of the system.
    """

    def __init__(self) -> None:
        self._paths: dict[LearningPathType, LearningPath] = {}
        self._register_paths()

    def _register_paths(self) -> None:
        """Register all learning paths."""

        # Recovery path
        self._paths[LearningPathType.RECOVERY] = LearningPath(
            path_type=LearningPathType.RECOVERY,
            title="Recovery Internals",
            description="How runtime survives failures: checkpoints, replay, deterministic recovery",
            target_audience="core_maintainers, plugin_developers",
            steps=[
                LearningStep(1, "State Lifecycle",
                    "Understand state tiers and persistence",
                    "durability/state_lifecycle",
                    ["StateTier", "StateEntry", "StateLifecycleManager"],
                    ["EPHEMERAL → SESSION → OPERATIONAL → STRUCTURAL"],
                    "Explain when each tier is used",
                    15),
                LearningStep(2, "Recovery Engine",
                    "How recovery works: snapshots, replay, deterministic execution",
                    "durability/recovery_engine",
                    ["RecoveryStep", "DeterministicRecoveryEngine", "FailureSnapshot"],
                    ["replay", "deterministic", "checkpoint"],
                    "Trace a recovery from failure to completion",
                    25),
                LearningStep(3, "Context GC",
                    "How stale context is collected without losing important state",
                    "durability/context_gc",
                    ["ContextType", "ContextStatus", "ContextGC"],
                    ["STALE", "EXPIRED", "GC policy"],
                    "Explain why STRUCTURAL state is never auto-collected",
                    20),
                LearningStep(4, "Chaos Testing",
                    "How we verify recovery works by injecting failures",
                    "durability/chaos_testing",
                    ["ChaosType", "ChaosScenario", "ChaosTester"],
                    ["fault injection", "recovery verification"],
                    "Design a chaos test for a new failure mode",
                    20),
            ],
        )

        # Governance path
        self._paths[LearningPathType.GOVERNANCE] = LearningPath(
            path_type=LearningPathType.GOVERNANCE,
            title="Governance Deep Dive",
            description="How runtime stays safe: contracts, approvals, boundaries, evolution",
            target_audience="core_maintainers, architects",
            steps=[
                LearningStep(1, "Transparency Contracts",
                    "Mandatory visibility rules that cannot be overridden",
                    "trust/transparency_contracts",
                    ["TransparencyContractManager", "EventCategory", "VisibilityAction"],
                    ["SHOW", "SUMMARIZE", "DELAY", "SUPPRESS"],
                    "Explain which events must always be visible",
                    20),
                LearningStep(2, "Approval Intelligence",
                    "Risk-based approval: when to auto-apply, when to require human",
                    "ergonomics/approval_intelligence",
                    ["ApprovalRisk", "ApprovalStatus", "ApprovalIntelligence"],
                    ["LOW → auto-apply", "CRITICAL → mandatory approval"],
                    "Trace an approval decision from request to resolution",
                    25),
                LearningStep(3, "Boundary Enforcement",
                    "Architectural boundaries between subsystems",
                    "coherence/boundary_enforcement",
                    ["ArchitecturalBoundaryEnforcer", "BoundaryViolation"],
                    ["allowed imports", "circular dependencies", "forbidden imports"],
                    "Explain why compression can import from trust but not from web_ui",
                    20),
                LearningStep(4, "Evolution Safety",
                    "How architecture changes are classified and governed",
                    "coherence/evolution_safety",
                    ["EvolutionSafetyRules", "ChangeCategory", "ChangeRisk"],
                    ["SAFE", "REVIEW_REQUIRED", "HIGH_RISK"],
                    "Classify a proposed change and explain the approval process",
                    25),
            ],
        )

        # Observability path
        self._paths[LearningPathType.OBSERVABILITY] = LearningPath(
            path_type=LearningPathType.OBSERVABILITY,
            title="Observability & Trust",
            description="How runtime makes itself visible: traces, explanations, calm metrics",
            target_audience="all_contributors",
            steps=[
                LearningStep(1, "Operational Observability",
                    "Timeline entries, decision traces, runtime events",
                    "durability/observability",
                    ["EntryType", "TimelineEntry", "DecisionTrace"],
                    ["RUNTIME_EVENT", "DECISION", "ERROR", "RECOVERY"],
                    "Trace a decision from trigger to outcome",
                    20),
                LearningStep(2, "Explainability Layer",
                    "Unified explanations: WHY, SOURCE, CONSTRAINTS, IMPACT",
                    "durability/explainability_layer",
                    ["ExplanationField", "UnifiedExplanation"],
                    ["WHY", "SOURCE", "CONSTRAINTS", "IMPACT", "CONFIDENCE"],
                    "Generate an explanation for a runtime decision",
                    20),
                LearningStep(3, "Trust Drift Detection",
                    "How we detect when user trust is eroding",
                    "trust/trust_drift_detection",
                    ["TrustDriftType", "TrustDriftDetector"],
                    ["BLIND_APPROVAL", "SUPPRESSION_DISTRUST", "GOVERNANCE_FATIGUE"],
                    "Explain what triggers a trust drift alert",
                    20),
                LearningStep(4, "Operational Calm",
                    "Measuring psychological sustainability",
                    "compression/operational_calm",
                    ["CalmDimension", "CalmLevel", "OperationalCalmMetrics"],
                    ["interruption density", "alert frequency", "approval pressure"],
                    "Explain why calm metrics matter for usability",
                    15),
            ],
        )

        # Execution path
        self._paths[LearningPathType.EXECUTION] = LearningPath(
            path_type=LearningPathType.EXECUTION,
            title="Runtime Execution",
            description="How runtime actually runs: workflows, state, approvals, recovery",
            target_audience="core_maintainers, plugin_developers",
            steps=[
                LearningStep(1, "Workflow Execution",
                    "How workflows are defined, executed, and monitored",
                    "runtime/workflows",
                    ["Workflow", "WorkflowStep"],
                    ["sequential execution", "approval gates", "checkpoints"],
                    "Trace a workflow from start to finish",
                    25),
                LearningStep(2, "State Management",
                    "State lifecycle, tiers, and GC",
                    "durability/state_lifecycle",
                    ["StateTier", "StateLifecycleManager"],
                    ["EPHEMERAL", "SESSION", "OPERATIONAL", "STRUCTURAL"],
                    "Explain state tier promotion and GC policy",
                    20),
                LearningStep(3, "Conflict Detection",
                    "How runtime detects and resolves conflicts",
                    "runtime/conflict_detection",
                    ["ConflictDetector", "ConflictType"],
                    ["resource conflict", "semantic conflict", "temporal conflict"],
                    "Explain how a conflict is detected and resolved",
                    15),
            ],
        )

        # Plugin path
        self._paths[LearningPathType.PLUGIN] = LearningPath(
            path_type=LearningPathType.PLUGIN,
            title="Plugin Boundary Path",
            description="How to write plugins that respect runtime boundaries",
            target_audience="plugin_developers, extension_authors",
            steps=[
                LearningStep(1, "Plugin Boundaries",
                    "What plugins can and cannot do",
                    "durability/plugin_boundaries",
                    ["PluginCapability", "PluginTrustLevel", "PluginBoundaryEnforcer"],
                    ["READ_FILES", "WRITE_FILES", "BYPASS_APPROVALS"],
                    "Explain why BYPASS_APPROVALS is forbidden",
                    20),
                LearningStep(2, "Extension Contracts",
                    "Capability contracts for safe extension",
                    "runtime/ecosystem/plugin_governance",
                    ["ExtensionContract", "CapabilityPermission"],
                    ["visibility permissions", "workflow permissions", "automation permissions"],
                    "Design a capability contract for a new plugin",
                    25),
            ],
        )

    def get_path(self, path_type: LearningPathType) -> Optional[LearningPath]:
        """Get a learning path by type."""
        return self._paths.get(path_type)

    def list_paths(self) -> list[LearningPathType]:
        """List all available learning paths."""
        return list(self._paths.keys())

    def get_total_learning_time(self) -> int:
        """Get total learning time across all paths in minutes."""
        return sum(p.total_minutes for p in self._paths.values())

    @property
    def total_paths(self) -> int:
        return len(self._paths)
