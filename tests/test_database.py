"""
Tests for Database
"""

import pytest
import tempfile
import os
from pathlib import Path

from core.database import Database


class TestDatabase:
    def setup_method(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = Database(self.temp_db.name)
    
    def teardown_method(self):
        self.db.close()
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_create_project(self):
        project_id = self.db.create_project(
            name="test_project",
            path="/tmp/test",
            profile="medium",
            requirements="test requirements"
        )
        
        assert project_id > 0
        
        project = self.db.get_project(project_id)
        assert project is not None
        assert project["name"] == "test_project"
    
    def test_get_project_not_found(self):
        result = self.db.get_project(99999)
        assert result is None
    
    def test_update_project_status(self):
        project_id = self.db.create_project(
            name="test",
            path="/tmp/test",
            profile="light",
            requirements=""
        )
        
        self.db.update_project_status(project_id, "completed")
        
        project = self.db.get_project(project_id)
        assert project["status"] == "completed"
    
    def test_create_task(self):
        project_id = self.db.create_project(
            name="test",
            path="/tmp/test",
            profile="light",
            requirements=""
        )
        
        task_id = self.db.create_task(
            project_id=project_id,
            agent="backend",
            title="Create API",
            description="Create REST API",
            priority="high"
        )
        
        assert task_id > 0
        
        tasks = self.db.get_tasks(project_id)
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Create API"
    
    def test_update_task_status(self):
        project_id = self.db.create_project(
            name="test",
            path="/tmp/test",
            profile="light",
            requirements=""
        )
        
        task_id = self.db.create_task(
            project_id=project_id,
            agent="backend",
            title="Test task"
        )
        
        self.db.update_task_status(task_id, "in_progress")
        self.db.update_task_status(task_id, "completed", '{"result": "done"}')
        
        tasks = self.db.get_tasks(project_id)
        assert tasks[0]["status"] == "completed"
    
    def test_log(self):
        project_id = self.db.create_project(
            name="test",
            path="/tmp/test",
            profile="light",
            requirements=""
        )
        
        self.db.log(project_id, "backend", "INFO", "Task completed")
        
        logs = self.db.get_logs(project_id)
        assert len(logs) >= 1
        assert logs[0]["message"] == "Task completed"
