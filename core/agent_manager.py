"""
Agent Manager - Управление AI агентами с Tool Calling
"""

import os
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field

from .model_router import ModelRouter
from .database import Database
from .logger import setup_logger


ALLOWED_COMMANDS = {
    "python", "python3", "pip", "pip3", "pip install",
    "node", "npm", "npx",
    "git", "git add", "git commit", "git status", "git clone", "git pull", "git push",
    "pytest", "pytest tests/", "python -m pytest",
    "mkdir", "ls", "ls -la", "pwd", "cd",
    "uvicorn", "flask", "fastapi",
    "docker", "docker-compose",
    "curl", "wget",
    "cat", "head", "tail", "grep",
    "chmod", "chown",
    "echo"
}

ALLOWED_PATTERNS = [
    r"^python.*",
    r"^pip install.*",
    r"^git .*",
    r"^pytest.*",
    r"^mkdir.*",
    r"^ls.*",
    r"^cd .* && .*",
]


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable = None


@dataclass
class AgentTask:
    id: str
    agent: str
    task: str
    context: Dict = field(default_factory=dict)
    result: Any = None
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)


class AgentManager:
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.db = Database()
        self.logger = setup_logger("agent_manager")
        self.prompts_dir = Path(__file__).parent.parent / "prompts" / "roles"
        self.tools = self._register_tools()
        self.project_path: Optional[Path] = None
        self.context = None
        self.event_callback: Optional[Callable] = None
    
    def set_project_path(self, path: Path):
        self.project_path = path
    
    def set_context(self, context):
        self.context = context
    
    def set_event_callback(self, callback: Callable):
        self.event_callback = callback
    
    def emit_event(self, event_type: str, data: Dict[str, Any]):
        if self.event_callback:
            self.event_callback(event_type, data)
        self.logger.info(f"Event: {event_type} - {data.get('agent', 'system')}")
    
    def _is_command_allowed(self, command: str) -> bool:
        """Проверка команды по whitelist"""
        command_lower = command.lower().strip()
        
        if command_lower in ALLOWED_COMMANDS:
            return True
        
        for pattern in ALLOWED_PATTERNS:
            if re.match(pattern, command_lower):
                return True
        
        first_word = command_lower.split()[0] if command_lower.split() else ""
        if first_word in ALLOWED_COMMANDS:
            return True
        
        return False
    
    def _register_tools(self) -> Dict[str, Tool]:
        return {
            "create_file": Tool(
                name="create_file",
                description="Создать файл. Безопасная операция.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["path", "content"]
                },
                handler=self._create_file
            ),
            "read_file": Tool(
                name="read_file", 
                description="Прочитать файл.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                handler=self._read_file
            ),
            "list_directory": Tool(
                name="list_directory",
                description="Показать файлы в директории.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    }
                },
                handler=self._list_directory
            ),
            "run_command": Tool(
                name="run_command",
                description="Выполнить безопасную команду. Разрешены только: python, pip, git, pytest, npm, mkdir, ls",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"}
                    },
                    "required": ["command"]
                },
                handler=self._run_command
            ),
            "create_directory": Tool(
                name="create_directory",
                description="Создать директорию.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                handler=self._create_directory
            ),
            "write_to_file": Tool(
                name="write_to_file",
                description="Добавить в конец файла.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                },
                handler=self._append_to_file
            )
        }
    
    def get_tools_for_prompt(self) -> str:
        tools_desc = []
        for name, tool in self.tools.items():
            params = json.dumps(tool.parameters, indent=2)
            tools_desc.append(f"## {tool.name}\n{tool.description}\nParameters: {params}")
        return "\n\n".join(tools_desc)
    
    def get_agent_prompt(self, agent_name: str) -> str:
        prompt_file = self.prompts_dir / f"{agent_name}.md"
        
        if not prompt_file.exists():
            self.logger.warning(f"Промпт для {agent_name} не найден")
            return self._get_default_prompt(agent_name)
        
        return prompt_file.read_text(encoding='utf-8')
    
    def _get_default_prompt(self, agent_name: str) -> str:
        return f"""Ты - {agent_name} agent в AI Team System.
Создавай РЕАЛЬНЫЙ рабочий код.
Используй инструменты для создания файлов."""
    
    def run_agent(self, agent_name: str, task: str, context: Dict = None) -> Dict[str, Any]:
        self.logger.info(f"Запуск агента: {agent_name}")
        self.emit_event("agent_start", {"agent": agent_name})
        
        prompt_template = self.get_agent_prompt(agent_name)
        tools_description = self.get_tools_for_prompt()
        
        agent_context = {}
        if self.context:
            agent_context = self.context.get_context_for_agent(agent_name)
        
        full_prompt = f"""{prompt_template}

## PROJECT PATH: {self.project_path or 'Не указан'}

## AVAILABLE TOOLS
{tools_description}

## ALLOWED COMMANDS (whitelist)
python, pip, git, pytest, npm, mkdir, ls, docker, docker-compose

## ЗАДАНИЕ
{task}

## CONTEXT (от других агентов)
{json.dumps(context or agent_context, indent=2, ensure_ascii=False) if (context or agent_context) else 'Нет контекста'}

## ИНСТРУКЦИИ
1. Проанализируй задачу
2. Используй create_file для создания кода
3. Создавай РЕАЛЬНЫЙ рабочий код
4. После завершения верни JSON:
{{"status": "success", "files_created": ["file1.py"], "summary": "что сделано"}}

## TOOL CALL FORMAT
<tool_call>
{{"tool": "create_file", "path": "file.py", "content": "# код"}}
</tool_call>

Начни работу!
"""
        
        try:
            response = self.model_router.generate(
                prompt=full_prompt,
                agent=agent_name
            )
            
            created_files = self._extract_and_create_files(response)
            
            result = {
                "agent": agent_name,
                "status": "success",
                "response": response[:500],
                "files_created": created_files,
                "timestamp": datetime.now().isoformat()
            }
            
            self.emit_event("agent_complete", {"agent": agent_name, "files": created_files})
            self.logger.info(f"Агент {agent_name} завершил. Файлов: {len(created_files)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка {agent_name}: {e}")
            self.emit_event("agent_error", {"agent": agent_name, "error": str(e)})
            return {
                "agent": agent_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_and_create_files(self, response: str) -> List[str]:
        created = []
        tool_pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        matches = re.findall(tool_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                tool_data = json.loads(match)
                tool_name = tool_data.get("tool", "create_file")
                
                if tool_name in self.tools and self.tools[tool_name].handler:
                    result = self.tools[tool_name].handler(tool_data)
                    if result.get("success"):
                        created.append(result.get("path", "unknown"))
                        
            except json.JSONDecodeError:
                self.logger.warning(f"Bad tool_call: {match[:100]}")
        
        if not created and self.project_path:
            code_blocks = re.findall(r'```(?:\w+)?\s*(.*?)```', response, re.DOTALL)
            for i, code in enumerate(code_blocks):
                path = f"code/generated_{len(created)}_{i}.py"
                success = self._create_file({"path": path, "content": code.strip()})
                if success.get("success"):
                    created.append(path)
        
        return created
    
    def _create_file(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            file_path = self.project_path / params["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(params["content"], encoding='utf-8')
            
            self.logger.info(f"Создан: {file_path}")
            return {"success": True, "path": str(file_path.relative_to(self.project_path))}
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {"success": False, "error": str(e)}
    
    def _read_file(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            file_path = self.project_path / params["path"]
            if not file_path.exists():
                return {"success": False, "error": "File not found"}
            
            content = file_path.read_text(encoding='utf-8')
            return {"success": True, "content": content[:5000]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _list_directory(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            dir_path = self.project_path / params.get("path", ".")
            if not dir_path.exists():
                return {"success": False, "error": "Directory not found"}
            
            files = [str(p.relative_to(self.project_path)) for p in dir_path.rglob("*") if p.is_file()]
            return {"success": True, "files": files}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_command(self, params: Dict) -> Dict[str, Any]:
        command = params.get("command", "")
        
        if not self._is_command_allowed(command):
            self.logger.warning(f"Blocked command: {command}")
            return {
                "success": False,
                "error": f"Command not allowed: {command[:50]}",
                "blocked": True
            }
        
        try:
            cwd = params.get("cwd", str(self.project_path) if self.project_path else None)
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout (120s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_directory(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            dir_path = self.project_path / params["path"]
            dir_path.mkdir(parents=True, exist_ok=True)
            
            return {"success": True, "path": str(dir_path.relative_to(self.project_path))}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _append_to_file(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            file_path = self.project_path / params["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "a", encoding='utf-8') as f:
                f.write(params["content"])
            
            return {"success": True, "path": str(file_path.relative_to(self.project_path))}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_parallel(self, tasks: Dict[str, str], callback: Callable = None) -> Dict[str, Any]:
        """Параллельный запуск агентов"""
        import concurrent.futures
        
        results = {}
        
        def run_with_callback(agent, task):
            result = self.run_agent(agent, task)
            if callback:
                callback(agent, result)
            return agent, result
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(run_with_callback, agent, task): agent 
                for agent, task in tasks.items()
            }
            
            for future in concurrent.futures.as_completed(futures):
                agent = futures[future]
                try:
                    _, result = future.result()
                    results[agent] = result
                except Exception as e:
                    results[agent] = {"agent": agent, "status": "error", "error": str(e)}
        
        return results
