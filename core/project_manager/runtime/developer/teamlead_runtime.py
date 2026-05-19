"""
TeamLead Runtime — the central orchestrator.

TeamLead:
- reads Project Brain
- analyzes execution plans
- divides tasks
- assigns agents with skills and constraints
- checks coherence and conflicts
- validates outputs

TeamLead CANNOT:
- write all code itself
- bypass contracts
- bypass review
- change frozen constraints
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from .agent_registry import AgentRegistry
from .context_layers import ContextLayers
from .execution_memory import ExecutionMemory
from .execution_plan import ExecutionPlan, PlanPhase, PlanTask, PlanStatus
from .project_brain import ProjectBrain, RuntimeState, brain_to_dict
from .runtime_events import EventBus, EventType, EventSeverity
from .safe_review import SafeReview, ReviewResult
from .skill_router import SkillRouter, SkillAssignment
from .task_contracts import TaskContract, TaskContractBuilder


@dataclass
class OrchestrationResult:
    """Result of an orchestration run."""
    success: bool = False
    plan_id: str = ""
    status: str = ""
    tasks_created: int = 0
    tasks_assigned: int = 0
    phases_created: int = 0
    events: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "plan_id": self.plan_id,
            "status": self.status,
            "tasks_created": self.tasks_created,
            "tasks_assigned": self.tasks_assigned,
            "phases_created": self.phases_created,
            "events": self.events,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class TeamLeadRuntime:
    """
    TeamLead orchestration runtime.

    This is the brain of the orchestration system.
    All task assignments, planning, and validation go through TeamLead.
    """

    def __init__(self, project_brain: Optional[ProjectBrain] = None,
                 agent_registry: Optional[AgentRegistry] = None,
                 event_bus: Optional[EventBus] = None):
        self._brain = project_brain or ProjectBrain()
        self._registry = agent_registry or AgentRegistry()
        self._events = event_bus or EventBus()
        self._skill_router = SkillRouter(self._registry)
        self._review = SafeReview(self._brain, self._registry)
        self._memory = ExecutionMemory(project_id=self._brain.project_id)

    @property
    def brain(self) -> ProjectBrain:
        return self._brain

    @property
    def events(self) -> EventBus:
        return self._events

    @property
    def memory(self) -> ExecutionMemory:
        return self._memory

    def orchestrate(self, objective: str,
                    understanding_result: Optional[Dict] = None) -> OrchestrationResult:
        """
        Main orchestration entry point.

        Flow:
        1. Read Project Brain
        2. Create execution plan
        3. Divide into phases
        4. Create tasks with contracts
        5. Assign agents
        6. Validate coherence
        """
        result = OrchestrationResult()

        try:
            # Step 1: Read brain
            self._brain.set_runtime_state(RuntimeState.PLANNING)
            self._events.emit_simple(
                EventType.ORCHESTRATION_STARTED,
                f"Orchestration started for: {objective}",
                source="teamlead",
            )

            # Step 2: Create execution plan
            plan = self._create_execution_plan(objective, understanding_result)
            result.plan_id = plan.plan_id
            result.phases_created = len(plan.phases)

            self._events.emit_simple(
                EventType.PLAN_CREATED,
                f"Execution plan created: {plan.plan_id} with {len(plan.phases)} phases",
                source="teamlead",
                plan_id=plan.plan_id,
            )

            # Step 3: Create tasks and assign agents
            tasks_created, tasks_assigned = self._create_and_assign_tasks(plan)
            result.tasks_created = tasks_created
            result.tasks_assigned = tasks_assigned

            # Step 4: Validate coherence
            self._validate_coherence(plan)

            # Step 5: Update brain
            self._brain.set_runtime_state(RuntimeState.IDLE)
            self._brain.touch()

            # Collect events
            result.events = [e.to_dict() for e in self._events.get_timeline()]
            result.success = True
            result.status = "planned"

            self._events.emit_simple(
                EventType.ORCHESTRATION_COMPLETED,
                f"Orchestration completed: {tasks_created} tasks, {tasks_assigned} assigned",
                source="teamlead",
                plan_id=plan.plan_id,
            )

        except Exception as e:
            result.success = False
            result.status = "failed"
            result.errors.append(str(e))
            self._events.emit_simple(
                EventType.ORCHESTRATION_FAILED,
                f"Orchestration failed: {e}",
                source="teamlead",
                severity=EventSeverity.ERROR.value,
            )
            logger.error(f"Orchestration failed: {e}")

        return result

    def _create_execution_plan(self, objective: str,
                               understanding_result: Optional[Dict] = None) -> ExecutionPlan:
        """Create a structured execution plan from the objective."""
        plan = ExecutionPlan(
            project_id=self._brain.project_id,
            objective=objective,
            summary=f"Execute: {objective}",
        )

        # Extract info from understanding result
        affected_areas = []
        complexity = "medium"
        risks = []
        if understanding_result:
            affected_areas = understanding_result.get("affected_areas", [])
            complexity = understanding_result.get("estimated_complexity", "medium")
            risks = understanding_result.get("risks", [])

        plan.estimated_complexity = complexity
        plan.affected_areas = affected_areas
        plan.risks = risks
        plan.validation_strategy = "safe_review"
        plan.rollback_strategy = "snapshot_restore"

        # Create standard phases
        plan.add_phase("Understanding", "Analyze and understand the task", order=0)
        plan.add_phase("Planning", "Create detailed execution plan", order=1)
        plan.add_phase("Implementation", "Execute the plan", order=2)
        plan.add_phase("Review", "Validate and review outputs", order=3)

        return plan

    def _create_and_assign_tasks(self, plan: ExecutionPlan) -> tuple[int, int]:
        """Create tasks for the plan and assign agents."""
        tasks_created = 0
        tasks_assigned = 0

        # Determine task types from affected areas
        affected_areas = plan.affected_areas or ["backend"]

        # Create implementation tasks based on affected areas
        impl_phase = None
        for p in plan.phases:
            if p.name == "Implementation":
                impl_phase = p
                break

        if not impl_phase:
            return 0, 0

        task_definitions = self._derive_task_definitions(
            plan.objective, affected_areas, plan.estimated_complexity
        )

        for task_def in task_definitions:
            task = plan.add_task(
                title=task_def["title"],
                task_type=task_def["type"],
                phase_id=impl_phase.id,
                description=task_def.get("description", ""),
                priority=task_def.get("priority", "medium"),
            )
            tasks_created += 1

            # Assign agent
            assignment = self._skill_router.route_task(
                task_def["type"],
                preferred_agent=task_def.get("preferred_agent", ""),
            )

            if assignment.agent_id and assignment.confidence > 0:
                task.assigned_agent = assignment.agent_id
                task.skills = assignment.skills
                tasks_assigned += 1

                self._memory.record_task_assignment(
                    task.id, assignment.agent_id, assignment.skills
                )
                self._events.emit_simple(
                    EventType.TASK_ASSIGNED,
                    f"Task '{task.title}' assigned to {assignment.agent_id}",
                    source="teamlead",
                    task_id=task.id,
                    agent_id=assignment.agent_id,
                    plan_id=plan.plan_id,
                )
            else:
                self._events.emit_simple(
                    EventType.WARNING,
                    f"No suitable agent found for task '{task.title}'",
                    source="teamlead",
                    task_id=task.id,
                    severity=EventSeverity.WARNING.value,
                )

        return tasks_created, tasks_assigned

    def _derive_task_definitions(self, objective: str,
                                 affected_areas: List[str],
                                 complexity: str) -> List[Dict]:
        """Derive task definitions from the objective and affected areas."""
        tasks = []

        # Map areas to task types
        area_task_map = {
            "backend": [
                {"title": f"Implement backend: {objective}", "type": "create_api",
                 "preferred_agent": "backend", "priority": "high"},
            ],
            "frontend": [
                {"title": f"Implement frontend: {objective}", "type": "create_component",
                 "preferred_agent": "frontend", "priority": "high"},
            ],
            "testing": [
                {"title": f"Write tests: {objective}", "type": "create_test",
                 "preferred_agent": "tester", "priority": "medium"},
            ],
            "devops": [
                {"title": f"Configure infrastructure: {objective}", "type": "create_dockerfile",
                 "preferred_agent": "devops", "priority": "medium"},
            ],
            "documentation": [
                {"title": f"Update documentation: {objective}", "type": "create_docs",
                 "preferred_agent": "documentalist", "priority": "low"},
            ],
            "architecture": [
                {"title": f"Design architecture: {objective}", "type": "create_architecture",
                 "preferred_agent": "architect", "priority": "high"},
            ],
            "security": [
                {"title": f"Implement security: {objective}", "type": "create_auth",
                 "preferred_agent": "backend", "priority": "high"},
            ],
            "database": [
                {"title": f"Database changes: {objective}", "type": "create_model",
                 "preferred_agent": "backend", "priority": "high"},
            ],
        }

        for area in affected_areas:
            if area in area_task_map:
                tasks.extend(area_task_map[area])

        # If no tasks derived, create a generic one
        if not tasks:
            tasks.append({
                "title": objective,
                "type": "create_api",
                "preferred_agent": "backend",
                "priority": "medium",
            })

        return tasks

    def _validate_coherence(self, plan: ExecutionPlan) -> bool:
        """Validate the execution plan for coherence."""
        is_coherent = True

        # Check all tasks have agents
        unassigned = [t for t in plan.tasks if not t.assigned_agent]
        if unassigned:
            for t in unassigned:
                self._events.emit_simple(
                    EventType.WARNING,
                    f"Task '{t.title}' has no assigned agent",
                    source="teamlead",
                    task_id=t.id,
                    severity=EventSeverity.WARNING.value,
                )
            is_coherent = False

        # Check for conflicts (multiple agents on same file)
        agent_files: Dict[str, List[str]] = {}
        for task in plan.tasks:
            if task.assigned_agent and task.allowed_files:
                agent_files.setdefault(task.assigned_agent, []).extend(task.allowed_files)

        # Check constraints
        for constraint in self._brain.constraints:
            self._events.emit_simple(
                EventType.INFO,
                f"Constraint enforced: {constraint.rule}",
                source="teamlead",
            )

        return is_coherent

    def review_task(self, task_contract: TaskContract,
                    agent_id: str,
                    files_changed: Optional[List[str]] = None,
                    output: str = "") -> ReviewResult:
        """Review a task before completion."""
        result = self._review.review_task(
            task_contract, agent_id, files_changed or [], output
        )

        self._memory.record_review(
            task_contract.task_id,
            result.status == "passed",
            [v.message for v in result.violations],
        )

        if result.is_blocked:
            self._events.emit_simple(
                EventType.REVIEW_BLOCKED,
                f"Task {task_contract.task_id} blocked: {result.violations[0].message}",
                source="teamlead",
                task_id=task_contract.task_id,
                severity=EventSeverity.ERROR.value,
            )
        else:
            self._events.emit_simple(
                EventType.REVIEW_PASSED,
                f"Task {task_contract.task_id} passed review",
                source="teamlead",
                task_id=task_contract.task_id,
            )

        return result

    def get_context_for_agent(self, agent_id: str,
                              task_contract: TaskContract) -> str:
        """Build scoped context for an agent."""
        layers = ContextLayers()
        layers.set_system_identity(
            f"AI Team System — Agent: {agent_id}. "
            f"You are a scoped agent. Follow your contract exactly."
        )
        layers.set_project_brain(brain_to_dict(self._brain))
        layers.set_agent_task(task_contract.to_prompt_context())
        return layers.build_context()

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestration status."""
        return {
            "brain_state": self._brain.runtime_state,
            "project": self._brain.project_name,
            "active_goals": len(self._brain.active_goals),
            "active_tasks": len(self._brain.active_tasks),
            "completed_tasks": len(self._brain.completed_tasks),
            "events_count": self._events.event_count,
            "memory_records": len(self._memory.get_timeline()),
        }
