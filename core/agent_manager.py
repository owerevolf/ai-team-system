"""
Agent Manager - Управление AI агентами
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from model_router import ModelRouter
from database import Database
from logger import setup_logger


class AgentManager:
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.db = Database()
        self.logger = setup_logger("agent_manager")
        self.prompts_dir = Path(__file__).parent.parent / "prompts" / "roles"
    
    def get_agent_prompt(self, agent_name: str) -> str:
        """Загрузка промпта агента"""
        prompt_file = self.prompts_dir / f"{agent_name}.md"
        
        if not prompt_file.exists():
            self.logger.warning(f"Промпт для {agent_name} не найден")
            return f"Ты - {agent_name} agent. Выполни задачу."
        
        return prompt_file.read_text()
    
    def run_agent(self, agent_name: str, task: str, context: Dict = None) -> Dict[str, Any]:
        """Запуск агента с задачей"""
        self.logger.info(f"Запуск агента: {agent_name}")
        
        prompt = self.get_agent_prompt(agent_name)
        
        full_prompt = f"""
{prompt}

## ЗАДАНИЕ
{task}

## КОНТЕКСТ
{json.dumps(context or {}, indent=2, ensure_ascii=False) if context else 'Нет контекста'}

## ИНСТРУКЦИИ
1. Проанализируй задачу
2. Выполни необходимые действия
3. Верни результат в JSON формате
"""
        
        try:
            response = self.model_router.generate(
                prompt=full_prompt,
                agent=agent_name
            )
            
            result = {
                "agent": agent_name,
                "status": "success",
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Агент {agent_name} завершил работу")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка агента {agent_name}: {e}")
            return {
                "agent": agent_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_parallel(self, tasks: Dict[str, str]) -> Dict[str, Any]:
        """Параллельный запуск нескольких агентов"""
        results = {}
        
        for agent_name, task in tasks.items():
            results[agent_name] = self.run_agent(agent_name, task)
        
        return results
    
    def create_file(self, path: str, content: str) -> bool:
        """Создание файла"""
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            self.logger.info(f"Файл создан: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка создания файла {path}: {e}")
            return False
    
    def execute_command(self, command: str, cwd: str = None) -> Dict[str, Any]:
        """Выполнение shell команды"""
        try:
            result = subprocess.run(
                command,
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
            return {
                "success": False,
                "error": "Command timeout",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "returncode": -1
            }
