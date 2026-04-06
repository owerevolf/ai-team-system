"""
Tests for ProjectContext
"""

import pytest
from pathlib import Path

from core.project_context import ProjectContext, AgentResult


class TestProjectContext:
    def setup_method(self):
        self.context = ProjectContext(
            project_id=1,
            project_name="test_project",
            project_path=Path("/tmp/test_project"),
            requirements="Test requirements"
        )
    
    def test_init(self):
        assert self.context.project_id == 1
        assert self.context.project_name == "test_project"
        assert self.context.phase == "init"
    
    def test_set_phase(self):
        self.context.set_phase("development")
        assert self.context.phase == "development"
    
    def test_add_result(self):
        result = AgentResult(
            agent="backend",
            status="success",
            files_created=["main.py", "models.py"]
        )
        
        self.context.add_result(result)
        
        assert "backend" in self.context.agent_results
        assert len(self.context.agent_results["backend"].files_created) == 2
    
    def test_get_context_for_agent(self):
        self.context.architecture = {"stack": "FastAPI"}
        
        context = self.context.get_context_for_agent("backend")
        
        assert "project" in context
        assert context["project"]["name"] == "test_project"
        assert "architecture" in context
    
    def test_get_all_files(self):
        self.context.add_result(AgentResult(
            agent="backend",
            status="success",
            files_created=["file1.py"]
        ))
        self.context.add_result(AgentResult(
            agent="frontend",
            status="success",
            files_created=["index.html"]
        ))
        
        files = self.context.get_all_files()
        
        assert len(files) == 2
        assert "file1.py" in files
        assert "index.html" in files
    
    def test_get_summary(self):
        self.context.add_result(AgentResult(
            agent="backend",
            status="success",
            files_created=["main.py"]
        ))
        
        summary = self.context.get_summary()
        
        assert summary["project_id"] == 1
        assert summary["project_name"] == "test_project"
        assert summary["agents_completed"] == 1
        assert summary["total_files"] == 1
    
    def test_to_dict(self):
        data = self.context.to_dict()
        
        assert isinstance(data, dict)
        assert data["project_name"] == "test_project"
    
    def test_from_dict(self):
        data = {
            "project_id": 1,
            "project_name": "test",
            "project_path": "/tmp/test",
            "requirements": "req",
            "phase": "init",
            "plan": {},
            "architecture": {},
            "agent_results": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        context = ProjectContext.from_dict(data)
        
        assert context.project_name == "test"


class TestAgentResult:
    def test_init(self):
        result = AgentResult(
            agent="tester",
            status="success",
            files_created=["test.py"]
        )
        
        assert result.agent == "tester"
        assert result.status == "success"
        assert len(result.files_created) == 1
        assert result.timestamp is not None
