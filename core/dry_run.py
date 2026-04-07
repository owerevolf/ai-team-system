"""
Dry Run Mode - Тестирование без вызова LLM
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class DryRunSimulator:
    """Симуляция работы агентов без вызова LLM"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.actions: list = []
    
    def simulate_agent(self, agent: str, task: str) -> Dict[str, Any]:
        """Симуляция работы агента"""
        self.actions.append({
            "agent": agent,
            "task": task[:100],
            "time": datetime.now().isoformat()
        })
        
        return {
            "agent": agent,
            "status": "success (dry run)",
            "files_created": [],
            "simulated": True
        }
    
    def get_plan(self) -> Dict[str, Any]:
        """Получить план действий"""
        return {
            "mode": "dry-run",
            "project": self.project_path.name,
            "phases": [
                {"phase": "planning", "agent": "teamlead"},
                {"phase": "architecture", "agent": "architect"},
                {"phase": "development", "agents": ["backend", "frontend", "devops"]},
                {"phase": "testing", "agent": "tester"},
                {"phase": "documentation", "agent": "documentalist"}
            ],
            "actions": self.actions,
            "total_actions": len(self.actions)
        }
    
    def save_plan(self):
        """Сохранить план"""
        plan = self.get_plan()
        (self.project_path / "dry_run_plan.json").write_text(
            json.dumps(plan, indent=2, ensure_ascii=False)
        )
