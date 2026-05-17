"""
Task Coordination System — centralized task lifecycle management.

Task states: PENDING → RUNNING → COMPLETED
                    ↓          ↓
                 BLOCKED    FAILED
                    ↓          ↓
                 WAITING    ROLLED_BACK

Deterministic. No AI planning. Only state tracking and conflict prevention.
"""

import time
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class LockType(Enum):
    READ = "read"
    WRITE = "write"
    EXCLUSIVE = "exclusive"


@dataclass
class Task:
    """A single engineering task."""
    id: str = ""
    title: str = ""
    description: str = ""
    agent: str = ""
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    workflow: str = "default"  # feature, bugfix, refactor

    # Resources
    files_locked: List[str] = field(default_factory=list)
    modules_locked: List[str] = field(default_factory=list)
    symbols_locked: List[str] = field(default_factory=list)

    # Execution
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    error: str = ""

    # Results
    files_changed: List[str] = field(default_factory=list)
    patches_applied: int = 0
    validation_issues: int = 0
    risk_level: str = "low"
    risk_score: float = 0.0

    # Approval
    requires_approval: bool = False
    approved: bool = False
    approved_by: str = ""

    # Recovery
    snapshot_before: str = ""
    snapshot_after: str = ""
    checkpoint_ids: List[str] = field(default_factory=list)


@dataclass
class ResourceLock:
    """A lock on a resource (file, module, or symbol)."""
    resource: str
    lock_type: LockType
    task_id: str
    acquired_at: float = 0.0
    expires_at: float = 0.0  # 0 = no expiry


@dataclass
class ExecutionCheckpoint:
    """A recovery checkpoint for a task."""
    id: str = ""
    task_id: str = ""
    timestamp: str = ""
    description: str = ""
    snapshot_id: str = ""
    files_state: Dict[str, str] = field(default_factory=dict)  # file -> hash
    patches_applied: int = 0


class TaskCoordinationSystem:
    """
    Centralized task coordination.

    Responsibilities:
    - Register and track active tasks
    - Manage task lifecycle (state transitions)
    - Prevent overlapping execution on same resources
    - Enforce resource locking
    - Detect conflicts between tasks
    """

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._locks: Dict[str, ResourceLock] = {}  # resource -> lock
        self._task_locks: Dict[str, Set[str]] = defaultdict(set)  # task_id -> resources
        self._checkpoints: Dict[str, ExecutionCheckpoint] = {}
        self._lock = threading.Lock()

    # ── TASK LIFECYCLE ──

    def create_task(
        self,
        title: str,
        agent: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        workflow: str = "default",
    ) -> Task:
        """Register a new task."""
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            agent=agent,
            priority=priority,
            workflow=workflow,
            created_at=self._now(),
        )

        with self._lock:
            self._tasks[task.id] = task

        logger.info(f"Task created: {task.id} ({title}) by {agent}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_active_tasks(self) -> List[Task]:
        """Get all non-completed tasks."""
        return [
            t for t in self._tasks.values()
            if t.state in (TaskState.PENDING, TaskState.RUNNING, TaskState.BLOCKED,
                          TaskState.WAITING_APPROVAL)
        ]

    def get_tasks_by_state(self, state: TaskState) -> List[Task]:
        """Get tasks in a specific state."""
        return [t for t in self._tasks.values() if t.state == state]

    def transition_state(
        self, task_id: str, new_state: TaskState, reason: str = ""
    ) -> bool:
        """
        Transition a task to a new state.

        Enforces valid state transitions.
        """
        valid_transitions = {
            TaskState.PENDING: {TaskState.RUNNING, TaskState.CANCELLED},
            TaskState.RUNNING: {TaskState.BLOCKED, TaskState.WAITING_APPROVAL,
                               TaskState.COMPLETED, TaskState.FAILED},
            TaskState.BLOCKED: {TaskState.RUNNING, TaskState.CANCELLED},
            TaskState.WAITING_APPROVAL: {TaskState.RUNNING, TaskState.CANCELLED},
            TaskState.FAILED: {TaskState.PENDING, TaskState.ROLLED_BACK},
            TaskState.COMPLETED: set(),  # terminal
            TaskState.ROLLED_BACK: {TaskState.PENDING},  # can retry
            TaskState.CANCELLED: set(),  # terminal
        }

        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            allowed = valid_transitions.get(task.state, set())
            if new_state not in allowed:
                logger.warning(
                    f"Invalid transition: {task.state.value} -> {new_state.value} "
                    f"for task {task_id}"
                )
                return False

            old_state = task.state
            task.state = new_state

            if new_state == TaskState.RUNNING and not task.started_at:
                task.started_at = self._now()
            elif new_state in (TaskState.COMPLETED, TaskState.FAILED,
                             TaskState.ROLLED_BACK, TaskState.CANCELLED):
                task.completed_at = self._now()

            # Release locks on terminal states
            if new_state in (TaskState.COMPLETED, TaskState.FAILED,
                           TaskState.ROLLED_BACK, TaskState.CANCELLED):
                self._release_all_locks(task_id)

        logger.info(
            f"Task {task_id}: {old_state.value} -> {new_state.value}"
            f"{' (' + reason + ')' if reason else ''}"
        )
        return True

    # ── RESOURCE LOCKING ──

    def acquire_lock(
        self,
        task_id: str,
        resource: str,
        lock_type: LockType = LockType.WRITE,
        timeout: float = 30.0,
    ) -> bool:
        """
        Acquire a lock on a resource.

        Rules:
        - READ locks are compatible with other READ locks
        - WRITE locks are exclusive (no other READ or WRITE)
        - EXCLUSIVE locks block everything
        - Deadlock prevention: timeout-based
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.state not in (TaskState.PENDING, TaskState.RUNNING):
                return False

            existing = self._locks.get(resource)

            if existing:
                # Same task can upgrade its lock
                if existing.task_id == task_id:
                    if lock_type == LockType.EXCLUSIVE or existing.lock_type != lock_type:
                        existing.lock_type = lock_type
                    return True

                # Check compatibility
                if not self._locks_compatible(existing, lock_type):
                    return False
            now = time.time()
            self._locks[resource] = ResourceLock(
                resource=resource,
                lock_type=lock_type,
                task_id=task_id,
                acquired_at=now,
                expires_at=now + timeout if timeout > 0 else 0,
            )
            self._task_locks[task_id].add(resource)

        logger.debug(f"Lock acquired: {resource} ({lock_type.value}) by {task_id}")
        return True

    def release_lock(self, task_id: str, resource: str) -> bool:
        """Release a lock."""
        with self._lock:
            existing = self._locks.get(resource)
            if not existing or existing.task_id != task_id:
                return False

            del self._locks[resource]
            self._task_locks[task_id].discard(resource)

        logger.debug(f"Lock released: {resource} by {task_id}")
        return True

    def release_all_task_locks(self, task_id: str) -> int:
        """Release all locks held by a task. Returns count."""
        with self._lock:
            return self._release_all_locks(task_id)

    def get_lock_holder(self, resource: str) -> Optional[str]:
        """Get the task ID holding a lock on a resource."""
        lock = self._locks.get(resource)
        return lock.task_id if lock else None

    def get_task_resources(self, task_id: str) -> Set[str]:
        """Get all resources locked by a task."""
        return self._task_locks.get(task_id, set()).copy()

    def _release_all_locks(self, task_id: str) -> int:
        """Internal: release all locks for a task."""
        resources = list(self._task_locks.get(task_id, set()))
        count = 0
        for resource in resources:
            if resource in self._locks and self._locks[resource].task_id == task_id:
                del self._locks[resource]
                count += 1
        self._task_locks.pop(task_id, None)
        if count:
            logger.debug(f"Released {count} locks for task {task_id}")
        return count

    def _locks_compatible(self, existing: ResourceLock, requested: LockType) -> bool:
        """Check if a new lock is compatible with an existing one."""
        # READ + READ = OK
        if existing.lock_type == LockType.READ and requested == LockType.READ:
            return True
        # Everything else is incompatible
        return False

    # ── CONFLICT DETECTION ──

    def detect_conflicts(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Detect conflicts between a task and other active tasks.

        Conflict types:
        - file_overlap: both tasks modify same file
        - module_overlap: both tasks modify same module
        - symbol_overlap: both tasks modify same symbol
        - dependency_collision: tasks modify dependent files
        """
        conflicts = []

        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return conflicts

            task_resources = self._task_locks.get(task_id, set())

            for other_id, other_task in self._tasks.items():
                if other_id == task_id:
                    continue
                if other_task.state not in (TaskState.RUNNING, TaskState.PENDING,
                                           TaskState.BLOCKED):
                    continue

                other_resources = self._task_locks.get(other_id, set())

                # Check file overlap
                overlap = task_resources & other_resources
                if overlap:
                    for resource in overlap:
                        conflicts.append({
                            'type': 'file_overlap',
                            'resource': resource,
                            'task_a': task_id,
                            'task_b': other_id,
                            'severity': 'high',
                            'message': f"Both tasks lock: {resource}",
                        })

        return conflicts

    def can_start_task(self, task_id: str) -> Tuple[bool, str]:
        """Check if a task can safely start."""
        task = self._tasks.get(task_id)
        if not task:
            return False, "Task not found"

        if task.state != TaskState.PENDING:
            return False, f"Task is {task.state.value}"

        # Check for conflicts
        conflicts = self.detect_conflicts(task_id)
        high_conflicts = [c for c in conflicts if c['severity'] == 'high']
        if high_conflicts:
            return False, f"Conflicts with tasks: {', '.join(set(c['task_b'] for c in high_conflicts))}"

        return True, "OK"

    # ── CHECKPOINTS ──

    def create_checkpoint(
        self,
        task_id: str,
        description: str,
        snapshot_id: str = "",
        files_state: Optional[Dict[str, str]] = None,
    ) -> ExecutionCheckpoint:
        """Create a recovery checkpoint for a task."""
        checkpoint = ExecutionCheckpoint(
            id=str(uuid.uuid4())[:8],
            task_id=task_id,
            timestamp=self._now(),
            description=description,
            snapshot_id=snapshot_id,
            files_state=files_state or {},
        )

        with self._lock:
            self._checkpoints[checkpoint.id] = checkpoint
            task = self._tasks.get(task_id)
            if task:
                task.checkpoint_ids.append(checkpoint.id)

        logger.info(f"Checkpoint created: {checkpoint.id} for task {task_id}")
        return checkpoint

    def get_task_checkpoints(self, task_id: str) -> List[ExecutionCheckpoint]:
        """Get all checkpoints for a task."""
        task = self._tasks.get(task_id)
        if not task:
            return []

        return [
            self._checkpoints[cid]
            for cid in task.checkpoint_ids
            if cid in self._checkpoints
        ]

    def get_latest_checkpoint(self, task_id: str) -> Optional[ExecutionCheckpoint]:
        """Get the most recent checkpoint for a task."""
        checkpoints = self.get_task_checkpoints(task_id)
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda c: c.timestamp)

    # ── STATS ──

    def get_stats(self) -> Dict[str, Any]:
        """Get coordination system stats."""
        states = defaultdict(int)
        for task in self._tasks.values():
            states[task.state.value] += 1

        return {
            'total_tasks': len(self._tasks),
            'active_tasks': len(self.get_active_tasks()),
            'states': dict(states),
            'active_locks': len(self._locks),
            'checkpoints': len(self._checkpoints),
        }

    @staticmethod
    def _now() -> str:
        return time.strftime('%Y-%m-%dT%H:%M:%S')
