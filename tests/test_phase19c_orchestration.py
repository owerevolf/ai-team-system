"""
Tests for Phase 19C — Safe Orchestration Runtime.
"""

import pytest

from core.project_manager.runtime.developer.agent_registry import (
    AgentRegistry, AgentProfile, AgentCapabilities, RiskLevel,
)
from core.project_manager.runtime.developer.skill_router import (
    SkillRouter, SkillAssignment, TASK_SKILL_MAP, ALL_SKILLS,
)
from core.project_manager.runtime.developer.execution_plan import (
    ExecutionPlan, PlanPhase, PlanTask, PlanStatus,
)
from core.project_manager.runtime.developer.execution_memory import (
    ExecutionMemory, ExecutionRecord,
)
from core.project_manager.runtime.developer.runtime_events import (
    EventBus, RuntimeEvent, EventType, EventSeverity,
)
from core.project_manager.runtime.developer.safe_review import (
    SafeReview, ReviewResult, ReviewStatus, ViolationType,
)
from core.project_manager.runtime.developer.teamlead_runtime import (
    TeamLeadRuntime, OrchestrationResult,
)
from core.project_manager.runtime.developer.orchestrator import (
    Orchestrator, OrchestratorStatus,
)
from core.project_manager.runtime.developer.project_brain import (
    ProjectBrain, RuntimeState,
)
from core.project_manager.runtime.developer.brain_store import BrainStore
from core.project_manager.runtime.developer.task_contracts import (
    TaskContract, TaskContractBuilder,
)


# ═══════════════════════════════════════════════════════════════
# Agent Registry Tests
# ═══════════════════════════════════════════════════════════════

class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def test_default_agents_registered(self):
        reg = AgentRegistry()
        agents = reg.list_agents()
        assert len(agents) == 7

    def test_get_agent_by_id(self):
        reg = AgentRegistry()
        agent = reg.get("backend")
        assert agent is not None
        assert agent.id == "backend"
        assert agent.name == "Backend"

    def test_get_agent_by_role(self):
        reg = AgentRegistry()
        agent = reg.get_by_role("frontend")
        assert agent is not None
        assert agent.role == "frontend"

    def test_teamlead_capabilities(self):
        reg = AgentRegistry()
        tl = reg.get("teamlead")
        assert tl is not None
        assert tl.capabilities.can_approve_tasks is True
        assert tl.capabilities.can_assign_tasks is True
        assert tl.capabilities.can_modify_files is False
        assert tl.capabilities.can_review_others is True

    def test_backend_capabilities(self):
        reg = AgentRegistry()
        be = reg.get("backend")
        assert be is not None
        assert be.capabilities.can_create_files is True
        assert be.capabilities.can_modify_files is True
        assert be.capabilities.can_modify_architecture is False
        assert "fastapi" in be.supported_skills

    def test_frontend_capabilities(self):
        reg = AgentRegistry()
        fe = reg.get("frontend")
        assert fe is not None
        assert fe.capabilities.can_create_files is True
        assert fe.capabilities.can_modify_config is False
        assert "react" in fe.supported_skills or "css" in fe.supported_skills

    def test_tester_capabilities(self):
        reg = AgentRegistry()
        tester = reg.get("tester")
        assert tester is not None
        assert tester.capabilities.can_run_tests is True
        assert tester.capabilities.can_modify_files is False
        assert tester.risk_level == RiskLevel.LOW.value

    def test_get_capable_agents(self):
        reg = AgentRegistry()
        agents = reg.get_capable_agents("fastapi")
        assert len(agents) >= 1
        assert any(a.id == "backend" for a in agents)

    def test_can_agent(self):
        reg = AgentRegistry()
        assert reg.can_agent("backend", "write_api") is True
        assert reg.can_agent("backend", "deploy") is False
        assert reg.can_agent("nonexistent", "write_api") is False

    def test_validate_agent_task(self):
        reg = AgentRegistry()
        ok, msg = reg.validate_agent_task("backend", "write_api")
        assert ok is True
        ok, msg = reg.validate_agent_task("tester", "write_api")
        assert ok is False

    def test_agent_to_dict(self):
        reg = AgentRegistry()
        agent = reg.get("backend")
        assert agent is not None
        d = agent.to_dict()
        assert d["id"] == "backend"
        assert "capabilities" in d
        assert "supported_skills" in d


# ═══════════════════════════════════════════════════════════════
# Skill Router Tests
# ═══════════════════════════════════════════════════════════════

class TestSkillRouter:
    """Tests for SkillRouter."""

    def test_get_skills_for_task(self):
        router = SkillRouter()
        skills = router.get_skills_for_task("create_api")
        assert len(skills) > 0
        assert "fastapi" in skills

    def test_get_skills_for_unknown_task(self):
        router = SkillRouter()
        skills = router.get_skills_for_task("unknown_task")
        assert skills == []

    def test_route_task_to_backend(self):
        router = SkillRouter()
        assignment = router.route_task("create_api")
        assert assignment.agent_id == "backend"
        assert assignment.confidence > 0

    def test_route_task_to_frontend(self):
        router = SkillRouter()
        assignment = router.route_task("create_component")
        assert assignment.agent_id == "frontend"
        assert assignment.confidence > 0

    def test_route_task_to_tester(self):
        router = SkillRouter()
        assignment = router.route_task("create_test")
        assert assignment.agent_id == "tester"
        assert assignment.confidence > 0

    def test_route_with_preferred_agent(self):
        router = SkillRouter()
        assignment = router.route_task("create_api", preferred_agent="backend")
        assert assignment.agent_id == "backend"

    def test_route_unknown_task(self):
        router = SkillRouter()
        assignment = router.route_task("unknown_task")
        assert assignment.agent_id == "teamlead"
        assert assignment.confidence == 0.0

    def test_can_agent_handle(self):
        router = SkillRouter()
        assert router.can_agent_handle("backend", "create_api") is True
        assert router.can_agent_handle("frontend", "create_api") is False

    def test_suggest_agents_for_task(self):
        router = SkillRouter()
        suggestions = router.suggest_agents_for_task("create_api")
        assert len(suggestions) > 0
        assert suggestions[0]["agent_id"] == "backend"

    def test_skill_assignment_to_dict(self):
        assignment = SkillAssignment(
            agent_id="backend",
            task_id="t1",
            skills=["fastapi", "api_design"],
            primary_skill="fastapi",
            confidence=0.8,
        )
        d = assignment.to_dict()
        assert d["agent_id"] == "backend"
        assert d["confidence"] == 0.8


# ═══════════════════════════════════════════════════════════════
# Execution Plan Tests
# ═══════════════════════════════════════════════════════════════

class TestExecutionPlan:
    """Tests for ExecutionPlan."""

    def test_create_plan(self):
        plan = ExecutionPlan(project_id="test", objective="Add auth")
        assert plan.plan_id != ""
        assert plan.objective == "Add auth"
        assert plan.status == PlanStatus.DRAFT.value

    def test_add_phase(self):
        plan = ExecutionPlan(project_id="test", objective="Test")
        phase = plan.add_phase("Implementation", "Implement the feature", order=1)
        assert phase.name == "Implementation"
        assert phase.order == 1
        assert len(plan.phases) == 1

    def test_add_task(self):
        plan = ExecutionPlan(project_id="test", objective="Test")
        phase = plan.add_phase("Implementation", order=1)
        task = plan.add_task("Create API", task_type="create_api",
                             phase_id=phase.id)
        assert task.title == "Create API"
        assert task.phase_id == phase.id
        assert task.id in phase.task_ids

    def test_get_next_pending_task(self):
        plan = ExecutionPlan(project_id="test", objective="Test")
        phase = plan.add_phase("Implementation", order=1)
        t1 = plan.add_task("Task 1", phase_id=phase.id)
        t2 = plan.add_task("Task 2", phase_id=phase.id)

        next_task = plan.get_next_pending_task()
        assert next_task is not None
        assert next_task.id == t1.id

    def test_update_task_status(self):
        plan = ExecutionPlan(project_id="test", objective="Test")
        phase = plan.add_phase("Implementation", order=1)
        task = plan.add_task("Task 1", phase_id=phase.id)

        result = plan.update_task_status(task.id, "completed")
        assert result is True
        assert plan.completed_tasks == 1

    def test_get_progress(self):
        plan = ExecutionPlan(project_id="test", objective="Test")
        phase = plan.add_phase("Implementation", order=1)
        plan.add_task("Task 1", phase_id=phase.id)
        plan.add_task("Task 2", phase_id=phase.id)

        progress = plan.get_progress()
        assert progress["total"] == 2
        assert progress["completed"] == 0
        assert progress["percent"] == 0

    def test_phases_sorted_by_order(self):
        plan = ExecutionPlan(project_id="test", objective="Test")
        plan.add_phase("Review", order=3)
        plan.add_phase("Planning", order=1)
        plan.add_phase("Implementation", order=2)

        orders = [p.order for p in plan.phases]
        assert orders == [1, 2, 3]

    def test_plan_to_dict(self):
        plan = ExecutionPlan(project_id="test", objective="Test")
        d = plan.to_dict()
        assert d["project_id"] == "test"
        assert "phases" in d
        assert "tasks" in d
        assert "progress" in d


# ═══════════════════════════════════════════════════════════════
# Execution Memory Tests
# ═══════════════════════════════════════════════════════════════

class TestExecutionMemory:
    """Tests for ExecutionMemory."""

    def test_create_memory(self):
        mem = ExecutionMemory(plan_id="p1", project_id="proj1")
        assert mem.plan_id == "p1"
        assert mem.project_id == "proj1"

    def test_record(self):
        mem = ExecutionMemory()
        rec = mem.record("test", "Test message", task_id="t1")
        assert rec.record_type == "test"
        assert rec.message == "Test message"
        assert rec.task_id == "t1"

    def test_record_task_assignment(self):
        mem = ExecutionMemory()
        rec = mem.record_task_assignment("t1", "backend", ["fastapi"])
        assert rec.record_type == "task_assignment"
        assert rec.agent_id == "backend"

    def test_record_task_complete(self):
        mem = ExecutionMemory()
        rec = mem.record_task_complete("t1", "backend", "Done")
        assert rec.record_type == "task_complete"

    def test_record_task_failure(self):
        mem = ExecutionMemory()
        rec = mem.record_task_failure("t1", "backend", "Error occurred")
        assert rec.record_type == "task_failure"

    def test_record_review(self):
        mem = ExecutionMemory()
        rec = mem.record_review("t1", True, [])
        assert rec.record_type == "review"
        assert rec.data["passed"] is True

    def test_get_timeline(self):
        mem = ExecutionMemory()
        mem.record("test", "Message 1")
        mem.record("test", "Message 2")
        timeline = mem.get_timeline()
        assert len(timeline) == 2

    def test_get_records_by_type(self):
        mem = ExecutionMemory()
        mem.record("type_a", "A")
        mem.record("type_b", "B")
        mem.record("type_a", "A2")
        records = mem.get_records_by_type("type_a")
        assert len(records) == 2

    def test_get_summary(self):
        mem = ExecutionMemory(plan_id="p1")
        mem.record("test", "Test")
        summary = mem.get_summary()
        assert summary["plan_id"] == "p1"
        assert summary["total_records"] == 1


# ═══════════════════════════════════════════════════════════════
# Runtime Events Tests
# ═══════════════════════════════════════════════════════════════

class TestRuntimeEvents:
    """Tests for EventBus and RuntimeEvent."""

    def test_create_event(self):
        event = RuntimeEvent(
            event_type=EventType.TASK_CREATED.value,
            message="Task created",
            source="test",
        )
        assert event.event_type == EventType.TASK_CREATED.value
        assert event.event_id != ""
        assert event.timestamp != ""

    def test_event_to_dict(self):
        event = RuntimeEvent(event_type="test", message="Test")
        d = event.to_dict()
        assert "event_id" in d
        assert "timestamp" in d
        assert d["message"] == "Test"

    def test_emit_event(self):
        bus = EventBus()
        event = RuntimeEvent(event_type="test", message="Test")
        bus.emit(event)
        assert bus.event_count == 1

    def test_emit_simple(self):
        bus = EventBus()
        event = bus.emit_simple(EventType.TASK_CREATED, "Task created", source="test")
        assert event.event_type == EventType.TASK_CREATED.value
        assert bus.event_count == 1

    def test_subscribe_to_type(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.TASK_CREATED, lambda e: received.append(e))
        bus.emit_simple(EventType.TASK_CREATED, "Task created")
        bus.emit_simple(EventType.TASK_COMPLETED, "Task done")
        assert len(received) == 1

    def test_subscribe_all(self):
        bus = EventBus()
        received = []
        bus.subscribe_all(lambda e: received.append(e))
        bus.emit_simple(EventType.TASK_CREATED, "Task created")
        bus.emit_simple(EventType.TASK_COMPLETED, "Task done")
        assert len(received) == 2

    def test_get_timeline(self):
        bus = EventBus()
        bus.emit_simple(EventType.TASK_CREATED, "Created")
        bus.emit_simple(EventType.TASK_COMPLETED, "Done")
        timeline = bus.get_timeline()
        assert len(timeline) == 2

    def test_get_events_by_type(self):
        bus = EventBus()
        bus.emit_simple(EventType.TASK_CREATED, "Created 1")
        bus.emit_simple(EventType.TASK_CREATED, "Created 2")
        bus.emit_simple(EventType.TASK_COMPLETED, "Done")
        events = bus.get_events_by_type(EventType.TASK_CREATED)
        assert len(events) == 2

    def test_clear_timeline(self):
        bus = EventBus()
        bus.emit_simple(EventType.TASK_CREATED, "Created")
        bus.clear()
        assert bus.event_count == 0


# ═══════════════════════════════════════════════════════════════
# Safe Review Tests
# ═══════════════════════════════════════════════════════════════

class TestSafeReview:
    """Tests for SafeReview."""

    def test_review_passes_with_no_violations(self):
        review = SafeReview()
        contract = TaskContractBuilder("Test", "Test objective") \
            .with_agent("backend") \
            .with_allowed_files(["test.py"]) \
            .build()
        result = review.review_task(contract, "backend", ["test.py"], "test output")
        assert result.status == ReviewStatus.PASSED.value
        assert not result.is_blocked

    def test_review_blocks_forbidden_file(self):
        review = SafeReview()
        contract = TaskContractBuilder("Test", "Test objective") \
            .with_agent("backend") \
            .with_allowed_files(["test.py"]) \
            .with_forbidden_files(["main.py"]) \
            .build()
        result = review.review_task(contract, "backend", ["test.py", "main.py"], "output")
        assert result.is_blocked
        assert any(v.violation_type == ViolationType.FORBIDDEN_FILE
                  for v in result.violations)

    def test_review_blocks_scope_violation(self):
        review = SafeReview()
        contract = TaskContractBuilder("Test", "Test objective") \
            .with_agent("backend") \
            .with_allowed_files(["f1.py"]) \
            .with_limits(max_files=1, max_lines=100) \
            .build()
        files = ["f1.py", "f2.py", "f3.py"]
        result = review.review_task(contract, "backend", files, "output")
        assert result.is_blocked
        assert any(v.violation_type == ViolationType.SCOPE
                  for v in result.violations)

    def test_review_blocks_unknown_agent(self):
        review = SafeReview()
        contract = TaskContractBuilder("Test", "Test objective") \
            .with_agent("backend") \
            .with_allowed_files(["test.py"]) \
            .build()
        result = review.review_task(contract, "unknown_agent", ["test.py"], "output")
        assert result.is_blocked

    def test_review_blocks_dangerous_operations(self):
        review = SafeReview()
        contract = TaskContractBuilder("Test", "Test objective") \
            .with_agent("backend") \
            .with_allowed_files(["test.py"]) \
            .build()
        result = review.review_task(contract, "backend", ["test.py"],
                                    "os.remove('/important')")
        assert result.is_blocked
        assert any(v.violation_type == ViolationType.DANGEROUS
                  for v in result.violations)

    def test_review_result_to_dict(self):
        result = ReviewResult(status=ReviewStatus.PASSED.value)
        d = result.to_dict()
        assert d["status"] == "passed"
        assert d["is_blocked"] is False


# ═══════════════════════════════════════════════════════════════
# TeamLead Runtime Tests
# ═══════════════════════════════════════════════════════════════

class TestTeamLeadRuntime:
    """Tests for TeamLeadRuntime."""

    def test_create_runtime(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        assert tl.brain.project_id == "test"

    def test_orchestrate_creates_plan(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        result = tl.orchestrate("Add realtime notifications")
        assert result.success is True
        assert result.plan_id != ""
        assert result.tasks_created > 0

    def test_orchestrate_creates_phases(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        result = tl.orchestrate("Add realtime notifications")
        assert result.phases_created == 4  # Understanding, Planning, Implementation, Review

    def test_orchestrate_emits_events(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        result = tl.orchestrate("Add realtime notifications")
        assert len(result.events) > 0

    def test_orchestrate_with_understanding(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        understanding = {
            "objective": "Add realtime",
            "affected_areas": ["backend", "frontend"],
            "estimated_complexity": "high",
            "risks": ["WebSocket complexity"],
            "suggested_agent": "backend",
        }
        result = tl.orchestrate("Add realtime", understanding)
        assert result.success is True
        assert result.tasks_assigned > 0

    def test_review_task_passes(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        contract = TaskContractBuilder("Test", "Test objective") \
            .with_agent("backend") \
            .with_allowed_files(["test.py"]) \
            .build()
        result = tl.review_task(contract, "backend", ["test.py"], "test output")
        assert result.status == ReviewStatus.PASSED.value

    def test_review_task_blocks(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        contract = TaskContractBuilder("Test", "Test objective") \
            .with_agent("backend") \
            .with_allowed_files(["test.py"]) \
            .with_forbidden_files(["main.py"]) \
            .build()
        result = tl.review_task(contract, "backend", ["main.py"], "output")
        assert result.is_blocked

    def test_get_status(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        status = tl.get_status()
        assert "brain_state" in status
        assert "project" in status

    def test_get_context_for_agent(self):
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)
        contract = TaskContractBuilder("Test", "Test objective") \
            .with_agent("backend") \
            .with_allowed_files(["test.py"]) \
            .build()
        context = tl.get_context_for_agent("backend", contract)
        assert "System Identity" in context
        assert "Agent Task Context" in context


# ═══════════════════════════════════════════════════════════════
# Orchestrator Tests
# ═══════════════════════════════════════════════════════════════

class TestOrchestrator:
    """Tests for Orchestrator."""

    def test_create_orchestrator(self):
        orch = Orchestrator(project_id="test")
        assert orch.status.state == "idle"

    def test_initialize(self):
        orch = Orchestrator(project_id="test")
        brain = orch.initialize("test", "Test Project", "A test project")
        assert brain.project_id == "test"
        assert brain.project_name == "Test Project"

    def test_process_message_returns_understanding(self):
        orch = Orchestrator(project_id="test")
        orch.initialize("test", "Test")
        result = orch.process_message("Add realtime notifications")
        assert "understanding" in result
        assert "status" in result

    def test_process_message_creates_plan(self):
        orch = Orchestrator(project_id="test")
        orch.initialize("test", "Test")
        result = orch.process_message("Add realtime notifications")
        if result.get("status") == "planned":
            assert "plan" in result
            assert result["plan"]["tasks_created"] > 0

    def test_process_message_without_init(self):
        orch = Orchestrator()
        result = orch.process_message("Test")
        assert "error" in result

    def test_get_timeline(self):
        orch = Orchestrator(project_id="test")
        orch.initialize("test", "Test")
        orch.process_message("Test message")
        timeline = orch.get_timeline()
        assert isinstance(timeline, list)

    def test_get_agent_status(self):
        orch = Orchestrator(project_id="test")
        orch.initialize("test", "Test")
        agents = orch.get_agent_status()
        assert len(agents) == 7

    def test_get_status(self):
        orch = Orchestrator(project_id="test")
        orch.initialize("test", "Test")
        status = orch.status.to_dict()
        assert "state" in status
        assert "tasks_total" in status


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestOrchestrationIntegration:
    """Integration tests for the full orchestration flow."""

    def test_full_orchestration_flow(self, tmp_path):
        """Test: initialize → process_message → review."""
        store = BrainStore(storage_dir=str(tmp_path / "brains"))
        orch = Orchestrator(project_id="integration-test", brain_store=store)
        orch.initialize("integration-test", "Integration Test", "Test project")

        # Process a message
        result = orch.process_message("Добавь WebSocket для realtime уведомлений")
        assert result["status"] in ("planned", "clarification_needed")

        if result["status"] == "planned":
            assert result["plan"]["tasks_created"] > 0
            assert result["plan"]["phases_created"] == 4

        # Check timeline
        timeline = orch.get_timeline()
        assert len(timeline) > 0

        # Check agents
        agents = orch.get_agent_status()
        assert len(agents) == 7

    def test_review_blocks_forbidden_files(self):
        """Test that review correctly blocks forbidden file modifications."""
        brain = ProjectBrain(project_id="test", project_name="Test")
        tl = TeamLeadRuntime(project_brain=brain)

        contract = TaskContractBuilder("Test", "Test") \
            .with_agent("backend") \
            .with_allowed_files(["test.py"]) \
            .with_forbidden_files(["main.py"]) \
            .build()

        # Should pass
        result = tl.review_task(contract, "backend", ["test.py"], "output")
        assert not result.is_blocked

        # Should block
        result = tl.review_task(contract, "backend", ["main.py"], "output")
        assert result.is_blocked

    def test_skill_routing_matches_agents(self):
        """Test that skill routing correctly matches agents to tasks."""
        router = SkillRouter()

        # Backend task
        assignment = router.route_task("create_api")
        assert assignment.agent_id == "backend"

        # Frontend task
        assignment = router.route_task("create_component")
        assert assignment.agent_id == "frontend"

        # Test task
        assignment = router.route_task("create_test")
        assert assignment.agent_id == "tester"

    def test_execution_plan_progress(self):
        """Test execution plan progress tracking."""
        plan = ExecutionPlan(project_id="test", objective="Test")
        phase = plan.add_phase("Implementation", order=1)
        t1 = plan.add_task("Task 1", phase_id=phase.id)
        t2 = plan.add_task("Task 2", phase_id=phase.id)

        progress = plan.get_progress()
        assert progress["total"] == 2
        assert progress["completed"] == 0

        plan.update_task_status(t1.id, "completed")
        progress = plan.get_progress()
        assert progress["completed"] == 1
        assert progress["percent"] == 50.0

    def test_agent_cannot_exceed_scope(self):
        """Test that agents are limited by their scope."""
        reg = AgentRegistry()
        backend = reg.get("backend")

        # Backend has max 8 files per task
        assert backend.max_files_per_task == 8

        # Backend cannot modify architecture
        assert backend.capabilities.can_modify_architecture is False

        # Backend cannot deploy
        assert reg.can_agent("backend", "deploy") is False

    def test_teamlead_cannot_write_code(self):
        """Test that TeamLead cannot write code directly."""
        reg = AgentRegistry()
        tl = reg.get("teamlead")

        assert tl.capabilities.can_create_files is False
        assert tl.capabilities.can_modify_files is False
        assert reg.can_agent("teamlead", "write_code") is False

        # But can assign and review
        assert tl.capabilities.can_assign_tasks is True
        assert tl.capabilities.can_review_others is True
