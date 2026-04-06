"""
ProjectContext - Общий контекст для всех агентов
Передаёт артефакты между фазами и агентами
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json


@dataclass
class AgentResult:
    agent: str
    status: str
    files_created: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProjectContext:
    project_id: int
    project_name: str
    project_path: Path
    requirements: str
    
    phase: str = "init"
    
    plan: Dict[str, Any] = field(default_factory=dict)
    architecture: Dict[str, Any] = field(default_factory=dict)
    
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()
    
    def set_phase(self, phase: str):
        self.phase = phase
        self.update_timestamp()
    
    def add_result(self, result: AgentResult):
        self.agent_results[result.agent] = result
        self.update_timestamp()
    
    def get_context_for_agent(self, agent: str) -> Dict[str, Any]:
        """Получить контекст для конкретного агента"""
        context = {
            "project": {
                "name": self.project_name,
                "path": str(self.project_path)
            },
            "requirements": self.requirements,
            "current_phase": self.phase
        }
        
        if agent == "backend":
            context["architecture"] = self.architecture
            context["previous_results"] = {
                "architect": asdict(self.agent_results.get("architect", AgentResult(agent="architect", status="pending")))
            }
        
        elif agent == "frontend":
            context["architecture"] = self.architecture
            context["api_spec"] = self.architecture.get("api_endpoints", {})
            context["previous_results"] = {
                "architect": asdict(self.agent_results.get("architect", AgentResult(agent="architect", status="pending"))),
                "backend": asdict(self.agent_results.get("backend", AgentResult(agent="backend", status="pending")))
            }
        
        elif agent == "tester":
            context["architecture"] = self.architecture
            context["previous_results"] = {
                name: asdict(r) for name, r in self.agent_results.items()
            }
        
        elif agent == "documentalist":
            context["architecture"] = self.architecture
            context["all_results"] = {
                name: asdict(r) for name, r in self.agent_results.items()
            }
            context["files_created"] = self.get_all_files()
        
        elif agent == "devops":
            context["architecture"] = self.architecture
            context["files_created"] = self.get_all_files()
        
        return context
    
    def get_all_files(self) -> List[str]:
        """Все созданные файлы"""
        files = []
        for result in self.agent_results.values():
            files.extend(result.files_created)
        return files
    
    def get_summary(self) -> Dict[str, Any]:
        """Сводка по проекту"""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "phase": self.phase,
            "agents_completed": len(self.agent_results),
            "total_files": len(self.get_all_files()),
            "status": "success" if all(r.status == "success" for r in self.agent_results.values()) else "partial",
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectContext":
        data["project_path"] = Path(data["project_path"])
        data["agent_results"] = {
            k: AgentResult(**v) for k, v in data.get("agent_results", {}).items()
        }
        return cls(**data)
