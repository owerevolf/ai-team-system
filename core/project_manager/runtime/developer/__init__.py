"""
Developer Mode — Project Brain & Understanding Runtime.

This package provides the orchestration foundation for Developer Mode:
- ProjectBrain: single source of truth for project state
- BrainStore: JSON persistence for project brains
- UnderstandingEngine: understand-before-execution philosophy
- TaskContracts: scoped execution contracts for agents
- ContextLayers: layered context to stay under 150k tokens
- Orchestrator: main orchestration runtime
- TeamLeadRuntime: central orchestrator
- AgentRegistry: unified agent registry
- SkillRouter: skill-to-agent routing
- ExecutionPlan: structured execution plan
- ExecutionMemory: execution timeline
- SafeReview: validation layer
- PatchEngine: patch-based changes (NO direct writes)
- WorkspaceRuntime: isolated workspace system
- RepoScanner: project understanding
- KnowledgeIndex: context compression
- ExecutionSandbox: governed execution boundary
- ApprovalRuntime: human approval flow
- TaskExecutor: controlled worker runtime
- DeveloperTerminal: safe terminal abstraction

Phase 19A-19D — Foundation only. No autonomous coding.
"""

from .project_brain import (
    ProjectBrain, ArchitectureSummary, RepoMap, TechStack,
    Goal, Task, Decision, Constraint, Risk, MemorySnapshot,
    RuntimeState, BrainEncoder, brain_to_dict, brain_from_dict,
)
from .brain_store import BrainStore
from .understanding_engine import UnderstandingEngine, UnderstandingResult
from .task_contracts import TaskContract, TaskContractBuilder
from .context_layers import ContextLayers, ContextLayer
from .orchestrator import Orchestrator, OrchestratorStatus
from .teamlead_runtime import TeamLeadRuntime, OrchestrationResult
from .agent_registry import AgentRegistry, AgentProfile, AgentCapabilities
from .skill_router import SkillRouter, SkillAssignment
from .execution_memory import ExecutionMemory, ExecutionRecord
from .execution_plan import ExecutionPlan, PlanPhase, PlanTask
from .safe_review import SafeReview, ReviewResult, ReviewViolation
from .runtime_events import EventBus, RuntimeEvent, EventType, EventSeverity
from .patch_engine import PatchEngine, Patch, PatchStatus, RiskLevel, FilePatch
from .workspace_runtime import WorkspaceRuntime, Workspace, WorkspaceSnapshot
from .repo_scanner import RepoScanner, RepoMap as ScannedRepoMap
from .knowledge_index import KnowledgeIndex, KnowledgeEntry
from .execution_sandbox import ExecutionSandbox, SandboxResult, SandboxPolicy
from .approval_runtime import ApprovalRuntime, ApprovalRequest, ApprovalLevel, ApprovalStatus
from .task_executor import TaskExecutor, ExecutionResult
from .developer_terminal import DeveloperTerminal, TerminalCommand

__all__ = [
    # Phase 19B
    "ProjectBrain", "BrainStore", "UnderstandingEngine", "TaskContract",
    "ContextLayers", "brain_to_dict", "brain_from_dict",
    # Phase 19C
    "Orchestrator", "TeamLeadRuntime", "AgentRegistry", "SkillRouter",
    "ExecutionMemory", "ExecutionPlan", "SafeReview", "EventBus",
    # Phase 19D
    "PatchEngine", "WorkspaceRuntime", "RepoScanner", "KnowledgeIndex",
    "ExecutionSandbox", "ApprovalRuntime", "TaskExecutor", "DeveloperTerminal",
]
