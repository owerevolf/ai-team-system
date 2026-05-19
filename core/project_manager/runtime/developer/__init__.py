"""
Developer Mode — Project Brain & Understanding Runtime.

This package provides the orchestration foundation for Developer Mode:
- ProjectBrain: single source of truth for project state
- BrainStore: JSON persistence for project brains
- UnderstandingEngine: understand-before-execution philosophy
- TaskContracts: scoped execution contracts for agents
- ContextLayers: layered context to stay under 150k tokens
- DeveloperAPI: FastAPI endpoints for developer mode

Phase 19B — Foundation only. No autonomous coding.
"""

from .orchestrator import Orchestrator, OrchestratorStatus
from .teamlead_runtime import TeamLeadRuntime, OrchestrationResult
from .agent_registry import AgentRegistry, AgentProfile, AgentCapabilities, AgentRole, RiskLevel
from .skill_router import SkillRouter, SkillAssignment
from .execution_memory import ExecutionMemory, ExecutionRecord
from .execution_plan import ExecutionPlan, PlanPhase, PlanTask, PlanStatus
from .safe_review import SafeReview, ReviewResult, ReviewViolation, ReviewStatus, ViolationType
from .runtime_events import EventBus, RuntimeEvent, EventType, EventSeverity

__all__ = [
    "ProjectBrain",
    "ArchitectureSummary",
    "RepoMap",
    "TechStack",
    "Goal",
    "Task",
    "Decision",
    "Constraint",
    "Risk",
    "MemorySnapshot",
    "RuntimeState",
    "BrainEncoder",
    "brain_to_dict",
    "brain_from_dict",
    "BrainStore",
    "UnderstandingEngine",
    "UnderstandingResult",
    "TaskContract",
    "TaskContractBuilder",
    "ContextLayers",
    "ContextLayer",
]
