"""
Governance Layer — PHASE 6.

Unified entry point for all governance subsystems.
This is the coordination kernel for platform governance.

Modules:
- interfaces.py          : P1 — Service boundaries (abstract interfaces)
- dependency_governance.py: P2 — Dependency policies
- drift_detection.py     : P3 — Architectural drift detection
- complexity_budget.py   : P4 — Complexity budget system
- health_model.py        : P5 — Platform health scoring
- introspection.py       : P6 — Runtime introspection
- debuggability.py       : P7 — Execution tracing
- policy_engine.py       : P8 — Governance policy engine
- operational_modes.py   : P9 — Operational modes
- event_governance.py    : P10 — Event governance
- change_governance.py   : P11 — Change impact tracking
- ownership.py           : P12 — Subsystem ownership
- config_governance.py   : P13 — Configuration governance
- failure_governance.py  : P14 — Failure management
- auditability.py        : P15 — Platform audit log
- observability.py       : P16 — Observability simplification
- simplification.py      : P17 — Dead code detection
- extensibility.py       : P18 — Governed extensibility
- stress_tests.py        : P19 — Platform stress tests
- long_run_stability.py  : P20 — Long-run stability monitoring
"""

from typing import Dict, List, Optional, Any

# P1: Interfaces
from core.project_manager.governance.interfaces import (
    Subsystem, ServiceRegistry,
    RetrievalService, ValidationEngine, WorkflowRuntime,
    LockManager, SnapshotService, TelemetryEngine,
    RiskEngine, ExecutionScheduler,
)

# P2: Dependency Governance
from core.project_manager.governance.dependency_governance import (
    DependencyGovernance, DependencyRule, DependencyPolicy, BoundaryViolation,
)

# P3: Drift Detection
from core.project_manager.governance.drift_detection import (
    ArchitecturalDriftDetector, DriftSignal, DriftSeverity, ModuleMetrics,
)

# P4: Complexity Budget
from core.project_manager.governance.complexity_budget import (
    ComplexityBudgetSystem, Budget, BudgetStatus, BudgetViolation,
)

# P5: Health Model
from core.project_manager.governance.health_model import (
    PlatformHealthModel, HealthStatus, HealthFactor, HealthReport,
)

# P6: Introspection
from core.project_manager.governance.introspection import (
    RuntimeIntrospection, RuntimeTask, TaskStatus, Bottleneck, SubsystemStatus,
)

# P7: Debuggability
from core.project_manager.governance.debuggability import (
    DebuggabilityLayer, TraceType, TraceStatus, TraceEntry,
)

# P8: Policy Engine
from core.project_manager.governance.policy_engine import (
    GovernancePolicyEngine, PolicyRule, PolicyType, PolicyAction,
    PolicyDecision, PolicyViolation,
)

# P9: Operational Modes
from core.project_manager.governance.operational_modes import (
    OperationalModes, OperationalMode, ModeConfig,
)

# P10: Event Governance
from core.project_manager.governance.event_governance import (
    EventGovernance, EventBudget, EventChain, EventPolicy,
)

# P11: Change Governance
from core.project_manager.governance.change_governance import (
    ChangeGovernance, ChangeRecord, ChangeType, ImpactLevel,
)

# P12: Ownership
from core.project_manager.governance.ownership import (
    OwnershipSystem, SubsystemOwner, RiskLevel, ModificationPolicy,
)

# P13: Config Governance
from core.project_manager.governance.config_governance import (
    ConfigurationGovernance, ConfigEntry, ConfigChange, ConfigEnvironment,
)

# P14: Failure Governance
from core.project_manager.governance.failure_governance import (
    FailureGovernance, FailureRecord, FailureType, FailureSeverity, RetryPolicy,
)

# P15: Auditability
from core.project_manager.governance.auditability import (
    PlatformAuditability, AuditEntry, AuditEventType,
)

# P16: Observability
from core.project_manager.governance.observability import (
    ObservabilitySimplification, Signal, SignalPriority,
    AnomalyThreshold, Alert,
)

# P17: Simplification
from core.project_manager.governance.simplification import (
    RuntimeSimplificationDetector, DeadItem, DeadItemSeverity,
)

# P18: Extensibility
from core.project_manager.governance.extensibility import (
    GovernedExtensibility, PlatformExtension, ExtensionContract, ExtensionState,
)

# P19: Stress Tests
from core.project_manager.governance.stress_tests import PlatformStressTests

# P20: Long-Run Stability
from core.project_manager.governance.long_run_stability import (
    LongRunStability, StabilitySnapshot,
)


class GovernanceLayer:
    """
    Unified governance layer for the platform.
    Coordinates all governance subsystems.

    This is the single entry point for all governance operations.
    """

    def __init__(self, env: str = "development"):
        # P1: Service Registry
        self.registry = ServiceRegistry()

        # P2: Dependency Governance
        self.dependencies = DependencyGovernance()

        # P3: Drift Detection
        self.drift = ArchitecturalDriftDetector()

        # P4: Complexity Budget
        self.budgets = ComplexityBudgetSystem()

        # P5: Health Model
        self.health = PlatformHealthModel()

        # P6: Introspection
        self.introspection = RuntimeIntrospection()

        # P7: Debuggability
        self.debug = DebuggabilityLayer()

        # P8: Policy Engine
        self.policies = GovernancePolicyEngine()

        # P9: Operational Modes
        mode_map = {
            'development': OperationalMode.NORMAL,
            'testing': OperationalMode.DIAGNOSTIC,
            'staging': OperationalMode.SAFE,
            'production': OperationalMode.NORMAL,
        }
        self.modes = OperationalModes(default_mode=mode_map.get(env, OperationalMode.NORMAL))

        # P10: Event Governance
        self.events = EventGovernance()

        # P11: Change Governance
        self.changes = ChangeGovernance()

        # P12: Ownership
        self.ownership = OwnershipSystem()

        # P13: Config Governance
        env_map = {
            'development': ConfigEnvironment.DEVELOPMENT,
            'testing': ConfigEnvironment.TESTING,
            'staging': ConfigEnvironment.STAGING,
            'production': ConfigEnvironment.PRODUCTION,
        }
        self.config = ConfigurationGovernance(env=env_map.get(env, ConfigEnvironment.DEVELOPMENT))

        # P14: Failure Governance
        self.failures = FailureGovernance()

        # P15: Auditability
        self.audit = PlatformAuditability()

        # P16: Observability
        self.observability = ObservabilitySimplification()

        # P17: Simplification
        self.simplification = RuntimeSimplificationDetector()

        # P18: Extensibility
        self.extensions = GovernedExtensibility()

        # P20: Long-Run Stability
        self.stability = LongRunStability()

    def get_full_report(self) -> Dict[str, Any]:
        """Get a comprehensive governance report."""
        return {
            'health': self.health.compute_health().__dict__,
            'budgets': self.budgets.get_status(),
            'introspection': self.introspection.get_snapshot(),
            'policies': self.policies.get_stats(),
            'failures': self.failures.get_stats(),
            'audit': self.audit.get_stats(),
            'observability': self.observability.get_stats(),
            'stability': self.stability.get_stability_report(),
            'operational_mode': self.modes.get_config_summary(),
            'ownership': self.ownership.get_risk_report(),
            'changes': self.changes.get_impact_summary(),
        }
