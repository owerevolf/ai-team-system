"""
P1 — Internal Service Boundaries.

Defines explicit interfaces (contracts) for each subsystem.
Each subsystem exposes ONLY its interface — never internals.

Subsystems:
  - PM Core          : coordination kernel (facade)
  - Retrieval Service: context retrieval pipeline
  - Validation Engine: deterministic validation pipeline
  - Workflow Runtime : workflow execution engine
  - Lock Manager     : resource locking
  - Snapshot Service : project snapshots
  - Telemetry Engine : metrics and observability
  - Risk Engine      : risk analysis
  - Execution Scheduler: task scheduling

Rule: subsystems communicate ONLY through these interfaces.
Never import internals across subsystem boundaries.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ── Subsystem IDs ──

class Subsystem(Enum):
    PM_CORE = "pm_core"
    RETRIEVAL = "retrieval"
    VALIDATION = "validation"
    WORKFLOW = "workflow"
    LOCK_MANAGER = "lock_manager"
    SNAPSHOT = "snapshot"
    TELEMETRY = "telemetry"
    RISK = "risk"
    SCHEDULER = "scheduler"


# ── Retrieval Interface ──

class RetrievalService(ABC):
    """Interface for context retrieval."""

    @abstractmethod
    def retrieve(self, query: str, agent: str, max_files: int = -1,
                 max_symbols: int = -1, token_budget: int = -1) -> Tuple[str, List[Any]]:
        """Retrieve context for a query. Returns (context, stage_results)."""
        ...

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        ...


# ── Validation Interface ──

class ValidationEngine(ABC):
    """Interface for deterministic validation."""

    @abstractmethod
    def validate(self, checks: Optional[List[str]] = None) -> Any:
        """Run validation checks. Returns ValidationResult."""
        ...

    @abstractmethod
    def validate_incremental(self, changed_files: List[str]) -> Any:
        """Run validation only for changed files. Returns ValidationResult."""
        ...

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        ...


# ── Workflow Interface ──

class WorkflowRuntime(ABC):
    """Interface for workflow execution."""

    @abstractmethod
    def execute_workflow(self, workflow_name: str, task_id: str) -> Dict[str, Any]:
        """Execute a workflow for a task. Returns execution result."""
        ...

    @abstractmethod
    def get_workflow_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a running workflow."""
        ...

    @abstractmethod
    def cancel_workflow(self, task_id: str) -> bool:
        """Cancel a running workflow."""
        ...


# ── Lock Manager Interface ──

class LockManager(ABC):
    """Interface for resource locking."""

    @abstractmethod
    def acquire(self, task_id: str, resource: str, lock_type: str,
                timeout: float = 30.0) -> bool:
        """Acquire a lock on a resource."""
        ...

    @abstractmethod
    def release(self, task_id: str, resource: str) -> bool:
        """Release a lock."""
        ...

    @abstractmethod
    def release_all(self, task_id: str) -> int:
        """Release all locks for a task. Returns count."""
        ...

    @abstractmethod
    def get_holder(self, resource: str) -> Optional[str]:
        """Get the task ID holding a lock."""
        ...


# ── Snapshot Interface ──

class SnapshotService(ABC):
    """Interface for project snapshots."""

    @abstractmethod
    def create_snapshot(self, label: str = "") -> str:
        """Create a snapshot. Returns snapshot ID."""
        ...

    @abstractmethod
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore a snapshot."""
        ...

    @abstractmethod
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get snapshot data."""
        ...

    @abstractmethod
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all snapshots."""
        ...


# ── Telemetry Interface ──

class TelemetryEngine(ABC):
    """Interface for metrics and observability."""

    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        ...

    @abstractmethod
    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get recorded metrics."""
        ...

    @abstractmethod
    def get_health_indicators(self) -> Dict[str, Any]:
        """Get health indicators."""
        ...


# ── Risk Engine Interface ──

class RiskEngine(ABC):
    """Interface for risk analysis."""

    @abstractmethod
    def analyze_risk(self, files_changed: List[str],
                     symbols_changed: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze risk of changes. Returns risk assessment."""
        ...

    @abstractmethod
    def get_module_stability(self, file_path: str) -> Dict[str, Any]:
        """Get stability metrics for a module."""
        ...


# ── Scheduler Interface ──

class ExecutionScheduler(ABC):
    """Interface for task scheduling."""

    @abstractmethod
    def schedule_task(self, task_id: str, priority: int = 0) -> bool:
        """Schedule a task for execution."""
        ...

    @abstractmethod
    def get_next_task(self) -> Optional[str]:
        """Get the next task to execute. Returns task ID."""
        ...

    @abstractmethod
    def get_queue_status(self) -> Dict[str, Any]:
        """Get scheduler queue status."""
        ...


# ── Service Registry ──

class ServiceRegistry:
    """
    Central registry for subsystem services.
    Enforces that subsystems only access each other through interfaces.
    """

    def __init__(self):
        self._services: Dict[Subsystem, Any] = {}
        self._interfaces: Dict[Subsystem, type] = {
            Subsystem.RETRIEVAL: RetrievalService,
            Subsystem.VALIDATION: ValidationEngine,
            Subsystem.WORKFLOW: WorkflowRuntime,
            Subsystem.LOCK_MANAGER: LockManager,
            Subsystem.SNAPSHOT: SnapshotService,
            Subsystem.TELEMETRY: TelemetryEngine,
            Subsystem.RISK: RiskEngine,
            Subsystem.SCHEDULER: ExecutionScheduler,
        }

    def register(self, subsystem: Subsystem, service: Any) -> None:
        """Register a service for a subsystem."""
        expected = self._interfaces.get(subsystem)
        if expected and not isinstance(service, expected):
            raise TypeError(
                f"{subsystem.value} service must implement {expected.__name__}, "
                f"got {type(service).__name__}"
            )
        self._services[subsystem] = service

    def get(self, subsystem: Subsystem) -> Any:
        """Get a service by subsystem."""
        service = self._services.get(subsystem)
        if service is None:
            raise KeyError(f"No service registered for {subsystem.value}")
        return service

    def has(self, subsystem: Subsystem) -> bool:
        """Check if a service is registered."""
        return subsystem in self._services

    def list_registered(self) -> List[Subsystem]:
        """List all registered subsystems."""
        return list(self._services.keys())
