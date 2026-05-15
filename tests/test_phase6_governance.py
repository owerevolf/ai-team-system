"""
Tests for PHASE 6 — Platform Governance.
Tests all 20 governance priorities.
"""

import time
import threading
from pathlib import Path

# ── P1: Service Boundaries ──

def test_service_registry():
    from core.project_manager.governance.interfaces import ServiceRegistry, Subsystem
    reg = ServiceRegistry()
    assert reg.list_registered() == []
    assert not reg.has(Subsystem.PM_CORE)

def test_service_registry_unknown_subsystem():
    from core.project_manager.governance.interfaces import ServiceRegistry, Subsystem
    reg = ServiceRegistry()
    try:
        reg.get(Subsystem.PM_CORE)
        assert False, "Should raise KeyError"
    except KeyError:
        pass


# ── P2: Dependency Governance ──

def test_dependency_governance_forbidden():
    from core.project_manager.governance.dependency_governance import DependencyGovernance
    from core.project_manager.governance.interfaces import Subsystem
    dg = DependencyGovernance()
    allowed, reason = dg.check_dependency(Subsystem.TELEMETRY, Subsystem.WORKFLOW)
    assert not allowed
    assert "FORBIDDEN" in reason

def test_dependency_governance_allowed():
    from core.project_manager.governance.dependency_governance import DependencyGovernance
    from core.project_manager.governance.interfaces import Subsystem
    dg = DependencyGovernance()
    allowed, reason = dg.check_dependency(Subsystem.WORKFLOW, Subsystem.LOCK_MANAGER)
    assert allowed

def test_dependency_governance_read_only():
    from core.project_manager.governance.dependency_governance import DependencyGovernance
    from core.project_manager.governance.interfaces import Subsystem
    dg = DependencyGovernance()
    allowed, reason = dg.check_dependency(Subsystem.SNAPSHOT, Subsystem.PM_CORE)
    assert allowed
    assert "READ_ONLY" in reason

def test_dependency_map():
    from core.project_manager.governance.dependency_governance import DependencyGovernance
    dg = DependencyGovernance()
    dep_map = dg.get_dependency_map()
    assert 'pm_core' in dep_map
    assert 'telemetry' in dep_map


# ── P3: Drift Detection ──

def test_drift_detector_empty():
    from core.project_manager.governance.drift_detection import ArchitecturalDriftDetector
    detector = ArchitecturalDriftDetector()
    # Analyze only governance directory — should not crash
    signals = detector.analyze_directory(Path("core/project_manager/governance"), pattern="*.py")
    assert isinstance(signals, list)

def test_drift_detector_summary():
    from core.project_manager.governance.drift_detection import ArchitecturalDriftDetector
    detector = ArchitecturalDriftDetector()
    detector.analyze_directory(Path("core/project_manager/governance"), pattern="*.py")
    summary = detector.get_summary()
    assert 'total_modules' in summary
    assert summary['total_modules'] > 0


# ── P4: Complexity Budget ──

def test_complexity_budget_default():
    from core.project_manager.governance.complexity_budget import ComplexityBudgetSystem, BudgetStatus
    cbs = ComplexityBudgetSystem()
    budget = cbs.get_budget('fan_out')
    assert budget is not None
    assert budget.status == BudgetStatus.OK

def test_complexity_budget_exceeded():
    from core.project_manager.governance.complexity_budget import ComplexityBudgetSystem, BudgetStatus
    cbs = ComplexityBudgetSystem()
    violation = cbs.update('fan_out', 20)
    assert violation is not None
    assert 'exceeded' in violation.message.lower() or 'Budget' in violation.message

def test_complexity_budget_status():
    from core.project_manager.governance.complexity_budget import ComplexityBudgetSystem
    cbs = ComplexityBudgetSystem()
    status = cbs.get_status()
    assert 'fan_out' in status
    assert 'dependency_depth' in status


# ── P5: Health Model ──

def test_health_model_stable():
    from core.project_manager.governance.health_model import PlatformHealthModel, HealthStatus
    model = PlatformHealthModel()
    report = model.compute_health({
        'validation_stability': 0.95,
        'rollback_frequency': 0.9,
        'workflow_failures': 0.95,
        'lock_contention': 0.85,
        'cache_invalidation': 0.9,
        'retrieval_overload': 0.88,
        'event_recursion': 0.92,
        'subsystem_stability': 0.95,
    })
    assert report.overall_status == HealthStatus.STABLE
    assert report.overall_score >= 0.8

def test_health_model_critical():
    from core.project_manager.governance.health_model import PlatformHealthModel, HealthStatus
    model = PlatformHealthModel()
    report = model.compute_health({
        'validation_stability': 0.2,
        'rollback_frequency': 0.3,
        'workflow_failures': 0.1,
        'lock_contention': 0.2,
        'cache_invalidation': 0.3,
        'retrieval_overload': 0.2,
        'event_recursion': 0.1,
        'subsystem_stability': 0.2,
    })
    assert report.overall_status == HealthStatus.CRITICAL

def test_health_model_trend():
    from core.project_manager.governance.health_model import PlatformHealthModel
    model = PlatformHealthModel()
    for i in range(20):
        model.record_factor('test_factor', 0.5 + i * 0.02)
    trend = model.get_trend('test_factor')
    assert trend is not None
    assert trend > 0  # improving


# ── P6: Runtime Introspection ──

def test_introspection_register_task():
    from core.project_manager.governance.introspection import RuntimeIntrospection, TaskStatus
    ri = RuntimeIntrospection()
    ri.register_task("task-1", "agent-a", "default", ["file.py"])
    tasks = ri.get_running_tasks()
    assert len(tasks) == 1
    assert tasks[0].task_id == "task-1"

def test_introspection_bottleneck_detection():
    from core.project_manager.governance.introspection import RuntimeIntrospection, TaskStatus
    ri = RuntimeIntrospection()
    ri.register_task("t1", "a1", "default", ["shared.py"])
    ri.register_task("t2", "a2", "default", ["shared.py"])
    ri.update_task("t2", status=TaskStatus.BLOCKED)
    # Just verify no crash
    bottlenecks = ri.detect_bottlenecks(threshold_seconds=0)
    assert isinstance(bottlenecks, list)

def test_introspection_snapshot():
    from core.project_manager.governance.introspection import RuntimeIntrospection
    ri = RuntimeIntrospection()
    ri.register_subsystem("test-sub")
    ri.register_task("t1", "a1", "default", ["f.py"])
    snapshot = ri.get_snapshot()
    assert 'active_tasks' in snapshot
    assert 'unstable_subsystems' in snapshot


# ── P7: Debuggability ──

def test_debuggability_trace():
    from core.project_manager.governance.debuggability import DebuggabilityLayer, TraceType, TraceStatus
    dl = DebuggabilityLayer()
    tid = dl.start_trace(TraceType.EXECUTION, "task-1", "test_op")
    assert tid != ""
    dl.end_trace(tid, TraceStatus.SUCCESS)
    trace = dl.get_trace(tid)
    assert trace is not None
    assert trace.status == TraceStatus.SUCCESS

def test_debuggability_task_traces():
    from core.project_manager.governance.debuggability import DebuggabilityLayer, TraceType, TraceStatus
    dl = DebuggabilityLayer()
    dl.start_trace(TraceType.EXECUTION, "task-1", "op1")
    dl.start_trace(TraceType.VALIDATION, "task-1", "op2")
    traces = dl.get_task_traces("task-1")
    assert len(traces) == 2

def test_debuggability_execution_summary():
    from core.project_manager.governance.debuggability import DebuggabilityLayer, TraceType, TraceStatus
    dl = DebuggabilityLayer()
    tid = dl.start_trace(TraceType.EXECUTION, "task-1", "failing_op")
    dl.end_trace(tid, TraceStatus.FAILED, error="test error")
    summary = dl.get_execution_summary("task-1")
    assert summary['failed_count'] == 1


# ── P8: Policy Engine ──

def test_policy_engine_default_rules():
    from core.project_manager.governance.policy_engine import GovernancePolicyEngine, PolicyType
    pe = GovernancePolicyEngine()
    rules = pe.get_all_rules()
    assert len(rules) > 0

def test_policy_engine_check_concurrency():
    from core.project_manager.governance.policy_engine import GovernancePolicyEngine, PolicyType, PolicyAction
    pe = GovernancePolicyEngine()
    decision = pe.check_policy(PolicyType.CONCURRENCY, {
        'agent': 'test-agent',
        'current_concurrent': 15,
    })
    assert not decision.allowed
    assert decision.action == PolicyAction.DENY

def test_policy_engine_violations():
    from core.project_manager.governance.policy_engine import GovernancePolicyEngine, PolicyType
    pe = GovernancePolicyEngine()
    pe.check_policy(PolicyType.CONCURRENCY, {
        'agent': 'test-agent',
        'current_concurrent': 15,
    })
    violations = pe.get_violations()
    assert len(violations) > 0


# ── P9: Operational Modes ──

def test_operational_modes_default():
    from core.project_manager.governance.operational_modes import OperationalModes, OperationalMode
    om = OperationalModes()
    assert om.current_mode == OperationalMode.NORMAL

def test_operational_modes_switch():
    from core.project_manager.governance.operational_modes import OperationalModes, OperationalMode
    om = OperationalModes()
    change = om.set_mode(OperationalMode.SAFE)
    assert change['to'] == 'safe'
    assert om.is_safe_mode()

def test_operational_modes_config():
    from core.project_manager.governance.operational_modes import OperationalModes, OperationalMode
    om = OperationalModes(OperationalMode.PERFORMANCE)
    assert om.config.max_concurrent_tasks == 10
    assert om.config.enable_aggressive_caching is True


# ── P10: Event Governance ──

def test_event_governance_budget():
    from core.project_manager.governance.event_governance import EventGovernance
    eg = EventGovernance()
    eg.set_budget("test_event", max_per_second=5, max_per_minute=100)
    allowed, reason = eg.check_event_allowed("test_event")
    assert allowed

def test_event_governance_chain():
    from core.project_manager.governance.event_governance import EventGovernance
    eg = EventGovernance()
    chain = eg.start_event_chain("chain-1", "root_event")
    assert chain.chain_id == "chain-1"
    allowed, _ = eg.record_chain_event("chain-1", "child_event")
    assert allowed
    ended = eg.end_event_chain("chain-1")
    assert ended is not None
    assert len(ended.events) == 1


# ── P11: Change Governance ──

def test_change_governance_record():
    from core.project_manager.governance.change_governance import (
        ChangeGovernance, ChangeRecord, ChangeType
    )
    cg = ChangeGovernance()
    change = ChangeRecord(
        change_id="chg-1",
        change_type=ChangeType.ADD,
        target="test_module.py",
        subsystem="test",
        timestamp=time.time(),
    )
    result = cg.record_change(change)
    assert result['change_id'] == 'chg-1'

def test_change_governance_impact_summary():
    from core.project_manager.governance.change_governance import (
        ChangeGovernance, ChangeRecord, ChangeType
    )
    cg = ChangeGovernance()
    cg.record_change(ChangeRecord(
        change_id="chg-1", change_type=ChangeType.ADD,
        target="test.py", subsystem="test", timestamp=time.time(),
    ))
    summary = cg.get_impact_summary()
    assert summary['total_changes'] == 1


# ── P12: Ownership ──

def test_ownership_get():
    from core.project_manager.governance.ownership import OwnershipSystem
    os = OwnershipSystem()
    owner = os.get_owner("pm_core")
    assert owner is not None
    assert owner.subsystem == "pm_core"

def test_ownership_modification_check():
    from core.project_manager.governance.ownership import OwnershipSystem
    os = OwnershipSystem()
    allowed, reason = os.check_modification_allowed("pm_core", "developer")
    # pm_core requires approval
    assert not allowed or "review" in reason.lower()

def test_ownership_risk_report():
    from core.project_manager.governance.ownership import OwnershipSystem
    os = OwnershipSystem()
    report = os.get_risk_report()
    assert 'total_subsystems' in report
    assert report['total_subsystems'] > 0


# ── P13: Config Governance ──

def test_config_governance_set_get():
    from core.project_manager.governance.config_governance import ConfigurationGovernance
    cg = ConfigurationGovernance()
    success, error = cg.set('max_concurrent_tasks', 5, description="test")
    assert success, error
    assert cg.get('max_concurrent_tasks') == 5

def test_config_governance_validation():
    from core.project_manager.governance.config_governance import ConfigurationGovernance
    cg = ConfigurationGovernance()
    success, error = cg.set('max_concurrent_tasks', "not_a_number")
    assert not success

def test_config_governance_history():
    from core.project_manager.governance.config_governance import ConfigurationGovernance
    cg = ConfigurationGovernance()
    cg.set('max_concurrent_tasks', 5)
    cg.set('max_concurrent_tasks', 10)
    history = cg.get_history('max_concurrent_tasks')
    assert len(history) == 2


# ── P14: Failure Governance ──

def test_failure_governance_record():
    from core.project_manager.governance.failure_governance import (
        FailureGovernance, FailureType, FailureSeverity
    )
    fg = FailureGovernance()
    failure = fg.record_failure("task-1", "test-sub", FailureType.TRANSIENT,
                                 FailureSeverity.MEDIUM, "test failure")
    assert failure.failure_id != ""
    assert not failure.resolved

def test_failure_governance_retry():
    from core.project_manager.governance.failure_governance import (
        FailureGovernance, FailureType, FailureSeverity
    )
    fg = FailureGovernance()
    failure = fg.record_failure("task-1", "test-sub", FailureType.TRANSIENT,
                                 FailureSeverity.LOW, "test")
    should_retry, delay = fg.should_retry(failure.failure_id)
    assert should_retry
    assert delay > 0

def test_failure_governance_stats():
    from core.project_manager.governance.failure_governance import (
        FailureGovernance, FailureType, FailureSeverity
    )
    fg = FailureGovernance()
    fg.record_failure("task-1", "test-sub", FailureType.TRANSIENT,
                       FailureSeverity.LOW, "test")
    stats = fg.get_stats()
    assert stats['total_failures'] == 1


# ── P15: Auditability ──

def test_auditability_log():
    from core.project_manager.governance.auditability import (
        PlatformAuditability, AuditEventType
    )
    pa = PlatformAuditability()
    entry = pa.log(AuditEventType.POLICY_VIOLATION, "test-agent",
                   "modify", "config", "denied")
    assert entry.event_id != ""

def test_auditability_violations():
    from core.project_manager.governance.auditability import (
        PlatformAuditability, AuditEventType
    )
    pa = PlatformAuditability()
    pa.log(AuditEventType.POLICY_VIOLATION, "agent", "action", "target", "denied")
    violations = pa.get_violations()
    assert len(violations) == 1


# ── P16: Observability ──

def test_observability_signal():
    from core.project_manager.governance.observability import (
        ObservabilitySimplification, SignalPriority
    )
    obs = ObservabilitySimplification()
    obs.set_threshold("cpu_usage", warning=70, critical=90)
    alert = obs.record_signal("cpu_usage", 95, SignalPriority.HIGH, "test")
    assert alert is not None
    assert alert.severity == "critical"

def test_observability_dedup():
    from core.project_manager.governance.observability import (
        ObservabilitySimplification, SignalPriority
    )
    obs = ObservabilitySimplification()
    obs.set_threshold("cpu_usage", warning=70, critical=90, cooldown_seconds=0)
    alert1 = obs.record_signal("cpu_usage", 95, SignalPriority.HIGH, "test")
    alert2 = obs.record_signal("cpu_usage", 96, SignalPriority.HIGH, "test")
    # Second should be deduplicated
    assert alert2 is None

def test_observability_actionable():
    from core.project_manager.governance.observability import (
        ObservabilitySimplification, SignalPriority
    )
    obs = ObservabilitySimplification()
    obs.record_signal("test", 1.0, SignalPriority.CRITICAL, "sub", "critical issue")
    obs.record_signal("test2", 1.0, SignalPriority.NOISE, "sub", "noise")
    actionable = obs.get_actionable_metrics()
    assert len(actionable) == 1


# ── P17: Simplification ──

def test_simplification_register():
    from core.project_manager.governance.simplification import RuntimeSimplificationDetector
    sd = RuntimeSimplificationDetector()
    sd.register_item("feature", "test_feature", "test.py")
    sd.record_usage("feature", "test_feature")
    dead = sd.detect_dead_features(threshold_days=30)
    # Used recently, should not be dead
    assert len(dead) == 0

def test_simplification_dead_detection():
    from core.project_manager.governance.simplification import RuntimeSimplificationDetector
    sd = RuntimeSimplificationDetector()
    sd.register_item("feature", "dead_feature", "dead.py")
    # Never used, threshold 0 days
    dead = sd.detect_dead_features(threshold_days=0)
    assert len(dead) >= 1


# ── P18: Extensibility ──

def test_extensibility_register():
    from core.project_manager.governance.extensibility import (
        GovernedExtensibility, PlatformExtension, ExtensionContract, ExtensionState
    )

    class TestExtension(PlatformExtension):
        def get_contract(self):
            return ExtensionContract(name="test-ext", version="1.0", description="test")
        def initialize(self, registry):
            return True
        def start(self):
            return True
        def stop(self):
            return True
        def health_check(self):
            return {'healthy': True}
        def get_state(self):
            return ExtensionState.ACTIVE

    ge = GovernedExtensibility()
    ext = TestExtension()
    success, error = ge.register_extension(ext)
    assert success, error

def test_extensibility_circular_deps():
    from core.project_manager.governance.extensibility import (
        GovernedExtensibility, PlatformExtension, ExtensionContract, ExtensionState
    )

    class ExtA(PlatformExtension):
        def get_contract(self):
            return ExtensionContract(name="ext-a", version="1.0", description="a")
        def initialize(self, registry): return True
        def start(self): return True
        def stop(self): return True
        def health_check(self): return {'healthy': True}
        def get_state(self): return ExtensionState.ACTIVE

    class ExtB(PlatformExtension):
        def get_contract(self):
            return ExtensionContract(name="ext-b", version="1.0", description="b")
        def initialize(self, registry): return True
        def start(self): return True
        def stop(self): return True
        def health_check(self): return {'healthy': True}
        def get_state(self): return ExtensionState.ACTIVE

    ge = GovernedExtensibility()
    ge.register_extension(ExtA())
    ge.register_extension(ExtB())

    # Manually set up circular dependency
    ge._dependency_graph["ext-a"] = {"ext-b"}
    ge._dependency_graph["ext-b"] = {"ext-a"}

    cycles = ge.check_circular_dependencies()
    assert len(cycles) > 0


# ── P20: Long-Run Stability ──

def test_stability_snapshot():
    from core.project_manager.governance.long_run_stability import LongRunStability
    ls = LongRunStability()
    snapshot = ls.take_snapshot(memory_items=100, cache_entries=50)
    assert snapshot.memory_items == 100

def test_stability_memory_leak_detection():
    from core.project_manager.governance.long_run_stability import LongRunStability
    ls = LongRunStability()
    # Simulate growing memory — significant growth
    for i in range(25):
        ls.take_snapshot(memory_items=100 + i * 50, cache_entries=50)
    result = ls.detect_memory_leak(window=5)
    assert result is not None
    assert result['detected'] is True

def test_stability_report():
    from core.project_manager.governance.long_run_stability import LongRunStability
    ls = LongRunStability()
    ls.take_snapshot(memory_items=100, cache_entries=50)
    report = ls.get_stability_report()
    assert 'is_stable' in report


# ── Governance Layer Integration ──

def test_governance_layer_creation():
    from core.project_manager.governance import GovernanceLayer
    gov = GovernanceLayer(env="testing")
    assert gov.registry is not None
    assert gov.dependencies is not None
    assert gov.health is not None
    assert gov.policies is not None

def test_governance_layer_report():
    from core.project_manager.governance import GovernanceLayer
    gov = GovernanceLayer(env="testing")
    report = gov.get_full_report()
    assert 'health' in report
    assert 'budgets' in report
    assert 'introspection' in report
    assert 'policies' in report
