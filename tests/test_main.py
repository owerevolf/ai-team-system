"""
Tests for AITeamSystem
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from core.main import AITeamSystem


class TestAITeamSystem:
    def setup_method(self):
        with patch('core.main.AgentManager'), \
             patch('core.main.ModelRouter'), \
             patch('core.main.Database'), \
             patch('core.main.setup_logger'):
            self.system = AITeamSystem()
            self.temp_dir = tempfile.mkdtemp()
            self.system.project_path = Path(self.temp_dir)
    
    def test_scan_hardware(self):
        with patch('core.main.SystemScanner') as mock_scanner:
            mock_instance = Mock()
            mock_instance.get_info.return_value = {
                "cpu": {"cores": 8, "threads": 16},
                "ram": {"total_gb": 32},
                "gpu": {"name": "RTX 3080"},
                "ollama": {"available": True}
            }
            mock_scanner.return_value = mock_instance
            self.system.scanner = mock_instance
            
            info = self.system.scan_hardware()
            
            assert info["cpu"]["cores"] == 8
    
    def test_create_project_structure(self):
        with patch('core.main.Database'):
            with patch('core.main.ProjectContext'):
                self.system.db = Mock()
                
                result = self.system.create_project(
                    "test_project",
                    "Test requirements"
                )
                
                assert "project_name" in result
                assert Path(self.temp_dir).exists()


class TestProjectCreation:
    def test_project_path_creation(self):
        with patch('core.main.AgentManager'), \
             patch('core.main.ModelRouter'), \
             patch('core.main.Database'), \
             patch('core.main.setup_logger'):
            
            system = AITeamSystem()
            system.project_path = Path(tempfile.mkdtemp())
            
            (system.project_path / "test.md").write_text("test")
            
            assert (system.project_path / "test.md").exists()
