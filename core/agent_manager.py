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
    
    def set_project_path(self, path: Path):
        """Установить путь к проекту"""
        self.project_path = path
    
    def _register_tools(self) -> Dict[str, Tool]:
        """Регистрация доступных инструментов"""
        return {
            "create_file": Tool(
                name="create_file",
                description="Создать файл с указанным содержимым. Используй для создания кода, конфигов, документации.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Путь к файлу относительно project_path"},
                        "content": {"type": "string", "description": "Содержимое файла"},
                        "description": {"type": "string", "description": "Описание что делает файл"}
                    },
                    "required": ["path", "content"]
                },
                handler=self._create_file
            ),
            "read_file": Tool(
                name="read_file", 
                description="Прочитать содержимое файла",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Путь к файлу"}
                    },
                    "required": ["path"]
                },
                handler=self._read_file
            ),
            "list_directory": Tool(
                name="list_directory",
                description="Показать файлы в директории",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Путь к директории"}
                    }
                },
                handler=self._list_directory
            ),
            "run_command": Tool(
                name="run_command",
                description="Выполнить shell команду",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Команда для выполнения"},
                        "cwd": {"type": "string", "description": "Рабочая директория"}
                    },
                    "required": ["command"]
                },
                handler=self._run_command
            ),
            "create_directory": Tool(
                name="create_directory",
                description="Создать директорию",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Путь к директории"}
                    },
                    "required": ["path"]
                },
                handler=self._create_directory
            ),
            "write_to_file": Tool(
                name="write_to_file",
                description="Добавить содержимое в конец файла",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Путь к файлу"},
                        "content": {"type": "string", "description": "Добавляемое содержимое"}
                    },
                    "required": ["path", "content"]
                },
                handler=self._append_to_file
            )
        }
    
    def get_tools_for_prompt(self) -> str:
        """Формирование текстового описания инструментов для промпта"""
        tools_desc = []
        for name, tool in self.tools.items():
            params = json.dumps(tool.parameters, indent=2)
            tools_desc.append(f"## {tool.name}\n{tool.description}\nParameters: {params}")
        return "\n\n".join(tools_desc)
    
    def get_agent_prompt(self, agent_name: str) -> str:
        """Загрузка промпта агента"""
        prompt_file = self.prompts_dir / f"{agent_name}.md"
        
        if not prompt_file.exists():
            self.logger.warning(f"Промпт для {agent_name} не найден")
            return self._get_default_prompt(agent_name)
        
        return prompt_file.read_text(encoding='utf-8')
    
    def _get_default_prompt(self, agent_name: str) -> str:
        """Дефолтный промпт если файл не найден"""
        return f"""Ты - {agent_name} agent в AI Team System.
Твоя задача - создавать код и файлы для проекта.

Используй инструменты для создания файлов.
Всегда создавай РЕАЛЬНЫЙ рабочий код, не примеры.
"""
    
    def run_agent(self, agent_name: str, task: str, context: Dict = None) -> Dict[str, Any]:
        """Запуск агента с задачей"""
        self.logger.info(f"Запуск агента: {agent_name}")
        
        prompt_template = self.get_agent_prompt(agent_name)
        tools_description = self.get_tools_for_prompt()
        
        full_prompt = f"""{prompt_template}

## PROJECT PATH: {self.project_path or 'Не указан'}

## AVAILABLE TOOLS
{tools_description}

## ЗАДАНИЕ
{task}

## КОНТЕКСТ
{json.dumps(context or {}, indent=2, ensure_ascii=False) if context else 'Нет контекста'}

## ИНСТРУКЦИИ
1. Проанализируй задачу
2. Если нужно создать код - используй create_file
3. Если нужно прочитать существующие файлы - используй read_file
4. Создавай РЕАЛЬНЫЙ рабочий код (не псевдокод)
5. После завершения верни JSON:
{{"status": "success", "files_created": ["file1.py", "file2.py"], "summary": "что сделано"}}

## FORMAT FOR TOOL CALLS
Когда нужен инструмент, верни:
<tool_call>
{{"tool": "tool_name", "path": "file.py", "content": "# код файла", "description": "что делает"}}
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
                "response": response,
                "files_created": created_files,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Агент {agent_name} завершил работу. Создано файлов: {len(created_files)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка агента {agent_name}: {e}")
            return {
                "agent": agent_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_and_create_files(self, response: str) -> List[str]:
        """Извлечение и создание файлов из ответа модели"""
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
                else:
                    path = tool_data.get("path")
                    content = tool_data.get("content", "")
                    if path and content:
                        success = self._create_file({"path": path, "content": content})
                        if success:
                            created.append(path)
                            
            except json.JSONDecodeError:
                self.logger.warning(f"Не удалось распарсить tool_call: {match[:100]}")
        
        if not created and self.project_path:
            code_blocks = re.findall(r'```(?:\w+)?\s*(.*?)```', response, re.DOTALL)
            for i, code in enumerate(code_blocks):
                path = f"code/generated_{len(created)}_{i}.py"
                success = self._create_file({"path": path, "content": code.strip()})
                if success:
                    created.append(path)
        
        return created
    
    def _create_file(self, params: Dict) -> Dict[str, Any]:
        """Создание файла"""
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            file_path = self.project_path / params["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(params["content"], encoding='utf-8')
            
            self.logger.info(f"Создан файл: {file_path}")
            return {"success": True, "path": str(file_path.relative_to(self.project_path))}
        except Exception as e:
            self.logger.error(f"Ошибка создания файла: {e}")
            return {"success": False, "error": str(e)}
    
    def _read_file(self, params: Dict) -> Dict[str, Any]:
        """Чтение файла"""
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
        """Список файлов в директории"""
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
        """Выполнение команды"""
        try:
            cwd = params.get("cwd", str(self.project_path) if self.project_path else None)
            result = subprocess.run(
                params["command"],
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_directory(self, params: Dict) -> Dict[str, Any]:
        """Создание директории"""
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            dir_path = self.project_path / params["path"]
            dir_path.mkdir(parents=True, exist_ok=True)
            
            return {"success": True, "path": str(dir_path.relative_to(self.project_path))}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _append_to_file(self, params: Dict) -> Dict[str, Any]:
        """Добавление в файл"""
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
    
    def run_parallel(self, tasks: Dict[str, str]) -> Dict[str, Any]:
        """Параллельный запуск агентов"""
        import concurrent.futures
        
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.run_agent, agent, task): agent 
                for agent, task in tasks.items()
            }
            
            for future in concurrent.futures.as_completed(futures):
                agent = futures[future]
                try:
                    results[agent] = future.result()
                except Exception as e:
                    results[agent] = {"agent": agent, "status": "error", "error": str(e)}
        
        return results
