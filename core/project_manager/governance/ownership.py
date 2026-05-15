"""
P12 — Ownership System.

Every subsystem has an owner, responsibility boundary,
allowed dependencies, risk level, and modification policy.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModificationPolicy(Enum):
    FREE = "free"           # anyone can modify
    REVIEW = "review"       # requires review
    APPROVAL = "approval"   # requires explicit approval
    LOCKED = "locked"       # no modifications without escalation


@dataclass
class SubsystemOwner:
    """Ownership information for a subsystem."""
    subsystem: str
    owner: str  # owner identifier (agent, team, or role)
    responsibility: str  # what this subsystem is responsible for
    allowed_dependencies: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    modification_policy: ModificationPolicy = ModificationPolicy.REVIEW
    max_lines: int = 500
    max_dependencies: int = 15
    description: str = ""


class OwnershipSystem:
    """
    Manages subsystem ownership.
    Every subsystem must have a clear owner and boundaries.
    """

    def __init__(self):
        self._owners: Dict[str, SubsystemOwner] = {}
        self._build_default_ownership()

    def _build_default_ownership(self) -> None:
        """Set up default ownership for all subsystems."""
        defaults = [
            SubsystemOwner(
                subsystem="pm_core",
                owner="platform-team",
                responsibility="Coordination kernel — facade for all subsystems",
                allowed_dependencies=["retrieval", "validation", "workflow", "lock_manager",
                                      "snapshot", "telemetry", "risk", "scheduler"],
                risk_level=RiskLevel.CRITICAL,
                modification_policy=ModificationPolicy.APPROVAL,
                max_lines=800,
                max_dependencies=10,
                description="ProjectManager core — must remain stable"
            ),
            SubsystemOwner(
                subsystem="retrieval",
                owner="platform-team",
                responsibility="Context retrieval pipeline — multi-stage retrieval",
                allowed_dependencies=["pm_core"],
                risk_level=RiskLevel.MEDIUM,
                modification_policy=ModificationPolicy.REVIEW,
                max_lines=500,
                max_dependencies=5,
                description="Retrieval service — read-only access to PM Core"
            ),
            SubsystemOwner(
                subsystem="validation",
                owner="platform-team",
                responsibility="Deterministic validation pipeline",
                allowed_dependencies=["pm_core"],
                risk_level=RiskLevel.HIGH,
                modification_policy=ModificationPolicy.REVIEW,
                max_lines=500,
                max_dependencies=3,
                description="Validation engine — pure function, no side effects"
            ),
            SubsystemOwner(
                subsystem="workflow",
                owner="platform-team",
                responsibility="Workflow execution engine",
                allowed_dependencies=["pm_core", "lock_manager", "snapshot"],
                risk_level=RiskLevel.HIGH,
                modification_policy=ModificationPolicy.REVIEW,
                max_lines=400,
                max_dependencies=5,
                description="Workflow runtime — coordinates task execution"
            ),
            SubsystemOwner(
                subsystem="lock_manager",
                owner="platform-team",
                responsibility="Resource locking and conflict prevention",
                allowed_dependencies=["pm_core"],
                risk_level=RiskLevel.HIGH,
                modification_policy=ModificationPolicy.APPROVAL,
                max_lines=400,
                max_dependencies=2,
                description="Lock manager — must be deadlock-free"
            ),
            SubsystemOwner(
                subsystem="snapshot",
                owner="platform-team",
                responsibility="Project snapshot and restore",
                allowed_dependencies=["pm_core"],
                risk_level=RiskLevel.MEDIUM,
                modification_policy=ModificationPolicy.REVIEW,
                max_lines=300,
                max_dependencies=2,
                description="Snapshot service — read-only relative to PM Core"
            ),
            SubsystemOwner(
                subsystem="telemetry",
                owner="platform-team",
                responsibility="Metrics, observability, and health monitoring",
                allowed_dependencies=["pm_core"],
                risk_level=RiskLevel.LOW,
                modification_policy=ModificationPolicy.REVIEW,
                max_lines=400,
                max_dependencies=2,
                description="Telemetry engine — passive observation only"
            ),
            SubsystemOwner(
                subsystem="risk",
                owner="platform-team",
                responsibility="Risk analysis and stability tracking",
                allowed_dependencies=["pm_core"],
                risk_level=RiskLevel.MEDIUM,
                modification_policy=ModificationPolicy.REVIEW,
                max_lines=400,
                max_dependencies=3,
                description="Risk engine — stateless analysis"
            ),
            SubsystemOwner(
                subsystem="scheduler",
                owner="platform-team",
                responsibility="Task scheduling and queue management",
                allowed_dependencies=["pm_core", "lock_manager"],
                risk_level=RiskLevel.MEDIUM,
                modification_policy=ModificationPolicy.REVIEW,
                max_lines=300,
                max_dependencies=3,
                description="Execution scheduler — deterministic task ordering"
            ),
            SubsystemOwner(
                subsystem="governance",
                owner="platform-team",
                responsibility="Platform governance, policies, and boundaries",
                allowed_dependencies=["pm_core"],
                risk_level=RiskLevel.CRITICAL,
                modification_policy=ModificationPolicy.APPROVAL,
                max_lines=600,
                max_dependencies=3,
                description="Governance layer — defines platform rules"
            ),
        ]
        for owner in defaults:
            self._owners[owner.subsystem] = owner

    def get_owner(self, subsystem: str) -> Optional[SubsystemOwner]:
        """Get ownership info for a subsystem."""
        return self._owners.get(subsystem)

    def set_owner(self, owner: SubsystemOwner) -> None:
        """Set or update ownership for a subsystem."""
        self._owners[owner.subsystem] = owner

    def check_modification_allowed(self, subsystem: str, modifier: str) -> tuple:
        """
        Check if a modification is allowed.
        Returns: (allowed, reason)
        """
        owner = self._owners.get(subsystem)
        if not owner:
            return True, "No ownership defined — allowed by default"

        if owner.modification_policy == ModificationPolicy.FREE:
            return True, "Free modification policy"
        elif owner.modification_policy == ModificationPolicy.REVIEW:
            return True, "Allowed with review required"
        elif owner.modification_policy == ModificationPolicy.APPROVAL:
            return False, f"Modification requires approval from {owner.owner}"
        elif owner.modification_policy == ModificationPolicy.LOCKED:
            return False, f"Subsystem is locked — contact {owner.owner} for escalation"

        return True, "Unknown policy — allowed by default"

    def get_all_owners(self) -> Dict[str, SubsystemOwner]:
        """Get all ownership records."""
        return dict(self._owners)

    def get_risk_report(self) -> Dict[str, Any]:
        """Get risk report for all subsystems."""
        by_risk = {}
        for risk in RiskLevel:
            subsystems = [o for o in self._owners.values() if o.risk_level == risk]
            if subsystems:
                by_risk[risk.value] = [s.subsystem for s in subsystems]
        return {
            'total_subsystems': len(self._owners),
            'by_risk': by_risk,
            'locked': [o.subsystem for o in self._owners.values()
                       if o.modification_policy == ModificationPolicy.LOCKED],
        }
