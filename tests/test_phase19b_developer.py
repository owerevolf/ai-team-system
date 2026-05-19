"""
Tests for Phase 19B — Project Brain & Understanding Runtime.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from core.project_manager.runtime.developer.project_brain import (
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
from core.project_manager.runtime.developer.brain_store import BrainStore
from core.project_manager.runtime.developer.understanding_engine import (
    UnderstandingEngine,
    UnderstandingResult,
)
from core.project_manager.runtime.developer.task_contracts import (
    TaskContract,
    TaskContractBuilder,
    ContractStatus,
)
from core.project_manager.runtime.developer.context_layers import (
    ContextLayers,
    ContextLayer,
)


# ═══════════════════════════════════════════════════════════════
# Project Brain Tests
# ═══════════════════════════════════════════════════════════════

class TestProjectBrain:
    """Tests for ProjectBrain dataclass."""

    def test_create_default_brain(self):
        brain = ProjectBrain()
        assert brain.project_id == ""
        assert brain.runtime_state == RuntimeState.IDLE.value
        assert brain.active_tasks == []
        assert brain.decisions == []

    def test_create_brain_with_identity(self):
        brain = ProjectBrain(
            project_id="test-proj",
            project_name="Test Project",
        )
        assert brain.project_id == "test-proj"
        assert brain.project_name == "Test Project"

    def test_add_goal(self):
        brain = ProjectBrain(project_id="test")
        goal = brain.add_goal("Add auth", "Implement JWT authentication")
        assert goal.title == "Add auth"
        assert goal.description == "Implement JWT authentication"
        assert goal.status == "active"
        assert len(brain.active_goals) == 1

    def test_add_task(self):
        brain = ProjectBrain(project_id="test")
        task = brain.add_task("Fix bug", "Fix login bug", owner_agent="backend")
        assert task.title == "Fix bug"
        assert task.owner_agent == "backend"
        assert task.status.value == "active"
        assert len(brain.active_tasks) == 1

    def test_complete_task(self):
        brain = ProjectBrain(project_id="test")
        task = brain.add_task("Fix bug")
        assert len(brain.active_tasks) == 1
        assert len(brain.completed_tasks) == 0

        result = brain.complete_task(task.id)
        assert result is True
        assert len(brain.active_tasks) == 0
        assert len(brain.completed_tasks) == 1

    def test_complete_nonexistent_task(self):
        brain = ProjectBrain(project_id="test")
        result = brain.complete_task("nonexistent")
        assert result is False

    def test_add_decision(self):
        brain = ProjectBrain(project_id="test")
        d = brain.add_decision(
            "Use FastAPI",
            "We will use FastAPI for the API layer",
            context="Need async support",
            alternatives=["Flask", "Django"],
        )
        assert d.title == "Use FastAPI"
        assert d.decision == "We will use FastAPI for the API layer"
        assert len(d.alternatives) == 2
        assert len(brain.decisions) == 1

    def test_add_constraint(self):
        brain = ProjectBrain(project_id="test")
        c = brain.add_constraint(
            "No raw SQL",
            "Use ORM for all database operations",
            severity="hard",
        )
        assert c.rule == "No raw SQL"
        assert c.severity == "hard"
        assert len(brain.constraints) == 1

    def test_add_risk(self):
        brain = ProjectBrain(project_id="test")
        r = brain.add_risk(
            "WebSocket reconnect issues",
            likelihood="medium",
            impact="high",
            mitigation="Implement exponential backoff",
        )
        assert r.description == "WebSocket reconnect issues"
        assert r.likelihood == "medium"
        assert r.impact == "high"
        assert len(brain.known_risks) == 1

    def test_add_snapshot(self):
        brain = ProjectBrain(project_id="test")
        snap = brain.add_snapshot(
            "Initial project setup",
            key_facts=["Python 3.12", "FastAPI", "SQLite"],
            context_tokens=500,
        )
        assert snap.summary == "Initial project setup"
        assert len(snap.key_facts) == 3
        assert len(brain.memory_snapshots) == 1

    def test_set_runtime_state(self):
        brain = ProjectBrain(project_id="test")
        brain.set_runtime_state(RuntimeState.EXECUTING)
        assert brain.runtime_state == "executing"

    def test_touch_updates_timestamp(self):
        brain = ProjectBrain(project_id="test")
        old_updated = brain.updated_at
        brain.touch()
        assert brain.updated_at != old_updated

    def test_summary(self):
        brain = ProjectBrain(
            project_id="test",
            project_name="Test Project",
            current_phase="Phase 19B",
        )
        brain.add_task("Task 1")
        brain.add_task("Task 2")
        brain.complete_task(brain.active_tasks[0].id)
        s = brain.summary()
        assert "Test Project" in s
        assert "Phase 19B" in s


class TestBrainSerialization:
    """Tests for brain serialization/deserialization."""

    def test_brain_to_dict(self):
        brain = ProjectBrain(
            project_id="test",
            project_name="Test",
        )
        d = brain_to_dict(brain)
        assert isinstance(d, dict)
        assert d["project_id"] == "test"
        assert d["project_name"] == "Test"

    def test_brain_from_dict(self):
        data = {
            "project_id": "test",
            "project_name": "Test Project",
            "project_summary": "A test project",
            "runtime_state": "idle",
            "active_goals": [
                {"id": "g1", "title": "Goal 1", "status": "active",
                 "priority": "medium", "created_at": "2025-01-01T00:00:00Z"}
            ],
            "active_tasks": [
                {"id": "t1", "title": "Task 1", "status": "active",
                 "priority": "high", "owner_agent": "backend",
                 "created_at": "2025-01-01T00:00:00Z"}
            ],
            "completed_tasks": [],
            "blocked_tasks": [],
            "decisions": [],
            "constraints": [
                {"id": "c1", "rule": "No raw SQL", "reason": "Safety",
                 "severity": "hard"}
            ],
            "known_risks": [],
            "memory_snapshots": [],
            "architecture": {"pattern": "layered", "layers": ["api", "service", "data"]},
            "tech_stack": {"languages": ["python"], "frameworks": ["fastapi"]},
            "repo_map": {"entrypoints": ["main.py"], "total_files": 42},
        }
        brain = brain_from_dict(data)
        assert brain.project_id == "test"
        assert brain.project_name == "Test Project"
        assert len(brain.active_goals) == 1
        assert len(brain.active_tasks) == 1
        assert brain.active_tasks[0].owner_agent == "backend"
        assert len(brain.constraints) == 1
        assert brain.architecture.pattern == "layered"
        assert "python" in brain.tech_stack.languages

    def test_roundtrip_serialization(self):
        """Test that brain -> dict -> brain preserves data."""
        brain = ProjectBrain(
            project_id="roundtrip",
            project_name="Roundtrip Test",
            project_summary="Testing roundtrip",
            current_phase="Phase 19B",
            current_focus="Testing",
        )
        brain.add_goal("Test goal")
        brain.add_task("Test task", owner_agent="tester")
        brain.add_decision("Use pytest", "We use pytest for testing")
        brain.add_constraint("No print statements", "Use logging instead")

        d = brain_to_dict(brain)
        restored = brain_from_dict(d)

        assert restored.project_id == brain.project_id
        assert restored.project_name == brain.project_name
        assert restored.project_summary == brain.project_summary
        assert restored.current_phase == brain.current_phase
        assert len(restored.active_goals) == len(brain.active_goals)
        assert len(restored.active_tasks) == len(brain.active_tasks)
        assert len(restored.decisions) == len(brain.decisions)
        assert len(restored.constraints) == len(brain.constraints)

    def test_brain_encoder_with_enum(self):
        encoder = BrainEncoder()
        assert encoder.default(RuntimeState.EXECUTING) == "executing"


# ═══════════════════════════════════════════════════════════════
# Brain Store Tests
# ═══════════════════════════════════════════════════════════════

class TestBrainStore:
    """Tests for BrainStore persistence."""

    @pytest.fixture
    def store(self, tmp_path):
        return BrainStore(storage_dir=str(tmp_path / "brains"))

    def test_create_brain(self, store):
        brain = store.create_brain("test-proj", "Test Project")
        assert brain.project_id == "test-proj"
        assert brain.project_name == "Test Project"
        assert store.brain_exists("test-proj")

    def test_save_and_load_brain(self, store):
        brain = store.create_brain("test-proj", "Test")
        brain.project_summary = "A test project"
        brain.add_task("Task 1")
        store.save_brain(brain)

        loaded = store.load_brain("test-proj")
        assert loaded is not None
        assert loaded.project_summary == "A test project"
        assert len(loaded.active_tasks) == 1

    def test_load_nonexistent_brain(self, store):
        loaded = store.load_brain("nonexistent")
        assert loaded is None

    def test_update_brain(self, store):
        store.create_brain("test-proj", "Test")
        updated = store.update_brain("test-proj", project_summary="Updated")
        assert updated is not None
        assert updated.project_summary == "Updated"

    def test_snapshot_brain(self, store):
        store.create_brain("test-proj", "Test")
        snap_path = store.snapshot_brain("test-proj")
        assert snap_path is not None
        assert Path(snap_path).exists()

    def test_list_brains(self, store):
        store.create_brain("proj1", "Project 1")
        store.create_brain("proj2", "Project 2")
        brains = store.list_brains()
        assert len(brains) == 2
        names = [b["project_name"] for b in brains]
        assert "Project 1" in names
        assert "Project 2" in names

    def test_delete_brain(self, store):
        store.create_brain("test-proj", "Test")
        assert store.brain_exists("test-proj")
        result = store.delete_brain("test-proj")
        assert result is True
        assert not store.brain_exists("test-proj")

    def test_brain_exists(self, store):
        assert not store.brain_exists("nonexistent")
        store.create_brain("test-proj", "Test")
        assert store.brain_exists("test-proj")


# ═══════════════════════════════════════════════════════════════
# Understanding Engine Tests
# ═══════════════════════════════════════════════════════════════

class TestUnderstandingEngine:
    """Tests for UnderstandingEngine."""

    @pytest.fixture
    def engine(self):
        return UnderstandingEngine()

    def test_analyze_simple_request(self, engine):
        result = engine.analyze("Добавь realtime notifications")
        assert result.objective != ""
        assert "notification" in result.objective.lower() or "realtime" in result.objective.lower()

    def test_analyze_websocket_request(self, engine):
        result = engine.analyze("Добавь WebSocket для realtime уведомлений")
        assert "websocket" in result.affected_areas or "backend" in result.affected_areas
        assert len(result.risks) > 0

    def test_analyze_api_request(self, engine):
        result = engine.analyze("Создай новый API endpoint для пользователей")
        assert "backend" in result.affected_areas

    def test_analyze_frontend_request(self, engine):
        result = engine.analyze("Обнови стили на главной странице")
        assert "frontend" in result.affected_areas

    def test_analyze_test_request(self, engine):
        result = engine.analyze("Напиши тесты для модуля")
        assert "testing" in result.affected_areas

    def test_analyze_auth_request(self, engine):
        result = engine.analyze("Настроить JWT авторизацию")
        assert "security" in result.affected_areas or "backend" in result.affected_areas
        assert len(result.risks) > 0

    def test_estimate_complexity_low(self, engine):
        result = engine.analyze("Опечатка в README")
        assert result.estimated_complexity == "low"

    def test_estimate_complexity_critical(self, engine):
        result = engine.analyze("Перепиши всю систему с нуля")
        assert result.estimated_complexity == "critical"

    def test_generate_clarification_questions(self, engine):
        result = engine.analyze("Добавь realtime notifications")
        assert len(result.clarification_questions) > 0

    def test_format_for_display(self, engine):
        result = engine.analyze("Добавь WebSocket")
        formatted = result.format_for_display()
        assert "понял" in formatted.lower() or "понял" in formatted
        assert "\n" in formatted  # multi-line output

    def test_suggest_agent(self, engine):
        result = engine.analyze("Создай API endpoint")
        assert result.suggested_agent != ""

    def test_execution_hypothesis(self, engine):
        result = engine.analyze("Добавь авторизацию")
        assert result.execution_hypothesis != ""

    def test_understanding_result_defaults(self):
        result = UnderstandingResult()
        assert result.objective == ""
        assert result.is_ready is False
        assert result.risks == []


# ═══════════════════════════════════════════════════════════════
# Task Contracts Tests
# ═══════════════════════════════════════════════════════════════

class TestTaskContract:
    """Tests for TaskContract."""

    def test_create_contract(self):
        contract = TaskContract(
            task_id="t1",
            title="Add auth",
            objective="Implement JWT authentication",
            owner_agent="backend",
        )
        assert contract.task_id == "t1"
        assert contract.title == "Add auth"
        assert contract.status == ContractStatus.DRAFT.value

    def test_validate_valid_contract(self):
        contract = TaskContract(
            task_id="t1",
            title="Test",
            objective="Test objective",
            owner_agent="backend",
            allowed_files=["main.py"],
        )
        issues = contract.validate()
        assert len(issues) == 0
        assert contract.is_valid() is True

    def test_validate_missing_objective(self):
        contract = TaskContract(task_id="t1", title="Test", owner_agent="backend",
                               allowed_files=["main.py"])
        issues = contract.validate()
        assert "Objective is required" in issues

    def test_validate_missing_agent(self):
        contract = TaskContract(task_id="t1", title="Test", objective="Test",
                               allowed_files=["main.py"])
        issues = contract.validate()
        assert "Owner agent is required" in issues

    def test_validate_missing_files(self):
        contract = TaskContract(task_id="t1", title="Test", objective="Test",
                               owner_agent="backend")
        issues = contract.validate()
        assert "allowed file or module" in issues[0]

    def test_to_prompt_context(self):
        contract = TaskContract(
            task_id="t1",
            title="Add auth",
            objective="Implement JWT",
            context_summary="Project uses FastAPI",
            allowed_files=["auth.py", "models.py"],
            forbidden_files=["main.py"],
            validation_rules=["Must have tests", "Must not break existing API"],
            acceptance_criteria=["JWT works", "Tests pass"],
        )
        context = contract.to_prompt_context()
        assert "Add auth" in context
        assert "Implement JWT" in context
        assert "FastAPI" in context
        assert "auth.py" in context
        assert "main.py" in context
        assert "Must have tests" in context


class TestTaskContractBuilder:
    """Tests for TaskContractBuilder."""

    def test_build_basic_contract(self):
        contract = (TaskContractBuilder("Add auth", "Implement JWT")
                    .with_agent("backend")
                    .with_allowed_files(["auth.py"])
                    .build())
        assert contract.title == "Add auth"
        assert contract.objective == "Implement JWT"
        assert contract.owner_agent == "backend"
        assert "auth.py" in contract.allowed_files
        assert contract.is_valid() is True

    def test_build_full_contract(self):
        contract = (TaskContractBuilder("Add WebSocket", "Implement realtime")
                    .with_context("Project uses FastAPI")
                    .with_allowed_files(["ws.py", "events.py"])
                    .with_forbidden_files(["main.py", "config.py"])
                    .with_skills(["python", "websocket"])
                    .with_validation_rules(["Tests required"])
                    .with_acceptance_criteria(["Realtime works"])
                    .with_priority("high")
                    .with_agent("backend")
                    .with_limits(max_files=5, max_lines=200)
                    .with_safety(test_required=True, review_required=True)
                    .build())
        assert contract.priority == "high"
        assert contract.max_files_changed == 5
        assert contract.max_lines_changed == 200
        assert contract.test_required is True
        assert len(contract.forbidden_files) == 2
        assert len(contract.required_skills) == 2

    def test_build_with_parent(self):
        contract = (TaskContractBuilder("Subtask", "Do something")
                    .with_agent("backend")
                    .with_parent("parent-task-id")
                    .build())
        assert contract.parent_task_id == "parent-task-id"


# ═══════════════════════════════════════════════════════════════
# Context Layers Tests
# ═══════════════════════════════════════════════════════════════

class TestContextLayers:
    """Tests for ContextLayers."""

    def test_create_default_layers(self):
        layers = ContextLayers()
        assert layers.system_identity.name == "System Identity"
        assert layers.project_brain.name == "Project Brain"
        assert layers.max_total_tokens == 150000

    def test_set_system_identity(self):
        layers = ContextLayers()
        layers.set_system_identity("AI Team System Developer Mode")
        assert layers.system_identity.content == "AI Team System Developer Mode"
        assert layers.system_identity.required is True

    def test_set_project_brain(self):
        layers = ContextLayers()
        brain_dict = {
            "project_name": "Test",
            "project_summary": "A test project",
            "active_tasks": [{"title": "Task 1"}],
        }
        layers.set_project_brain(brain_dict)
        assert "Test" in layers.project_brain.content
        assert "active_tasks" in layers.project_brain.content

    def test_set_current_sprint(self):
        layers = ContextLayers()
        layers.set_current_sprint(
            goals=[{"title": "Goal 1"}],
            tasks=[{"title": "Task 1"}],
        )
        assert "Goal 1" in layers.current_sprint.content

    def test_set_agent_task(self):
        layers = ContextLayers()
        layers.set_agent_task("## Task: Add auth\nImplement JWT")
        assert "Add auth" in layers.agent_task.content

    def test_add_custom_layer(self):
        layers = ContextLayers()
        layers.add_custom_layer("Custom", "Custom content", priority=60)
        assert len(layers.custom_layers) == 1
        assert layers.custom_layers[0].name == "Custom"

    def test_get_active_layers_sorted_by_priority(self):
        layers = ContextLayers()
        layers.set_system_identity("System")
        layers.set_project_brain({"project_name": "Test"})
        layers.set_agent_task("Task context")
        layers.add_custom_layer("Low", "Low priority", priority=10)

        active = layers.get_active_layers()
        priorities = [l.priority for l in active]
        assert priorities == sorted(priorities, reverse=True)

    def test_build_context(self):
        layers = ContextLayers()
        layers.set_system_identity("System identity content")
        layers.set_project_brain({"project_name": "Test", "active_tasks": []})

        context = layers.build_context()
        assert "System Identity" in context
        assert "Project Brain" in context

    def test_build_context_with_budget(self):
        layers = ContextLayers()
        layers.set_system_identity("System")
        layers.set_project_brain({"project_name": "Test"})

        # Very small budget should still include required layers
        context = layers.build_context(max_tokens=10000)
        assert "System Identity" in context

    def test_token_usage(self):
        layers = ContextLayers()
        layers.set_system_identity("System identity")
        layers.set_project_brain({"project_name": "Test"})

        usage = layers.get_token_usage()
        assert "total" in usage
        assert "budget" in usage
        assert "remaining" in usage
        assert usage["budget"] == 150000
        assert usage["total"] > 0

    def test_is_within_budget(self):
        layers = ContextLayers()
        layers.set_system_identity("Short")
        assert layers.is_within_budget() is True

    def test_context_layer_estimate_tokens(self):
        layer = ContextLayer(name="Test", content="a" * 400)
        assert layer.estimate_tokens() == 100


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestDeveloperIntegration:
    """Integration tests for the developer package."""

    def test_full_brain_lifecycle(self, tmp_path):
        """Create, modify, save, load, snapshot a brain."""
        store = BrainStore(storage_dir=str(tmp_path / "brains"))

        # Create
        brain = store.create_brain("my-project", "My Project")
        brain.project_summary = "A Python web app"
        brain.set_runtime_state(RuntimeState.PLANNING)

        # Modify
        brain.add_goal("Add auth", "Implement JWT auth")
        brain.add_task("Create auth module", owner_agent="backend")
        brain.add_decision("Use FastAPI", "FastAPI for async support")
        brain.add_constraint("No raw SQL", "Use ORM")
        brain.add_risk("Token theft", likelihood="low", impact="high")

        # Save
        store.save_brain(brain)

        # Load
        loaded = store.load_brain("my-project")
        assert loaded is not None
        assert loaded.project_summary == "A Python web app"
        assert loaded.runtime_state == "planning"
        assert len(loaded.active_goals) == 1
        assert len(loaded.active_tasks) == 1
        assert len(loaded.decisions) == 1
        assert len(loaded.constraints) == 1
        assert len(loaded.known_risks) == 1

        # Snapshot
        snap_path = store.snapshot_brain("my-project")
        assert snap_path is not None
        assert Path(snap_path).exists()

    def test_understanding_with_project_context(self):
        """Test understanding engine with project brain context."""
        engine = UnderstandingEngine()
        brain_dict = {
            "project_name": "Test",
            "tech_stack": {"languages": ["python"], "frameworks": ["fastapi"]},
            "active_tasks": [{"title": "Add auth"}],
        }
        result = engine.analyze("Добавь WebSocket для realtime", brain_dict)
        assert result.objective != ""
        assert len(result.risks) > 0

    def test_context_layers_with_brain(self):
        """Test context layers with a real brain."""
        brain = ProjectBrain(
            project_id="test",
            project_name="Test Project",
            project_summary="A test project",
            current_phase="Phase 19B",
        )
        brain.add_task("Task 1")
        brain.add_decision("Use FastAPI", "FastAPI for async")

        layers = ContextLayers()
        layers.set_system_identity("AI Team System Developer Mode")
        layers.set_project_brain(brain_to_dict(brain))

        context = layers.build_context()
        assert "Test Project" in context
        assert "Phase 19B" in context

        usage = layers.get_token_usage()
        assert usage["total"] < usage["budget"]

    def test_task_contract_from_understanding(self):
        """Test creating a task contract from understanding result."""
        engine = UnderstandingEngine()
        result = engine.analyze("Добавь API endpoint для пользователей")

        contract = (TaskContractBuilder(result.objective, result.objective)
                    .with_agent(result.suggested_agent)
                    .with_priority(result.estimated_complexity)
                    .with_allowed_files(["api/routes.py", "api/models.py"])
                    .with_validation_rules(["Must have tests"])
                    .build())

        assert contract.is_valid() is True
        assert contract.owner_agent != ""
