"""
Phase 12, P2: Workflow Path Compression

Analyzes and compresses operational workflow paths:
- median workflow length
- interruption count
- approval chains
- recovery friction
- navigation depth

Principle: Fewer steps without hidden automation.
Remove ceremony, not safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StepType(Enum):
    VALIDATION = "validation"
    APPROVAL = "approval"
    CONFIRMATION = "confirmation"
    EXPLANATION = "explanation"
    STATE_TRANSITION = "state_transition"
    RECOVERY = "recovery"
    NOTIFICATION = "notification"


@dataclass
class WorkflowStep:
    """A single step in an operational workflow."""
    name: str
    step_type: StepType
    is_blocking: bool = True
    is_redundant: bool = False
    can_batch: bool = False
    merge_group: str = ""


@dataclass
class WorkflowPath:
    """A complete workflow from trigger to completion."""
    name: str
    steps: list[WorkflowStep] = field(default_factory=list)
    description: str = ""

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def blocking_steps(self) -> list[WorkflowStep]:
        return [s for s in self.steps if s.is_blocking]

    @property
    def redundant_steps(self) -> list[WorkflowStep]:
        return [s for s in self.steps if s.is_redundant]

    @property
    def batched_steps(self) -> list[list[WorkflowStep]]:
        """Group steps that can be batched together."""
        groups: dict[str, list[WorkflowStep]] = {}
        for step in self.steps:
            if step.can_batch and step.merge_group:
                groups.setdefault(step.merge_group, []).append(step)
        return [g for g in groups.values() if len(g) > 1]


@dataclass
class CompressionResult:
    """Result of workflow compression analysis."""
    original_path: WorkflowPath
    compressed_length: int
    removed_steps: list[str] = field(default_factory=list)
    batched_groups: list[list[str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def compression_ratio(self) -> float:
        if self.original_path.length == 0:
            return 1.0
        return self.compressed_length / self.original_path.length

    @property
    def steps_saved(self) -> int:
        return self.original_path.length - self.compressed_length


class WorkflowPathCompressor:
    """
    Analyzes registered workflow paths and produces compression plans.
    Identifies redundant steps, batchable groups, and unnecessary ceremony.
    """

    def __init__(self) -> None:
        self._paths: dict[str, WorkflowPath] = {}

    def register(self, path: WorkflowPath) -> None:
        """Register a workflow path for analysis."""
        self._paths[path.name] = path

    def analyze(self, path_name: str) -> CompressionResult:
        """Analyze a single workflow path for compression opportunities."""
        path = self._paths.get(path_name)
        if not path:
            return CompressionResult(
                original_path=WorkflowPath(name=path_name),
                compressed_length=0,
                warnings=[f"Unknown workflow: {path_name}"],
            )

        removed: list[str] = []
        batched: list[list[str]] = []
        warnings: list[str] = []
        kept_steps: list[WorkflowStep] = []

        # Remove redundant steps
        for step in path.steps:
            if step.is_redundant:
                removed.append(step.name)
            else:
                kept_steps.append(step)

        # Batch mergeable groups
        batch_groups = path.batched_steps
        for group in batch_groups:
            names = [s.name for s in group]
            batched.append(names)
            # Keep only first step from each batch
            for s in group[1:]:
                if s.name not in removed:
                    removed.append(s.name)
                    if s in kept_steps:
                        kept_steps.remove(s)

        # Warn about long approval chains
        approval_chain = [s for s in kept_steps if s.step_type == StepType.APPROVAL]
        if len(approval_chain) > 3:
            warnings.append(
                f"Approval chain has {len(approval_chain)} steps — consider reducing"
            )

        # Warn about excessive confirmations
        confirmations = [s for s in kept_steps if s.step_type == StepType.CONFIRMATION]
        if len(confirmations) > 2:
            warnings.append(
                f"Workflow has {len(confirmations)} confirmations — risk of confirmation fatigue"
            )

        return CompressionResult(
            original_path=path,
            compressed_length=len(kept_steps),
            removed_steps=removed,
            batched_groups=batched,
            warnings=warnings,
        )

    def analyze_all(self) -> dict[str, CompressionResult]:
        """Analyze all registered workflow paths."""
        return {name: self.analyze(name) for name in self._paths}

    @property
    def median_path_length(self) -> float:
        if not self._paths:
            return 0.0
        lengths = sorted(p.length for p in self._paths.values())
        n = len(lengths)
        if n % 2 == 1:
            return float(lengths[n // 2])
        return (lengths[n // 2 - 1] + lengths[n // 2]) / 2.0

    @property
    def total_steps(self) -> int:
        return sum(p.length for p in self._paths.values())

    @property
    def total_redundant(self) -> int:
        return sum(len(p.redundant_steps) for p in self._paths.values())
