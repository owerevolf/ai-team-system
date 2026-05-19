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

from .project_brain import (
    ProjectBrain,
    ArchitectureSummary,
    RepoMap,
    TechStack,
    Goal,
    Task,
    Decision,
    Constraint,
    Risk,
    MemorySnapshot,
    RuntimeState,
    BrainEncoder,
    brain_to_dict,
    brain_from_dict,
)
from .brain_store import BrainStore
from .understanding_engine import UnderstandingEngine, UnderstandingResult
from .task_contracts import TaskContract, TaskContractBuilder
from .context_layers import ContextLayers, ContextLayer

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
