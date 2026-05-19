"""
Project Brain — single source of truth for a project.

Stores everything the system knows about a project:
- what it is
- how it's built
- what we're doing
- what we decided
- what we must NOT do
- what could go wrong

Deterministic. Serializable. No AI opinions — only facts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RuntimeState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    UNDERSTANDING = "understanding"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    BLOCKED = "blocked"


class TaskStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TechStack:
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    databases: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    devops: List[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = []
        if self.languages:
            parts.append(f"Languages: {', '.join(self.languages)}")
        if self.frameworks:
            parts.append(f"Frameworks: {', '.join(self.frameworks)}")
        if self.databases:
            parts.append(f"DB: {', '.join(self.databases)}")
        if self.tools:
            parts.append(f"Tools: {', '.join(self.tools)}")
        if self.devops:
            parts.append(f"DevOps: {', '.join(self.devops)}")
        return " | ".join(parts) if parts else "Unknown"


@dataclass
class RepoMap:
    entrypoints: List[str] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0

    def summary(self) -> str:
        parts = []
        if self.entrypoints:
            parts.append(f"Entry: {', '.join(self.entrypoints[:3])}")
        if self.modules:
            parts.append(f"{len(self.modules)} modules")
        if self.services:
            parts.append(f"{len(self.services)} services")
        parts.append(f"{self.total_files} files")
        return " | ".join(parts) if parts else "Empty repo"


@dataclass
class ArchitectureSummary:
    pattern: str = ""  # monolith, microservices, layered, etc
    layers: List[str] = field(default_factory=list)
    key_components: List[str] = field(default_factory=list)
    data_flow: str = ""
    description: str = ""

    def summary(self) -> str:
        if self.description:
            return self.description
        parts = []
        if self.pattern:
            parts.append(self.pattern)
        if self.layers:
            parts.append(f"layers: {', '.join(self.layers)}")
        if self.key_components:
            parts.append(f"components: {', '.join(self.key_components[:5])}")
        return " | ".join(parts) if parts else "Not analyzed"


@dataclass
class Goal:
    id: str = ""
    title: str = ""
    description: str = ""
    status: str = "active"  # active, completed, cancelled
    priority: Priority = Priority.MEDIUM
    created_at: str = ""
    completed_at: str = ""


@dataclass
class Task:
    id: str = ""
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.ACTIVE
    priority: Priority = Priority.MEDIUM
    owner_agent: str = ""
    created_at: str = ""
    completed_at: str = ""


@dataclass
class Decision:
    id: str = ""
    title: str = ""
    context: str = ""
    decision: str = ""
    alternatives: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    created_at: str = ""


@dataclass
class Constraint:
    id: str = ""
    rule: str = ""
    reason: str = ""
    severity: str = "hard"  # hard = must never break, soft = prefer not to


@dataclass
class Risk:
    id: str = ""
    description: str = ""
    likelihood: str = "medium"  # low, medium, high
    impact: str = "medium"
    mitigation: str = ""


@dataclass
class MemorySnapshot:
    id: str = ""
    timestamp: str = ""
    summary: str = ""
    key_facts: List[str] = field(default_factory=list)
    context_tokens: int = 0


@dataclass
class ProjectBrain:
    """
    Single source of truth for a project.

    All agents read from ProjectBrain.
    No agent has its own truth.
    """

    # Identity
    project_id: str = ""
    project_name: str = ""
    created_at: str = ""
    updated_at: str = ""

    # Understanding
    project_summary: str = ""
    architecture: ArchitectureSummary = field(default_factory=ArchitectureSummary)
    tech_stack: TechStack = field(default_factory=TechStack)
    repo_map: RepoMap = field(default_factory=RepoMap)
    coding_standards: List[str] = field(default_factory=list)

    # Work
    active_goals: List[Goal] = field(default_factory=list)
    active_tasks: List[Task] = field(default_factory=list)
    completed_tasks: List[Task] = field(default_factory=list)
    blocked_tasks: List[Task] = field(default_factory=list)

    # Knowledge
    decisions: List[Decision] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    known_risks: List[Risk] = field(default_factory=list)

    # Memory
    memory_snapshots: List[MemorySnapshot] = field(default_factory=list)
    conversation_summary: str = ""

    # State
    current_focus: str = ""
    current_phase: str = ""
    runtime_state: str = RuntimeState.IDLE.value

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def add_goal(self, title: str, description: str = "",
                 priority: Priority = Priority.MEDIUM) -> Goal:
        goal = Goal(
            id=f"g{len(self.active_goals) + 1}",
            title=title,
            description=description,
            priority=priority,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.active_goals.append(goal)
        self.touch()
        return goal

    def add_task(self, title: str, description: str = "",
                 priority: Priority = Priority.MEDIUM,
                 owner_agent: str = "") -> Task:
        task = Task(
            id=f"t{len(self.active_tasks) + len(self.completed_tasks) + 1}",
            title=title,
            description=description,
            priority=priority,
            owner_agent=owner_agent,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.active_tasks.append(task)
        self.touch()
        return task

    def complete_task(self, task_id: str) -> bool:
        for i, t in enumerate(self.active_tasks):
            if t.id == task_id:
                t.status = TaskStatus.COMPLETED
                t.completed_at = datetime.utcnow().isoformat() + "Z"
                self.completed_tasks.append(t)
                self.active_tasks.pop(i)
                self.touch()
                return True
        return False

    def add_decision(self, title: str, decision: str,
                     context: str = "",
                     alternatives: Optional[List[str]] = None,
                     consequences: Optional[List[str]] = None) -> Decision:
        d = Decision(
            id=f"d{len(self.decisions) + 1}",
            title=title,
            context=context,
            decision=decision,
            alternatives=alternatives or [],
            consequences=consequences or [],
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.decisions.append(d)
        self.touch()
        return d

    def add_constraint(self, rule: str, reason: str = "",
                       severity: str = "hard") -> Constraint:
        c = Constraint(
            id=f"c{len(self.constraints) + 1}",
            rule=rule,
            reason=reason,
            severity=severity,
        )
        self.constraints.append(c)
        self.touch()
        return c

    def add_risk(self, description: str, likelihood: str = "medium",
                 impact: str = "medium", mitigation: str = "") -> Risk:
        r = Risk(
            id=f"r{len(self.known_risks) + 1}",
            description=description,
            likelihood=likelihood,
            impact=impact,
            mitigation=mitigation,
        )
        self.known_risks.append(r)
        self.touch()
        return r

    def add_snapshot(self, summary: str, key_facts: Optional[List[str]] = None,
                     context_tokens: int = 0) -> MemorySnapshot:
        snap = MemorySnapshot(
            id=f"s{len(self.memory_snapshots) + 1}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            summary=summary,
            key_facts=key_facts or [],
            context_tokens=context_tokens,
        )
        self.memory_snapshots.append(snap)
        self.touch()
        return snap

    def set_runtime_state(self, state: RuntimeState) -> None:
        self.runtime_state = state.value
        self.touch()

    def get_active_task_count(self) -> int:
        return len(self.active_tasks)

    def get_completed_task_count(self) -> int:
        return len(self.completed_tasks)

    def get_blocked_task_count(self) -> int:
        return len(self.blocked_tasks)

    def summary(self) -> str:
        parts = [
            f"Project: {self.project_name}",
            f"Phase: {self.current_phase or 'N/A'}",
            f"State: {self.runtime_state}",
            f"Tasks: {self.get_active_task_count()} active, "
            f"{self.get_completed_task_count()} done, "
            f"{self.get_blocked_task_count()} blocked",
        ]
        if self.tech_stack.summary():
            parts.append(f"Stack: {self.tech_stack.summary()}")
        if self.current_focus:
            parts.append(f"Focus: {self.current_focus}")
        return "\n".join(parts)


class BrainEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Enum):
            return o.value
        if hasattr(o, '__dataclass_fields__'):
            return {k: v for k, v in o.__dict__.items()}
        return super().default(o)


def brain_to_dict(brain: ProjectBrain) -> Dict[str, Any]:
    return json.loads(json.dumps(brain, cls=BrainEncoder))


def brain_from_dict(data: Dict[str, Any]) -> ProjectBrain:
    """Reconstruct a ProjectBrain from a dictionary."""
    brain = ProjectBrain(
        project_id=data.get("project_id", ""),
        project_name=data.get("project_name", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        project_summary=data.get("project_summary", ""),
        coding_standards=data.get("coding_standards", []),
        conversation_summary=data.get("conversation_summary", ""),
        current_focus=data.get("current_focus", ""),
        current_phase=data.get("current_phase", ""),
        runtime_state=data.get("runtime_state", RuntimeState.IDLE.value),
    )

    # Architecture
    arch = data.get("architecture", {})
    if arch:
        brain.architecture = ArchitectureSummary(
            pattern=arch.get("pattern", ""),
            layers=arch.get("layers", []),
            key_components=arch.get("key_components", []),
            data_flow=arch.get("data_flow", ""),
            description=arch.get("description", ""),
        )

    # Tech stack
    ts = data.get("tech_stack", {})
    if ts:
        brain.tech_stack = TechStack(
            languages=ts.get("languages", []),
            frameworks=ts.get("frameworks", []),
            databases=ts.get("databases", []),
            tools=ts.get("tools", []),
            devops=ts.get("devops", []),
        )

    # Repo map
    rm = data.get("repo_map", {})
    if rm:
        brain.repo_map = RepoMap(
            entrypoints=rm.get("entrypoints", []),
            modules=rm.get("modules", []),
            services=rm.get("services", []),
            tests=rm.get("tests", []),
            config_files=rm.get("config_files", []),
            total_files=rm.get("total_files", 0),
            total_lines=rm.get("total_lines", 0),
        )

    # Goals
    for g in data.get("active_goals", []):
        brain.active_goals.append(Goal(
            id=g.get("id", ""),
            title=g.get("title", ""),
            description=g.get("description", ""),
            status=g.get("status", "active"),
            priority=Priority(g.get("priority", "medium")),
            created_at=g.get("created_at", ""),
            completed_at=g.get("completed_at", ""),
        ))

    # Tasks
    for t in data.get("active_tasks", []):
        brain.active_tasks.append(Task(
            id=t.get("id", ""),
            title=t.get("title", ""),
            description=t.get("description", ""),
            status=TaskStatus(t.get("status", "active")),
            priority=Priority(t.get("priority", "medium")),
            owner_agent=t.get("owner_agent", ""),
            created_at=t.get("created_at", ""),
            completed_at=t.get("completed_at", ""),
        ))

    for t in data.get("completed_tasks", []):
        brain.completed_tasks.append(Task(
            id=t.get("id", ""),
            title=t.get("title", ""),
            description=t.get("description", ""),
            status=TaskStatus(t.get("status", "completed")),
            priority=Priority(t.get("priority", "medium")),
            owner_agent=t.get("owner_agent", ""),
            created_at=t.get("created_at", ""),
            completed_at=t.get("completed_at", ""),
        ))

    for t in data.get("blocked_tasks", []):
        brain.blocked_tasks.append(Task(
            id=t.get("id", ""),
            title=t.get("title", ""),
            description=t.get("description", ""),
            status=TaskStatus(t.get("status", "blocked")),
            priority=Priority(t.get("priority", "medium")),
            owner_agent=t.get("owner_agent", ""),
            created_at=t.get("created_at", ""),
            completed_at=t.get("completed_at", ""),
        ))

    # Decisions
    for d in data.get("decisions", []):
        brain.decisions.append(Decision(
            id=d.get("id", ""),
            title=d.get("title", ""),
            context=d.get("context", ""),
            decision=d.get("decision", ""),
            alternatives=d.get("alternatives", []),
            consequences=d.get("consequences", []),
            created_at=d.get("created_at", ""),
        ))

    # Constraints
    for c in data.get("constraints", []):
        brain.constraints.append(Constraint(
            id=c.get("id", ""),
            rule=c.get("rule", ""),
            reason=c.get("reason", ""),
            severity=c.get("severity", "hard"),
        ))

    # Risks
    for r in data.get("known_risks", []):
        brain.known_risks.append(Risk(
            id=r.get("id", ""),
            description=r.get("description", ""),
            likelihood=r.get("likelihood", "medium"),
            impact=r.get("impact", "medium"),
            mitigation=r.get("mitigation", ""),
        ))

    # Snapshots
    for s in data.get("memory_snapshots", []):
        brain.memory_snapshots.append(MemorySnapshot(
            id=s.get("id", ""),
            timestamp=s.get("timestamp", ""),
            summary=s.get("summary", ""),
            key_facts=s.get("key_facts", []),
            context_tokens=s.get("context_tokens", 0),
        ))

    return brain
