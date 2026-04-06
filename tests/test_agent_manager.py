"""
Tests for AgentManager
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from core.agent_manager import AgentManager, ALLOWED_COMMANDS


class TestAgentManager:
    def setup_method(self):
        with patch('core.agent_manager.ModelRouter'):
            with patch('core.agent_manager.Database'):
                self.manager = AgentManager(Mock())
                self.temp_dir = tempfile.mkdtemp()
                self.manager.project_path = Path(self.temp_dir)
    
    def test_create_file_success(self):
        result = self.manager._create_file({
            "path": "test.py",
            "content": "print('hello')"
        })
        
        assert result["success"] is True
        assert (Path(self.temp_dir) / "test.py").exists()
    
    def test_create_file_nested_path(self):
        result = self.manager._create_file({
            "path": "src/models/user.py",
            "content": "class User: pass"
        })
        
        assert result["success"] is True
        assert (Path(self.temp_dir) / "src" / "models" / "user.py").exists()
    
    def test_read_file(self):
        test_file = Path(self.temp_dir) / "readable.txt"
        test_file.write_text("test content")
        
        result = self.manager._read_file({"path": "readable.txt"})
        
        assert result["success"] is True
        assert "test content" in result["content"]
    
    def test_read_file_not_found(self):
        result = self.manager._read_file({"path": "nonexistent.txt"})
        
        assert result["success"] is False
    
    def test_list_directory(self):
        (Path(self.temp_dir) / "file1.py").touch()
        (Path(self.temp_dir) / "file2.py").touch()
        
        result = self.manager._list_directory({"path": "."})
        
        assert result["success"] is True
        assert len(result["files"]) == 2
    
    def test_create_directory(self):
        result = self.manager._create_directory({"path": "new_folder"})
        
        assert result["success"] is True
        assert (Path(self.temp_dir) / "new_folder").is_dir()
    
    def test_append_to_file(self):
        file_path = Path(self.temp_dir) / "append.txt"
        file_path.write_text("initial\n")
        
        self.manager._append_to_file({
            "path": "append.txt",
            "content": "appended\n"
        })
        
        assert file_path.read_text() == "initial\nappended\n"


class TestCommandWhitelist:
    def test_allowed_commands(self):
        allowed = ["python", "pip install", "git commit", "pytest tests/"]
        
        for cmd in allowed:
            assert cmd.split()[0] in ALLOWED_COMMANDS or any(
                cmd.startswith(p.replace("*", "").strip()) 
                for p in ALLOWED_COMMANDS
            )
    
    def test_command_whitelist_check(self):
        with patch('core.agent_manager.ModelRouter'):
            with patch('core.agent_manager.Database'):
                manager = AgentManager(Mock())
                
                assert manager._is_command_allowed("python main.py") is True
                assert manager._is_command_allowed("ls -la") is True
                assert manager._is_command_allowed("rm -rf /") is False
