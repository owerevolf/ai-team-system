"""
knowledge_runtime.py — Knowledge Operating System.

Main coordinator for the memory system.

Flow:
  repo changes → update summaries → detect drift → compress context → update memory index → update architectural memory → update intent links

This is the knowledge operating system.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .semantic_memory import SemanticMemory, ActiveTask, ProjectIdentity
from .context_compressor import ContextCompressor, CompressedContext
from .memory_index import MemoryIndex
from .drift_detection import DriftDetector, DriftReport
from .token_budget import TokenBudget, BudgetReport
from .intent_preservation import IntentPreservation
from .architectural_memory import ArchitecturalMemory
from .failure_memory import FailureMemory
from .memory_governor import MemoryGovernor, GovernorAction


class KnowledgeRuntime:
    """
    Knowledge operating system.
    Coordinates all memory subsystems.
    """

    def __init__(self, project_id: str = "", project_root: str = ".",
                 max_tokens: int = 150_000):
        self.project_id = project_id
        self._project_root = project_root

        # Core memory systems
        self.semantic_memory = SemanticMemory(project_id)
        self.memory_index = MemoryIndex()
        self.context_compressor = ContextCompressor(max_tokens)
        self.drift_detector = DriftDetector(project_root)
        self.token_budget = TokenBudget(max_tokens)
        self.intent_preservation = IntentPreservation()
        self.architectural_memory = ArchitecturalMemory()
        self.failure_memory = FailureMemory()
        self.memory_governor = MemoryGovernor()

        self._lock = threading.Lock()
        self._version = 0
        self._last_update = datetime.utcnow().isoformat() + "Z"

    # ── Task Lifecycle ──

    def start_task(self, task_id: str, title: str, objective: str,
                   agent_id: str = "", active_files: Optional[List[str]] = None,
                   constraints: Optional[List[str]] = None) -> None:
        """Start a new task, updating memory."""
        task = ActiveTask(
            task_id=task_id, title=title, objective=objective,
            agent_id=agent_id, active_files=active_files or [],
            constraints=constraints or [],
            started_at=datetime.utcnow().isoformat() + "Z",
        )
        self.semantic_memory.set_active_task(task)
        self._touch()

    def complete_task(self, task_id: str, success: bool,
                      summary: str = "") -> None:
        """Complete a task, updating memory."""
        task = self.semantic_memory.get_active_task()
        if task and task.task_id == task_id:
            if not success:
                self.failure_memory.record_failure(
                    failure_type="task_failure",
                    description=f"Task '{task.title}' failed: {summary}",
                    files_involved=task.active_files,
                )
            self._touch()

    # ── Memory Updates ──

    def update_subsystem(self, name: str, role: str = "",
                         key_files: Optional[List[str]] = None,
                         dependencies: Optional[List[str]] = None,
                         fragile_areas: Optional[List[str]] = None) -> None:
        """Update a subsystem in memory."""
        self.semantic_memory.update_subsystem(
            name, role, key_files, dependencies,
            integration_points=None, fragile_areas=fragile_areas,
        )

        # Also update memory index
        summary = f"{name}: {role}"
        if fragile_areas:
            summary += f" (fragile: {', '.join(fragile_areas)})"
        self.memory_index.add_entry(
            category="subsystem", key=name, summary=summary,
            importance=8, tags=["subsystem", name],
        )

        self._touch()

    def record_failure(self, failure_type: str, description: str,
                       files_involved: Optional[List[str]] = None,
                       task_id: str = "") -> None:
        """Record a failure across all memory systems."""
        # Semantic memory
        self.semantic_memory.record_failure(
            failure_type, description, files_involved, task_id,
        )

        # Failure memory
        pattern = self.failure_memory.record_failure(
            failure_type, description, files_involved,
        )

        # Memory index
        if pattern.occurrences >= 2:
            self.memory_index.add_entry(
                category="failure", key=pattern.signature,
                summary=description, importance=9,
                tags=["failure", failure_type, "recurring"],
            )

        self._touch()

    def record_rollback(self, task_id: str, reason: str,
                        files_affected: Optional[List[str]] = None) -> None:
        """Record a rollback."""
        self.semantic_memory.record_rollback(task_id, reason, files_affected)
        self.failure_memory.record_rollback(task_id, reason, files_affected)
        self._touch()

    # ── Context Building ──

    def build_task_context(self, max_tokens: int = 30000) -> str:
        """Build compressed context for the current task."""
        snapshot = self.semantic_memory.build_context_snapshot()

        context = self.context_compressor.compress_for_task(
            task_context=snapshot,
            memory_snapshot=snapshot,
            max_tokens=max_tokens,
        )

        return context

    def build_full_context(self, max_tokens: int = 150000) -> str:
        """Build full project context within token budget."""
        sections = []

        # 1. Project identity (pinned, highest priority)
        identity = self.intent_preservation.get_identity_summary()
        sections.append(identity)

        # 2. Active task
        task = self.semantic_memory.get_active_task()
        if task:
            task_ctx = f"# Active Task: {task.title}\n{task.objective}"
            if task.constraints:
                task_ctx += f"\nConstraints: {'; '.join(task.constraints)}"
            sections.append(task_ctx)

        # 3. Architecture
        arch = self.semantic_memory.get_architecture_summary()
        if arch.strip():
            sections.append(arch)

        # 4. Architectural memory
        arch_mem = self.architectural_memory.get_architecture_context()
        if arch_mem.strip():
            sections.append(arch_mem)

        # 5. Failure memory
        failure_mem = self.failure_memory.get_failure_context()
        if failure_mem.strip():
            sections.append(failure_mem)

        # 6. Knowledge index
        index_summary = self.memory_index.build_context_summary(max_entries=20)
        if index_summary.strip():
            sections.append(index_summary)

        # Assemble within budget
        full_context = "\n\n".join(sections)

        # Check token budget
        estimated_tokens = len(full_context) // 4
        if estimated_tokens > max_tokens:
            full_context = self.context_compressor._truncate_to_tokens(
                full_context, max_tokens
            )

        return full_context

    # ── Drift Detection ──

    def check_drift(self) -> List[DriftReport]:
        """Run drift detection on all memory."""
        memory_data = self.semantic_memory.build_context_snapshot()
        reports = self.drift_detector.check_all(memory_data)

        # Auto-fix what we can
        for report in reports:
            if report.auto_fixable:
                self._auto_fix_drift(report)

        return reports

    def _auto_fix_drift(self, report: DriftReport) -> None:
        """Auto-fix a drift report."""
        if report.drift_type == "dead_memory":
            # Remove dead references
            self.memory_index.mark_stale(report.memory_key)
        elif report.drift_type == "stale_summary":
            # Mark as needing update
            pass  # Will be updated on next scan

    # ── Governance ──

    def run_governance(self) -> List[GovernorAction]:
        """Run memory governance."""
        memory_data = self.semantic_memory.build_context_snapshot()
        return self.memory_governor.govern(memory_data)

    def check_operation_allowed(self, operation: str) -> tuple:
        """Check if an operation is allowed."""
        # Check governance
        allowed, reason = self.semantic_memory.check_operation_allowed(operation)
        if not allowed:
            return False, reason

        # Check intent
        allowed, reason = self.intent_preservation.check_against_intents(operation)
        if not allowed:
            return False, reason

        return True, "OK"

    # ── Identity ──

    def set_project_identity(self, **kwargs) -> None:
        """Set project identity."""
        identity = ProjectIdentity(**kwargs)
        self.semantic_memory.set_identity(identity)
        self._touch()

    def get_project_identity(self) -> str:
        """Get project identity summary."""
        return self.intent_preservation.get_identity_summary()

    # ── Stats ──

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        return {
            "project_id": self.project_id,
            "version": self._version,
            "last_update": self._last_update,
            "semantic_memory": self.semantic_memory.get_stats(),
            "memory_index": self.memory_index.get_stats(),
            "architectural_memory": self.architectural_memory.get_stats(),
            "failure_memory": self.failure_memory.get_stats(),
            "intent_preservation": self.intent_preservation.get_stats(),
            "drift_detection": self.drift_detector.get_stats(),
            "memory_governor": self.memory_governor.get_stats(),
            "token_budget": self.token_budget.get_budget_report().__dict__,
        }

    def _touch(self) -> None:
        """Update metadata."""
        self._version += 1
        self._last_update = datetime.utcnow().isoformat() + "Z"
