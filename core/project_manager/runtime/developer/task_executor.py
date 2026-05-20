"""
Task Executor — controlled worker runtime.

NOT an autonomous coder.
A controlled worker that:
1. Receives task contract
2. Loads scoped context
3. Requests skills
4. Calls execution sandbox
5. Generates patch
6. Passes to review
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from .agent_registry import AgentRegistry
from .approval_runtime import ApprovalRuntime, ApprovalLevel
from .execution_sandbox import ExecutionSandbox, SandboxPolicy
from .execution_plan import PlanTask
from .knowledge_index import KnowledgeIndex
from .patch_engine import PatchEngine, Patch, RiskLevel
from .project_brain import ProjectBrain
from .skill_router import SkillRouter
from .task_contracts import TaskContract
from .workspace_runtime import WorkspaceRuntime, Workspace


@dataclass
class ExecutionResult:
    """Result of a task execution."""
    success: bool = False
    task_id: str = ""
    agent_id: str = ""
    patch_id: str = ""
    approval_request_id: str = ""
    status: str = ""  # pending_approval, approved, rejected, failed
    output: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "patch_id": self.patch_id,
            "approval_request_id": self.approval_request_id,
            "status": self.status,
            "output": self.output,
            "errors": self.errors,
        }


class TaskExecutor:
    """
    Controlled task execution coordinator.

    Flow:
    1. Receive task contract
    2. Create workspace
    3. Load scoped context
    4. Generate patch (via sandbox)
    5. Validate patch
    6. Submit for approval
    7. Return result
    """

    def __init__(self, project_brain: ProjectBrain,
                 agent_registry: Optional[AgentRegistry] = None,
                 workspace_runtime: Optional[WorkspaceRuntime] = None,
                 patch_engine: Optional[PatchEngine] = None,
                 approval_runtime: Optional[ApprovalRuntime] = None,
                 knowledge_index: Optional[KnowledgeIndex] = None,
                 project_root: str = "."):
        self._brain = project_brain
        self._registry = agent_registry or AgentRegistry()
        self._skills = SkillRouter(self._registry)
        self._workspaces = workspace_runtime or WorkspaceRuntime()
        self._patches = patch_engine or PatchEngine(project_root)
        self._approval = approval_runtime or ApprovalRuntime()
        self._knowledge = knowledge_index or KnowledgeIndex(project_brain.project_id)
        self._sandbox = ExecutionSandbox(project_root, SandboxPolicy.PATCH_ONLY.value)
        self._project_root = project_root

    def execute_task(self, task_contract: TaskContract,
                     plan_task: Optional[PlanTask] = None) -> ExecutionResult:
        """
        Execute a task in a controlled manner.

        This is the main entry point for task execution.
        The agent NEVER writes files directly.
        """
        result = ExecutionResult(
            task_id=task_contract.task_id,
            agent_id=task_contract.owner_agent,
        )

        try:
            # Step 1: Validate agent can perform this task
            agent = self._registry.get(task_contract.owner_agent)
            if not agent:
                result.errors.append(f"Unknown agent: {task_contract.owner_agent}")
                return result

            # Step 2: Create workspace
            workspace = self._workspaces.create_workspace(
                project_id=self._brain.project_id,
                task_id=task_contract.task_id,
                project_root=self._project_root,
            )

            # Step 3: Create snapshot before changes
            self._workspaces.create_snapshot(
                workspace.workspace_id,
                "Pre-execution snapshot"
            )

            # Step 4: Load scoped context
            context = self._load_scoped_context(task_contract)

            # Step 5: Generate patch (mock for now — real implementation would call LLM)
            patch = self._generate_patch(task_contract, context, workspace)

            if not patch:
                result.errors.append("Failed to generate patch")
                return result

            result.patch_id = patch.patch_id

            # Step 6: Validate patch
            passed, errors, warnings = self._patches.validate_patch(
                patch,
                forbidden_files=task_contract.forbidden_files,
                max_files=task_contract.max_files_changed,
                max_lines=task_contract.max_lines_changed,
            )

            if not passed:
                result.errors.extend(errors)
                result.status = "validation_failed"
                return result

            # Step 7: Submit for approval
            approval_request = self._approval.create_request(
                patch_id=patch.patch_id,
                task_id=task_contract.task_id,
                agent_id=task_contract.owner_agent,
                summary=patch.summary,
                risk_level=patch.risk_level,
                files_changed=[f.file_path for f in patch.files],
                lines_added=patch.total_lines_added,
                lines_removed=patch.total_lines_removed,
                diff_preview="\n".join(f.diff for f in patch.files),
            )

            result.approval_request_id = approval_request.request_id

            if approval_request.status == "auto_approved":
                # Apply immediately for low-risk patches
                success = self._patches.apply_patch(patch)
                result.success = success
                result.status = "applied" if success else "apply_failed"
            else:
                result.success = True
                result.status = "pending_approval"

            # Step 8: Update brain
            self._brain.touch()

        except Exception as e:
            result.errors.append(str(e))
            result.status = "failed"
            logger.error(f"Task execution failed: {e}")

        return result

    def _load_scoped_context(self, task_contract: TaskContract) -> str:
        """Load scoped context for the agent."""
        context_parts = []

        # Task contract
        context_parts.append(task_contract.to_prompt_context())

        # Knowledge index
        knowledge = self._knowledge.build_context(max_entries=10)
        context_parts.append(knowledge)

        # Project constraints
        if self._brain.constraints:
            context_parts.append("# Constraints")
            for c in self._brain.constraints:
                context_parts.append(f"- {c.rule}")

        return "\n\n".join(context_parts)

    def _generate_patch(self, task_contract: TaskContract,
                        context: str, workspace: Workspace) -> Optional[Patch]:
        """
        Generate a patch for the task.

        In a real implementation, this would call the LLM with the scoped context.
        For now, we create a mock patch.
        """
        # This is where the LLM would generate the actual code changes
        # For Phase 19D, we create a placeholder patch
        file_changes = {}

        # Read allowed files from workspace
        for allowed_file in (task_contract.allowed_files or [])[:3]:
            read_result = self._sandbox.read_file(allowed_file)
            if read_result.success:
                # In real implementation, LLM would modify this content
                file_changes[allowed_file] = read_result.output

        if not file_changes:
            return None

        patch = self._patches.generate_patch(
            task_id=task_contract.task_id,
            file_changes=file_changes,
            created_by=task_contract.owner_agent,
            summary=f"Patch for: {task_contract.title}",
        )

        return patch

    def approve_patch(self, request_id: str) -> bool:
        """Approve a pending patch and apply it."""
        request = self._approval.approve(request_id)
        if not request:
            return False

        patch = self._patches.get_patch(request.patch_id)
        if not patch:
            return False

        return self._patches.apply_patch(patch)

    def reject_patch(self, request_id: str) -> bool:
        """Reject a pending patch."""
        request = self._approval.reject(request_id)
        return request is not None

    def get_approval_queue(self) -> List[Dict]:
        """Get all pending approval requests."""
        pending = self._approval.get_pending()
        return [r.to_dict() for r in pending]

    def get_approval_history(self, limit: int = 20) -> List[Dict]:
        """Get approval history."""
        history = self._approval.get_history(limit)
        return [r.to_dict() for r in history]
