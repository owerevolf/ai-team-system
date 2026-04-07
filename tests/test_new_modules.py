"""
Tests for new modules
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.token_tracker import TokenTracker, TokenUsage
from core.dry_run import DryRunSimulator
from core.zip_export import ZipExporter
from core.plugins import PluginManager, Plugin, create_git_plugin, create_file_search_plugin


class TestTokenTracker:
    def setup_method(self):
        self.tracker = TokenTracker()
    
    def test_record(self):
        self.tracker.record("backend", "ollama", 1000, 500, 3)
        
        assert len(self.tracker.usage) == 1
        assert self.tracker.usage[0].agent == "backend"
    
    def test_get_total(self):
        self.tracker.record("backend", "groq", 1000, 500, 3)
        self.tracker.record("frontend", "deepseek", 2000, 800, 5)
        
        stats = self.tracker.get_total()
        
        assert stats["total_calls"] == 2
        assert stats["total_tokens"] == 4300
        assert stats["total_files"] == 8
    
    def test_cost_calculation(self):
        self.tracker.record("backend", "deepseek", 1_000_000, 500_000, 1)
        
        stats = self.tracker.get_total()
        assert stats["total_cost"] > 0
    
    def test_format_report(self):
        self.tracker.record("backend", "ollama", 100, 50, 1)
        
        report = self.tracker.format_report()
        
        assert "backend" in report
        assert "ollama" in report
    
    def test_save(self):
        temp_dir = tempfile.mkdtemp()
        tracker = TokenTracker(Path(temp_dir))
        tracker.record("backend", "ollama", 100, 50, 1)
        tracker.save()
        
        assert (Path(temp_dir) / "token_usage.json").exists()


class TestDryRunSimulator:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.simulator = DryRunSimulator(Path(self.temp_dir))
    
    def test_simulate_agent(self):
        result = self.simulator.simulate_agent("backend", "Create API")
        
        assert result["status"] == "success (dry run)"
        assert result["simulated"] is True
    
    def test_get_plan(self):
        self.simulator.simulate_agent("teamlead", "Plan")
        self.simulator.simulate_agent("architect", "Design")
        
        plan = self.simulator.get_plan()
        
        assert plan["mode"] == "dry-run"
        assert plan["total_actions"] == 2
    
    def test_save_plan(self):
        self.simulator.simulate_agent("backend", "Test")
        self.simulator.save_plan()
        
        assert (Path(self.temp_dir) / "dry_run_plan.json").exists()


class TestZipExporter:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        (Path(self.temp_dir) / "test.py").write_text("print('hello')")
        (Path(self.temp_dir) / "readme.md").write_text("# Test")
    
    def test_export(self):
        exporter = ZipExporter(Path(self.temp_dir))
        output = Path(self.temp_dir) / "export.zip"
        
        result = exporter.export(output)
        
        assert result.exists()
        assert result.stat().st_size > 0
    
    def test_get_size_info(self):
        exporter = ZipExporter(Path(self.temp_dir))
        info = exporter.get_size_info()
        
        assert info["total_files"] == 2
        assert info["total_size_mb"] >= 0


class TestPluginManager:
    def setup_method(self):
        self.manager = PluginManager()
    
    def test_register_plugin(self):
        plugin = Plugin(
            name="test",
            version="1.0.0",
            description="Test plugin",
            tools={"test_tool": {"description": "Test", "handler": None}}
        )
        
        self.manager.register(plugin)
        
        assert "test_tool" in self.manager.tools
    
    def test_get_tools_description(self):
        plugin = Plugin(
            name="test",
            version="1.0.0",
            description="Test",
            tools={"test_tool": {"description": "A test tool", "parameters": {}}}
        )
        
        self.manager.register(plugin)
        desc = self.manager.get_tools_description()
        
        assert "test_tool" in desc
    
    def test_execute_tool(self):
        def handler(params):
            return {"success": True, "result": params.get("value")}
        
        plugin = Plugin(
            name="test",
            version="1.0.0",
            description="Test",
            tools={"add": {"description": "Add", "handler": handler}}
        )
        
        self.manager.register(plugin)
        result = self.manager.execute_tool("add", {"value": 42})
        
        assert result["success"] is True
        assert result["result"] == 42
    
    def test_execute_unknown_tool(self):
        result = self.manager.execute_tool("unknown", {})
        
        assert result["success"] is False
    
    def test_create_git_plugin(self):
        plugin = create_git_plugin()
        
        assert plugin.name == "git-tools"
        assert "git_status" in plugin.tools
    
    def test_create_file_search_plugin(self):
        plugin = create_file_search_plugin()
        
        assert plugin.name == "file-search"
        assert "search_files" in plugin.tools
