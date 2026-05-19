"""
Task Contracts — scoped execution contracts for agents.

Every task given to an agent MUST have a contract.
Agents NEVER get the whole project — only scoped context.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class ContractStatus(Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskContract:
    """
    A scoped execution contract for an agent.

    The agent receives ONLY:
    - this contract
    - the files listed in allowed_files
    - the context in context_summary

    The agent MUST NOT:
    - modify files not in allowed_files
    - change architecture
    - add dependencies without approval
    - modify unrelated modules
    """

    # Identity
    task_id: str = ""
    title: str = ""
    created_at: str = ""
    created_by: str = "developer"

    # Objective
    objective: str = ""
    context_summary: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)

    # Scope — what the agent is allowed to touch
    allowed_files: List[str] = field(default_factory=list)
    forbidden_files: List[str] = field(default_factory=list)
    allowed_modules: List[str] = field(default_factory=list)
    forbidden_modules: List[str] = field(default_factory=list)

    # Skills & tools
    required_skills: List[str] = field(default_factory=list)
    suggested_tools: List[str] = field(default_factory=list)

    # Output
    output_format: str = "code"  # code, diff, report, test
    expected_outputs: List[str] = field(default_factory=list)

    # Validation
    validation_rules: List[str] = field(default_factory=list)
    test_required: bool = True
    review_required: bool = True

    # Execution
    priority: str = "medium"  # low, medium, high, critical
    owner_agent: str = ""
    status: str = ContractStatus.DRAFT.value
    parent_task_id: str = ""  # for subtasks

    # Safety
    max_files_changed: int = 10
    max_lines_changed: int = 500
    requires_snapshot: bool = True
    rollback_on_failure: bool = True

    # Results (filled after execution)
    files_changed: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    error_message: str = ""

    def validate(self) -> List[str]:
        """Validate the contract. Returns list of issues."""
        issues = []
        if not self.objective:
            issues.append("Objective is required")
        if not self.owner_agent:
            issues.append("Owner agent is required")
        if not self.allowed_files and not self.allowed_modules:
            issues.append("At least one allowed file or module must be specified")
        if self.max_files_changed <= 0:
            issues.append("max_files_changed must be positive")
        if self.max_lines_changed <= 0:
            issues.append("max_lines_changed must be positive")
        return issues

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def to_prompt_context(self) -> str:
        """Convert contract to a context string for agent prompt."""
        lines = [
            f"## Task: {self.title}",
            f"",
            f"### Objective",
            f"{self.objective}",
            f"",
        ]
        if self.context_summary:
            lines.extend(["### Context", self.context_summary, ""])
        if self.allowed_files:
            lines.extend([
                "### Allowed Files",
                "\n".join(f"  - {f}" for f in self.allowed_files),
                "",
            ])
        if self.forbidden_files:
            lines.extend([
                "### Forbidden Files (DO NOT MODIFY)",
                "\n".join(f"  - {f}" for f in self.forbidden_files),
                "",
            ])
        if self.validation_rules:
            lines.extend([
                "### Validation Rules",
                "\n".join(f"  - {r}" for r in self.validation_rules),
                "",
            ])
        if self.acceptance_criteria:
            lines.extend([
                "### Acceptance Criteria",
                "\n".join(f"  - {ac}" for ac in self.acceptance_criteria),
                "",
            ])
        lines.extend([
            f"### Constraints",
            f"  - Max files changed: {self.max_files_changed}",
            f"  - Max lines changed: {self.max_lines_changed}",
            f"  - Tests required: {self.test_required}",
            f"  - Review required: {self.review_required}",
        ])
        return "\n".join(lines)


class TaskContractBuilder:
    """Builder for TaskContract with sensible defaults."""

    def __init__(self, title: str, objective: str):
        now = datetime.utcnow().isoformat() + "Z"
        self._contract = TaskContract(
            task_id=str(uuid.uuid4())[:8],
            title=title,
            objective=objective,
            created_at=now,
        )

    def with_context(self, context: str) -> TaskContractBuilder:
        self._contract.context_summary = context
        return self

    def with_allowed_files(self, files: List[str]) -> TaskContractBuilder:
        self._contract.allowed_files = files
        return self

    def with_forbidden_files(self, files: List[str]) -> TaskContractBuilder:
        self._contract.forbidden_files = files
        return self

    def with_allowed_modules(self, modules: List[str]) -> TaskContractBuilder:
        self._contract.allowed_modules = modules
        return self

    def with_forbidden_modules(self, modules: List[str]) -> TaskContractBuilder:
        self._contract.forbidden_modules = modules
        return self

    def with_skills(self, skills: List[str]) -> TaskContractBuilder:
        self._contract.required_skills = skills
        return self

    def with_validation_rules(self, rules: List[str]) -> TaskContractBuilder:
        self._contract.validation_rules = rules
        return self

    def with_acceptance_criteria(self, criteria: List[str]) -> TaskContractBuilder:
        self._contract.acceptance_criteria = criteria
        return self

    def with_output_format(self, fmt: str) -> TaskContractBuilder:
        self._contract.output_format = fmt
        return self

    def with_priority(self, priority: str) -> TaskContractBuilder:
        self._contract.priority = priority
        return self

    def with_agent(self, agent: str) -> TaskContractBuilder:
        self._contract.owner_agent = agent
        return self

    def with_limits(self, max_files: int = 10,
                    max_lines: int = 500) -> TaskContractBuilder:
        self._contract.max_files_changed = max_files
        self._contract.max_lines_changed = max_lines
        return self

    def with_safety(self, test_required: bool = True,
                    review_required: bool = True,
                    snapshot: bool = True,
                    rollback: bool = True) -> TaskContractBuilder:
        self._contract.test_required = test_required
        self._contract.review_required = review_required
        self._contract.requires_snapshot = snapshot
        self._contract.rollback_on_failure = rollback
        return self

    def with_parent(self, parent_task_id: str) -> TaskContractBuilder:
        self._contract.parent_task_id = parent_task_id
        return self

    def build(self) -> TaskContract:
        return self._contract
