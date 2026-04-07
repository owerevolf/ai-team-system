"""
Plugin System - Расширяемые инструменты для агентов
"""

import json
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, field


@dataclass
class Plugin:
    name: str
    version: str
    description: str
    tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    enabled: bool = True


class PluginManager:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}
    
    def register(self, plugin: Plugin):
        """Регистрация плагина"""
        self.plugins[plugin.name] = plugin
        
        for tool_name, tool_def in plugin.tools.items():
            self.tools[tool_name] = tool_def
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """Получить все инструменты"""
        return {
            name: tool for name, tool in self.tools.items()
            if self._is_tool_enabled(name)
        }
    
    def _is_tool_enabled(self, tool_name: str) -> bool:
        """Проверка включенности инструмента"""
        for plugin in self.plugins.values():
            if tool_name in plugin.tools:
                return plugin.enabled
        return True
    
    def get_tools_description(self) -> str:
        """Текстовое описание для промпта"""
        lines = []
        for name, tool in self.get_tools().items():
            desc = tool.get("description", "No description")
            params = json.dumps(tool.get("parameters", {}), indent=2)
            lines.append(f"## {name}\n{desc}\nParameters: {params}")
        return "\n\n".join(lines)
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение инструмента"""
        tool = self.tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        handler = tool.get("handler")
        if not handler:
            return {"success": False, "error": f"No handler for: {tool_name}"}
        
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Built-in Plugins ───

def create_git_plugin() -> Plugin:
    """Git операции"""
    import subprocess
    
    def run_git(params: Dict) -> Dict[str, Any]:
        command = params.get("command", "status")
        cwd = params.get("cwd", ".")
        
        allowed = ["status", "log", "diff", "branch", "add", "commit"]
        if command not in allowed:
            return {"success": False, "error": f"Command not allowed: {command}"}
        
        try:
            result = subprocess.run(
                f"git {command}",
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:2000],
                "error": result.stderr[:500]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    return Plugin(
        name="git-tools",
        version="1.0.0",
        description="Git operations for version control",
        tools={
            "git_status": {
                "name": "git_status",
                "description": "Show git status",
                "parameters": {"type": "object", "properties": {"cwd": {"type": "string"}}},
                "handler": lambda p: run_git({**p, "command": "status"})
            },
            "git_log": {
                "name": "git_log",
                "description": "Show git log",
                "parameters": {"type": "object", "properties": {"cwd": {"type": "string"}}},
                "handler": lambda p: run_git({**p, "command": "log --oneline -10"})
            }
        }
    )


def create_file_search_plugin() -> Plugin:
    """Поиск по файлам"""
    import re
    
    def search_files(params: Dict) -> Dict[str, Any]:
        path = Path(params.get("path", "."))
        pattern = params.get("pattern", "")
        
        if not path.exists():
            return {"success": False, "error": "Path not found"}
        
        results = []
        for file_path in path.rglob("*"):
            if file_path.is_file() and re.search(pattern, file_path.name, re.IGNORECASE):
                results.append(str(file_path))
        
        return {"success": True, "matches": results[:50]}
    
    return Plugin(
        name="file-search",
        version="1.0.0",
        description="Search files by pattern",
        tools={
            "search_files": {
                "name": "search_files",
                "description": "Search for files matching a pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "pattern": {"type": "string"}
                    },
                    "required": ["pattern"]
                },
                "handler": search_files
            }
        }
    )
