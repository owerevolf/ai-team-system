"""
Orchestrator — the main orchestration runtime.

This is the top-level orchestration entry point.
It coordinates:
- Understanding → Planning → Tasking → Review

All execution goes through TeamLead.
No free agents. No chaos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from .agent_registry import AgentRegistry
from .brain_store import BrainStore
from .execution_memory import ExecutionMemory
from .execution_plan import ExecutionPlan, PlanStatus
from .project_brain import ProjectBrain, RuntimeState, brain_to_dict
from .runtime_events import EventBus, EventType, EventSeverity
from .skill_router import SkillRouter
from .teamlead_runtime import TeamLeadRuntime, OrchestrationResult
from .understanding_engine import UnderstandingEngine


@dataclass
class OrchestratorStatus:
    """Current status of the orchestrator."""
    state: str = "idle"
    current_plan_id: str = ""
    current_phase: str = ""
    active_agents: List[str] = field(default_factory=list)
    tasks_total: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_blocked: int = 0
    events_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "current_plan_id": self.current_plan_id,
            "current_phase": self.current_phase,
            "active_agents": self.active_agents,
            "tasks_total": self.tasks_total,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_blocked": self.tasks_blocked,
            "events_count": self.events_count,
        }


class Orchestrator:
    """
    Main orchestration runtime.

    Flow:
    1. User sends a message
    2. Understanding phase analyzes the request
    3. Planning phase creates an execution plan
    4. Tasking phase assigns agents
    5. Review phase validates outputs

    Currently: PLANNING ONLY. No actual code execution.
    """

    def __init__(self, project_id: str = "",
                 brain_store: Optional[BrainStore] = None):
        self._project_id = project_id
        self._brain_store = brain_store or BrainStore()
        self._brain: Optional[ProjectBrain] = None
        self._events = EventBus()
        self._registry = AgentRegistry()
        self._skills = SkillRouter(self._registry)
        self._understanding = UnderstandingEngine()
        self._teamlead: Optional[TeamLeadRuntime] = None
        self._current_plan: Optional[ExecutionPlan] = None
        self._memory = ExecutionMemory(project_id=project_id)
        self._status = OrchestratorStatus()

    @property
    def brain(self) -> Optional[ProjectBrain]:
        return self._brain

    @property
    def events(self) -> EventBus:
        return self._events

    @property
    def status(self) -> OrchestratorStatus:
        return self._status

    def initialize(self, project_id: str,
                   project_name: str = "",
                   project_summary: str = "") -> ProjectBrain:
        """Initialize the orchestrator for a project."""
        self._project_id = project_id

        # Load or create brain
        self._brain = self._brain_store.load_brain(project_id)
        if not self._brain:
            self._brain = self._brain_store.create_brain(
                project_id, project_name or project_id
            )
            if project_summary:
                self._brain.project_summary = project_summary
                self._brain_store.save_brain(self._brain)

        # Initialize TeamLead
        self._teamlead = TeamLeadRuntime(
            project_brain=self._brain,
            agent_registry=self._registry,
            event_bus=self._events,
        )

        # Initialize memory
        self._memory = ExecutionMemory(
            project_id=project_id,
        )

        self._events.emit_simple(
            EventType.INFO,
            f"Orchestrator initialized for project: {project_id}",
            source="orchestrator",
        )

        return self._brain

    def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message through the full orchestration flow.

        Returns a dict with understanding, plan, and status.
        """
        if not self._brain:
            return {"error": "Orchestrator not initialized. Call initialize() first."}

        if not self._teamlead:
            return {"error": "TeamLead not initialized."}

        # Phase 1: Understanding
        self._status.state = "understanding"
        self._brain.set_runtime_state(RuntimeState.UNDERSTANDING)

        understanding = self._understanding.analyze(
            message, brain_to_dict(self._brain)
        )

        self._events.emit_simple(
            EventType.UNDERSTANDING_COMPLETED,
            f"Understanding complete: {understanding.objective}",
            source="orchestrator",
        )

        # Check if clarification needed
        if understanding.clarification_questions:
            self._events.emit_simple(
                EventType.CLARIFICATION_NEEDED,
                f"Clarification needed: {len(understanding.clarification_questions)} questions",
                source="orchestrator",
            )
            return {
                "status": "clarification_needed",
                "understanding": {
                    "objective": understanding.objective,
                    "formatted": understanding.format_for_display(),
                    "clarification_questions": understanding.clarification_questions,
                    "is_ready": False,
                },
            }

        # Phase 2: Planning
        self._status.state = "planning"
        self._brain.set_runtime_state(RuntimeState.PLANNING)

        understanding_dict = {
            "objective": understanding.objective,
            "affected_areas": understanding.affected_areas,
            "estimated_complexity": understanding.estimated_complexity,
            "risks": understanding.risks,
            "suggested_agent": understanding.suggested_agent,
        }

        orch_result = self._teamlead.orchestrate(
            objective=understanding.objective,
            understanding_result=understanding_dict,
        )

        self._status.current_plan_id = orch_result.plan_id
        self._status.tasks_total = orch_result.tasks_created
        self._status.events_count = self._events.event_count

        if orch_result.success:
            self._status.state = "planned"
            self._brain.set_runtime_state(RuntimeState.IDLE)
        else:
            self._status.state = "failed"
            self._brain.set_runtime_state(RuntimeState.BLOCKED)

        return {
            "status": "planned" if orch_result.success else "failed",
            "understanding": {
                "objective": understanding.objective,
                "formatted": understanding.format_for_display(),
                "is_ready": True,
            },
            "plan": {
                "plan_id": orch_result.plan_id,
                "tasks_created": orch_result.tasks_created,
                "tasks_assigned": orch_result.tasks_assigned,
                "phases_created": orch_result.phases_created,
            },
            "events": orch_result.events[-10:] if orch_result.events else [],
            "errors": orch_result.errors,
            "warnings": orch_result.warnings,
        }

    def get_plan_status(self) -> Optional[Dict[str, Any]]:
        """Get the current execution plan status."""
        if not self._teamlead:
            return None
        return self._teamlead.get_status()

    def get_timeline(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the event timeline."""
        events = self._events.get_timeline(limit=limit)
        return [e.to_dict() for e in events]

    def get_agent_status(self) -> List[Dict[str, Any]]:
        """Get status of all agents."""
        agents = self._registry.list_agents()
        return [a.to_dict() for a in agents]
