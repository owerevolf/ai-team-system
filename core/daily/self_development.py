"""
self_development.py — Self-Development Runtime.

Purpose: Allow the system to develop itself — but ONLY through governed flow.
Self-development must feel BORINGLY SAFE, not "wow AI writes itself".

Flow:
1. User request
2. Project understanding
3. Task decomposition
4. TeamLead planning
5. Scoped contracts
6. Patch generation
7. Review
8. Tests
9. Human approval
10. Apply

NEVER: direct self-modification. ONLY: patches + approvals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class SelfDevTask:
    """A self-development task."""
    task_id: str = ""
    title: str = ""
    description: str = ""
    target_files: List[str] = field(default_factory=list)
    risk_level: str = "low"
    status: str = "pending"  # pending, planning, generating, reviewing, testing, approved, applied, failed
    patches: List[Dict[str, Any]] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)
    approved: bool = False
    applied: bool = False


class SelfDevelopment:
    """
    Governed self-development runtime.
    System can develop itself — but only through the same governed flow as any task.
    """

    # Protected areas — never self-modify
    PROTECTED_AREAS = [
        "core/production/complexity_gate.py",
        "core/production/self_protection.py",
        "core/dual_mode/identity_validation.py",
        "core/workflow/enoughness_enforcement.py",
        "core/project_manager/governance/",
        "core/project_manager/runtime/developer/approval_runtime.py",
    ]

    # Maximum self-dev tasks per session
    MAX_SELF_DEV_TASKS = 3

    def __init__(self):
        self._tasks: Dict[str, SelfDevTask] = {}
        self._session_task_count = 0

    def create_task(self, title: str, description: str,
                    target_files: List[str]) -> Optional[SelfDevTask]:
        """Create a self-development task."""
        if self._session_task_count >= self.MAX_SELF_DEV_TASKS:
            logger.warning(f"Self-dev task limit reached ({self.MAX_SELF_DEV_TASKS})")
            return None

        # Check protected areas
        for f in target_files:
            if self._is_protected(f):
                logger.warning(f"Cannot self-modify protected area: {f}")
                return None

        import uuid
        task = SelfDevTask(
            task_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            target_files=target_files,
        )
        self._tasks[task.task_id] = task
        self._session_task_count += 1

        logger.info(f"Self-dev task created: {task.task_id} ({title})")
        return task

    def _is_protected(self, file_path: str) -> bool:
        """Check if a file is in a protected area."""
        for protected in self.PROTECTED_AREAS:
            if protected in file_path or file_path.startswith(protected):
                return True
        return False

    def get_task(self, task_id: str) -> Optional[SelfDevTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: str = "") -> List[SelfDevTask]:
        """List self-dev tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def advance_task(self, task_id: str, new_status: str) -> bool:
        """Advance a task to the next status."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        valid_transitions = {
            "pending": ["planning", "failed"],
            "planning": ["generating", "failed"],
            "generating": ["reviewing", "failed"],
            "reviewing": ["testing", "failed"],
            "testing": ["approved", "failed"],
            "approved": ["applied", "failed"],
            "applied": [],
            "failed": [],
        }

        if new_status not in valid_transitions.get(task.status, []):
            logger.warning(f"Invalid transition: {task.status} -> {new_status}")
            return False

        task.status = new_status
        logger.info(f"Self-dev task {task_id}: {task.status} -> {new_status}")
        return True

    def get_safe_self_dev_candidates(self) -> List[Dict[str, str]]:
        """
        Get a list of safe self-development candidates.
        Only suggests changes that are low-risk and well-scoped.
        """
        return [
            {
                "title": "Add missing docstrings",
                "description": "Add docstrings to functions that lack them",
                "risk": "low",
                "scope": "documentation",
            },
            {
                "title": "Fix lint warnings",
                "description": "Fix minor lint warnings (formatting, imports)",
                "risk": "low",
                "scope": "code quality",
            },
            {
                "title": "Add type hints",
                "description": "Add type hints to function signatures",
                "risk": "low",
                "scope": "type safety",
            },
            {
                "title": "Update README",
                "description": "Update documentation to reflect current state",
                "risk": "low",
                "scope": "documentation",
            },
        ]
