"""
Execution Plan — structured execution plan.

Not text. A structured model.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanStatus(Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class PhaseStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanPhase:
    """A single phase in the execution plan."""
    id: str = ""
    name: str = ""
    description: str = ""
    status: str = PhaseStatus.PENDING.value
    order: int = 0
    task_ids: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # phase IDs
    estimated_effort: str = "medium"  # low, medium, high


@dataclass
class PlanTask:
    """A task within an execution plan."""
    id: str = ""
    title: str = ""
    description: str = ""
    task_type: str = ""
    assigned_agent: str = ""
    skills: List[str] = field(default_factory=list)
    status: str = "pending"
    phase_id: str = ""
    dependencies: List[str] = field(default_factory=list)  # task IDs
    priority: str = "medium"
    estimated_complexity: str = "medium"
    allowed_files: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """
    Structured execution plan.

    Contains everything needed to execute a task:
    - phases (ordered steps)
    - tasks (with agent assignments)
    - dependencies
    - validation strategy
    - rollback strategy
    """

    plan_id: str = ""
    project_id: str = ""
    objective: str = ""
    summary: str = ""
    status: str = PlanStatus.DRAFT.value
    created_at: str = ""
    updated_at: str = ""

    # Plan structure
    phases: List[PlanPhase] = field(default_factory=list)
    tasks: List[PlanTask] = field(default_factory=list)

    # Analysis
    estimated_complexity: str = "medium"
    risks: List[str] = field(default_factory=list)
    affected_areas: List[str] = field(default_factory=list)

    # Strategy
    validation_strategy: str = ""
    rollback_strategy: str = ""

    # Results
    completed_tasks: int = 0
    failed_tasks: int = 0
    blocked_tasks: int = 0

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
        if not self.updated_at:
            self.updated_at = self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def add_phase(self, name: str, description: str = "",
                  order: int = 0) -> PlanPhase:
        phase = PlanPhase(
            id=f"ph{len(self.phases) + 1}",
            name=name,
            description=description,
            order=order,
        )
        self.phases.append(phase)
        self.phases.sort(key=lambda p: p.order)
        self.touch()
        return phase

    def add_task(self, title: str, task_type: str = "",
                 assigned_agent: str = "", phase_id: str = "",
                 description: str = "", priority: str = "medium",
                 skills: Optional[List[str]] = None) -> PlanTask:
        task = PlanTask(
            id=f"t{len(self.tasks) + 1}",
            title=title,
            description=description,
            task_type=task_type,
            assigned_agent=assigned_agent,
            skills=skills or [],
            phase_id=phase_id,
            priority=priority,
        )
        self.tasks.append(task)
        # Add to phase
        if phase_id:
            for phase in self.phases:
                if phase.id == phase_id:
                    phase.task_ids.append(task.id)
                    break
        self.touch()
        return task

    def get_task(self, task_id: str) -> Optional[PlanTask]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def get_phase(self, phase_id: str) -> Optional[PlanPhase]:
        for p in self.phases:
            if p.id == phase_id:
                return p
        return None

    def get_tasks_by_phase(self, phase_id: str) -> List[PlanTask]:
        return [t for t in self.tasks if t.phase_id == phase_id]

    def get_tasks_by_agent(self, agent_id: str) -> List[PlanTask]:
        return [t for t in self.tasks if t.assigned_agent == agent_id]

    def get_tasks_by_status(self, status: str) -> List[PlanTask]:
        return [t for t in self.tasks if t.status == status]

    def get_next_pending_task(self) -> Optional[PlanTask]:
        """Get the next pending task that has all dependencies met."""
        completed_ids = {t.id for t in self.tasks
                        if t.status == "completed"}
        for task in self.tasks:
            if task.status == "pending":
                deps_met = all(d in completed_ids
                              for d in task.dependencies)
                if deps_met:
                    return task
        return None

    def update_task_status(self, task_id: str, status: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        task.status = status
        if status == "completed":
            self.completed_tasks += 1
        elif status == "failed":
            self.failed_tasks += 1
        elif status == "blocked":
            self.blocked_tasks += 1
        self.touch()
        return True

    def get_progress(self) -> Dict[str, Any]:
        total = len(self.tasks)
        if total == 0:
            return {"total": 0, "completed": 0, "percent": 0}
        completed = len([t for t in self.tasks if t.status == "completed"])
        return {
            "total": total,
            "completed": completed,
            "failed": self.failed_tasks,
            "blocked": self.blocked_tasks,
            "pending": len([t for t in self.tasks if t.status == "pending"]),
            "percent": round(completed / total * 100, 1),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "objective": self.objective,
            "summary": self.summary,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "phases": [p.__dict__ for p in self.phases],
            "tasks": [t.__dict__ for t in self.tasks],
            "estimated_complexity": self.estimated_complexity,
            "risks": self.risks,
            "affected_areas": self.affected_areas,
            "validation_strategy": self.validation_strategy,
            "rollback_strategy": self.rollback_strategy,
            "progress": self.get_progress(),
        }
