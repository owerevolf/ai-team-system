"""
semantic_memory.py — Multi-Layer Project Memory.

5 layers of project memory:
1. Active Task — current work context
2. Project Architecture — subsystem map, module responsibilities
3. Operational History — failures, fixes, fragile areas, rollbacks
4. Human Intent — project identity, anti-goals, philosophy
5. Governance — frozen areas, forbidden ops, approval policies

Principle: RAW CONTEXT DIES. COMPRESSED ENGINEERING MEMORY SURVIVES.
"""

from __future__ import annotations

import time
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


# ── Layer 1: Active Task ──

@dataclass
class ActiveTask:
    """Current task context."""
    task_id: str = ""
    title: str = ""
    objective: str = ""
    active_files: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    started_at: str = ""
    agent_id: str = ""


# ── Layer 2: Project Architecture ──

@dataclass
class SubsystemSummary:
    """Compressed subsystem knowledge."""
    name: str = ""
    role: str = ""
    key_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    integration_points: List[str] = field(default_factory=list)
    fragile_areas: List[str] = field(default_factory=list)
    last_updated: str = ""
    confidence: float = 1.0


@dataclass
class ArchitectureMap:
    """Compressed architecture understanding."""
    subsystems: Dict[str, SubsystemSummary] = field(default_factory=dict)
    module_responsibilities: Dict[str, str] = field(default_factory=dict)
    integration_boundaries: List[Tuple[str, str]] = field(default_factory=list)
    last_updated: str = ""


# ── Layer 3: Operational History ──

@dataclass
class FailureRecord:
    """A recorded failure."""
    failure_id: str = ""
    task_id: str = ""
    failure_type: str = ""  # test_failure, build_failure, regression, rollback
    description: str = ""
    files_involved: List[str] = field(default_factory=list)
    resolution: str = ""
    timestamp: str = ""
    is_resolved: bool = False
    recurrence_count: int = 1


@dataclass
class FragileArea:
    """A known fragile area."""
    area: str = ""  # file, module, or subsystem
    reason: str = ""
    incident_count: int = 0
    last_incident: str = ""
    recommended_care: str = ""


# ── Layer 4: Human Intent ──

@dataclass
class ProjectIdentity:
    """Project identity anchor."""
    name: str = ""
    purpose: str = ""
    target_audience: str = ""
    core_values: List[str] = field(default_factory=list)
    anti_goals: List[str] = field(default_factory=list)
    ux_philosophy: str = ""
    coding_preferences: List[str] = field(default_factory=list)
    educational_principles: List[str] = field(default_factory=list)
    last_updated: str = ""


# ── Layer 5: Governance ──

@dataclass
class FrozenZone:
    """A frozen area that should not be modified."""
    area: str = ""
    reason: str = ""
    frozen_since: str = ""
    authorized_by: str = ""


@dataclass
class GovernancePolicy:
    """A governance policy."""
    policy_id: str = ""
    name: str = ""
    description: str = ""
    forbidden_operations: List[str] = field(default_factory=list)
    approval_required_for: List[str] = field(default_factory=list)
    enabled: bool = True


class SemanticMemory:
    """
    Multi-layer project memory system.

    Stores compressed engineering understanding across 5 layers.
    Each layer serves a different purpose and has different update semantics.
    """

    def __init__(self, project_id: str = ""):
        self.project_id = project_id
        self._lock = threading.Lock()

        # Layer 1: Active Task
        self._active_task: Optional[ActiveTask] = None
        self._task_history: List[ActiveTask] = []

        # Layer 2: Architecture
        self._architecture = ArchitectureMap()

        # Layer 3: Operational History
        self._failures: Dict[str, FailureRecord] = {}
        self._fragile_areas: Dict[str, FragileArea] = {}
        self._rollback_history: List[Dict[str, Any]] = []

        # Layer 4: Human Intent
        self._identity = ProjectIdentity()

        # Layer 5: Governance
        self._frozen_zones: Dict[str, FrozenZone] = {}
        self._governance_policies: Dict[str, GovernancePolicy] = {}

        # Metadata
        self._created_at = datetime.utcnow().isoformat() + "Z"
        self._last_updated = self._created_at
        self._version = 0

    # ── Layer 1: Active Task ──

    def set_active_task(self, task: ActiveTask) -> None:
        """Set the current active task."""
        with self._lock:
            if self._active_task:
                self._task_history.append(self._active_task)
                # Keep last 100 tasks
                if len(self._task_history) > 100:
                    self._task_history = self._task_history[-100:]
            self._active_task = task
            self._touch()

    def get_active_task(self) -> Optional[ActiveTask]:
        """Get current active task."""
        return self._active_task

    def get_task_history(self, limit: int = 20) -> List[ActiveTask]:
        """Get recent task history."""
        return self._task_history[-limit:]

    def update_active_files(self, files: List[str]) -> None:
        """Update active files for current task."""
        with self._lock:
            if self._active_task:
                self._active_task.active_files = files
                self._touch()

    def update_active_constraints(self, constraints: List[str]) -> None:
        """Update constraints for current task."""
        with self._lock:
            if self._active_task:
                self._active_task.constraints = constraints
                self._touch()

    # ── Layer 2: Architecture ──

    def update_subsystem(self, name: str, role: str = "",
                         key_files: Optional[List[str]] = None,
                         dependencies: Optional[List[str]] = None,
                         integration_points: Optional[List[str]] = None,
                         fragile_areas: Optional[List[str]] = None) -> None:
        """Update a subsystem summary."""
        with self._lock:
            existing = self._architecture.subsystems.get(name)
            now = datetime.utcnow().isoformat() + "Z"

            if existing:
                if role:
                    existing.role = role
                if key_files is not None:
                    existing.key_files = key_files
                if dependencies is not None:
                    existing.dependencies = dependencies
                if integration_points is not None:
                    existing.integration_points = integration_points
                if fragile_areas is not None:
                    existing.fragile_areas = fragile_areas
                existing.last_updated = now
            else:
                self._architecture.subsystems[name] = SubsystemSummary(
                    name=name, role=role, key_files=key_files or [],
                    dependencies=dependencies or [],
                    integration_points=integration_points or [],
                    fragile_areas=fragile_areas or [],
                    last_updated=now,
                )

            self._architecture.last_updated = now
            self._touch()

    def get_subsystem(self, name: str) -> Optional[SubsystemSummary]:
        """Get a subsystem summary."""
        return self._architecture.subsystems.get(name)

    def get_all_subsystems(self) -> Dict[str, SubsystemSummary]:
        """Get all subsystem summaries."""
        return dict(self._architecture.subsystems)

    def set_module_responsibility(self, module: str, responsibility: str) -> None:
        """Set a module's responsibility."""
        with self._lock:
            self._architecture.module_responsibilities[module] = responsibility
            self._architecture.last_updated = datetime.utcnow().isoformat() + "Z"
            self._touch()

    def get_module_responsibility(self, module: str) -> str:
        """Get a module's responsibility."""
        return self._architecture.module_responsibilities.get(module, "")

    def get_architecture_summary(self) -> str:
        """Get compressed architecture summary for LLM context."""
        lines = ["# Architecture Summary", ""]

        if self._architecture.subsystems:
            lines.append("## Subsystems")
            for name, sub in self._architecture.subsystems.items():
                lines.append(f"### {name}")
                if sub.role:
                    lines.append(f"Role: {sub.role}")
                if sub.key_files:
                    lines.append(f"Key files: {', '.join(sub.key_files[:5])}")
                if sub.dependencies:
                    lines.append(f"Depends on: {', '.join(sub.dependencies)}")
                if sub.fragile_areas:
                    lines.append(f"Fragile: {', '.join(sub.fragile_areas)}")
                lines.append("")

        if self._architecture.module_responsibilities:
            lines.append("## Module Responsibilities")
            for mod, resp in list(self._architecture.module_responsibilities.items())[:20]:
                lines.append(f"- {mod}: {resp}")
            lines.append("")

        return "\n".join(lines)

    # ── Layer 3: Operational History ──

    def record_failure(self, failure_type: str, description: str,
                       files_involved: Optional[List[str]] = None,
                       task_id: str = "",
                       resolution: str = "") -> FailureRecord:
        """Record a failure."""
        with self._lock:
            # Check for recurring failure
            for existing in self._failures.values():
                if (existing.failure_type == failure_type and
                    existing.description == description and
                    not existing.is_resolved):
                    existing.recurrence_count += 1
                    self._touch()
                    return existing

            record = FailureRecord(
                failure_id=str(uuid.uuid4())[:8],
                task_id=task_id,
                failure_type=failure_type,
                description=description,
                files_involved=files_involved or [],
                resolution=resolution,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            self._failures[record.failure_id] = record
            self._touch()

            # Update fragile areas
            for f in (files_involved or []):
                self._mark_fragile(f, failure_type)

            return record

    def _mark_fragile(self, area: str, reason: str) -> None:
        """Mark an area as fragile."""
        existing = self._fragile_areas.get(area)
        now = datetime.utcnow().isoformat() + "Z"
        if existing:
            existing.incident_count += 1
            existing.last_incident = now
        else:
            self._fragile_areas[area] = FragileArea(
                area=area, reason=reason, incident_count=1,
                last_incident=now,
            )

    def resolve_failure(self, failure_id: str, resolution: str) -> bool:
        """Mark a failure as resolved."""
        with self._lock:
            record = self._failures.get(failure_id)
            if record:
                record.is_resolved = True
                record.resolution = resolution
                self._touch()
                return True
            return False

    def record_rollback(self, task_id: str, reason: str,
                        files_affected: Optional[List[str]] = None) -> None:
        """Record a rollback."""
        with self._lock:
            self._rollback_history.append({
                "task_id": task_id,
                "reason": reason,
                "files_affected": files_affected or [],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            # Keep last 50 rollbacks
            if len(self._rollback_history) > 50:
                self._rollback_history = self._rollback_history[-50:]
            self._touch()

    def get_fragile_areas(self) -> List[FragileArea]:
        """Get all fragile areas, sorted by incident count."""
        areas = sorted(
            self._fragile_areas.values(),
            key=lambda a: a.incident_count, reverse=True,
        )
        return areas

    def get_recurring_failures(self, min_count: int = 2) -> List[FailureRecord]:
        """Get recurring failures."""
        return [
            f for f in self._failures.values()
            if f.recurrence_count >= min_count
        ]

    def get_failure_history(self, limit: int = 20) -> List[FailureRecord]:
        """Get recent failures."""
        sorted_failures = sorted(
            self._failures.values(),
            key=lambda f: f.timestamp, reverse=True,
        )
        return sorted_failures[:limit]

    # ── Layer 4: Human Intent ──

    def set_identity(self, identity: ProjectIdentity) -> None:
        """Set project identity."""
        with self._lock:
            identity.last_updated = datetime.utcnow().isoformat() + "Z"
            self._identity = identity
            self._touch()

    def get_identity(self) -> ProjectIdentity:
        """Get project identity."""
        return self._identity

    def update_identity_field(self, field_name: str, value: Any) -> bool:
        """Update a single identity field."""
        with self._lock:
            if hasattr(self._identity, field_name):
                setattr(self._identity, field_name, value)
                self._identity.last_updated = datetime.utcnow().isoformat() + "Z"
                self._touch()
                return True
            return False

    def get_identity_summary(self) -> str:
        """Get compressed identity summary."""
        identity = self._identity
        lines = ["# Project Identity", ""]

        if identity.name:
            lines.append(f"**Name:** {identity.name}")
        if identity.purpose:
            lines.append(f"**Purpose:** {identity.purpose}")
        if identity.target_audience:
            lines.append(f"**Audience:** {identity.target_audience}")

        if identity.core_values:
            lines.append(f"\n**Core Values:** {', '.join(identity.core_values)}")
        if identity.anti_goals:
            lines.append(f"\n**Anti-Goals:** {', '.join(identity.anti_goals)}")
        if identity.ux_philosophy:
            lines.append(f"\n**UX Philosophy:** {identity.ux_philosophy}")
        if identity.coding_preferences:
            lines.append(f"\n**Coding Preferences:** {', '.join(identity.coding_preferences)}")
        if identity.educational_principles:
            lines.append(f"\n**Educational Principles:** {', '.join(identity.educational_principles)}")

        return "\n".join(lines)

    # ── Layer 5: Governance ──

    def add_frozen_zone(self, area: str, reason: str,
                        authorized_by: str = "human") -> None:
        """Add a frozen zone."""
        with self._lock:
            self._frozen_zones[area] = FrozenZone(
                area=area, reason=reason,
                frozen_since=datetime.utcnow().isoformat() + "Z",
                authorized_by=authorized_by,
            )
            self._touch()

    def remove_frozen_zone(self, area: str) -> bool:
        """Remove a frozen zone."""
        with self._lock:
            if area in self._frozen_zones:
                del self._frozen_zones[area]
                self._touch()
                return True
            return False

    def is_frozen(self, area: str) -> Tuple[bool, str]:
        """Check if an area is frozen. Returns (frozen, reason)."""
        zone = self._frozen_zones.get(area)
        if zone:
            return True, zone.reason
        # Check partial matches
        for zone_area, zone in self._frozen_zones.items():
            if zone_area in area or area in zone_area:
                return True, zone.reason
        return False, ""

    def get_frozen_zones(self) -> List[FrozenZone]:
        """Get all frozen zones."""
        return list(self._frozen_zones.values())

    def add_governance_policy(self, policy: GovernancePolicy) -> None:
        """Add a governance policy."""
        with self._lock:
            self._governance_policies[policy.policy_id] = policy
            self._touch()

    def check_operation_allowed(self, operation: str) -> Tuple[bool, str]:
        """Check if an operation is allowed by governance policies."""
        for policy in self._governance_policies.values():
            if not policy.enabled:
                continue
            if operation in policy.forbidden_operations:
                return False, f"Operation '{operation}' is forbidden by policy '{policy.name}'"
        return True, "OK"

    # ── Utility ──

    def _touch(self) -> None:
        """Update metadata."""
        self._last_updated = datetime.utcnow().isoformat() + "Z"
        self._version += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "project_id": self.project_id,
            "version": self._version,
            "created_at": self._created_at,
            "last_updated": self._last_updated,
            "layers": {
                "active_task": self._active_task is not None,
                "task_history": len(self._task_history),
                "subsystems": len(self._architecture.subsystems),
                "module_responsibilities": len(self._architecture.module_responsibilities),
                "failures": len(self._failures),
                "fragile_areas": len(self._fragile_areas),
                "rollbacks": len(self._rollback_history),
                "frozen_zones": len(self._frozen_zones),
                "governance_policies": len(self._governance_policies),
            },
        }

    def build_context_snapshot(self) -> Dict[str, Any]:
        """Build a complete context snapshot for LLM consumption."""
        return {
            "identity": {
                "name": self._identity.name,
                "purpose": self._identity.purpose,
                "core_values": self._identity.core_values,
                "anti_goals": self._identity.anti_goals,
            },
            "active_task": {
                "title": self._active_task.title if self._active_task else "",
                "objective": self._active_task.objective if self._active_task else "",
                "active_files": self._active_task.active_files if self._active_task else [],
                "constraints": self._active_task.constraints if self._active_task else [],
            } if self._active_task else None,
            "architecture": {
                name: {
                    "role": s.role,
                    "key_files": s.key_files[:3],
                    "fragile_areas": s.fragile_areas,
                }
                for name, s in self._architecture.subsystems.items()
            },
            "fragile_areas": [
                {"area": f.area, "incidents": f.incident_count, "reason": f.reason}
                for f in self.get_fragile_areas()[:10]
            ],
            "frozen_zones": [
                {"area": z.area, "reason": z.reason}
                for z in self._frozen_zones.values()
            ],
            "recurring_failures": [
                {"type": f.failure_type, "count": f.recurrence_count, "desc": f.description}
                for f in self.get_recurring_failures()
            ],
        }
