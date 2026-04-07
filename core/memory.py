"""
Long-term Memory - Агенты запоминают прошлые проекты и учатся на ошибках
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    project_name: str
    agent: str
    action: str
    result: str
    lessons: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "agent": self.agent,
            "action": self.action,
            "result": self.result,
            "lessons": self.lessons,
            "files_created": self.files_created,
            "errors": self.errors,
            "timestamp": self.timestamp
        }


class AgentMemory:
    def __init__(self, memory_dir: Optional[Path] = None):
        if memory_dir is None:
            memory_dir = Path.home() / ".ai_team" / "memory"
        
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.entries: List[MemoryEntry] = []
        self._load()
    
    def _load(self):
        """Загрузка памяти из файлов"""
        memory_file = self.memory_dir / "memory.json"
        if memory_file.exists():
            try:
                data = json.loads(memory_file.read_text())
                self.entries = [MemoryEntry(**e) for e in data]
            except (json.JSONDecodeError, KeyError):
                self.entries = []
    
    def save(self):
        """Сохранение памяти"""
        memory_file = self.memory_dir / "memory.json"
        data = [e.to_dict() for e in self.entries]
        memory_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    def add(self, entry: MemoryEntry):
        """Добавление записи"""
        self.entries.append(entry)
        self.save()
    
    def search(self, agent: str = None, action: str = None, 
               project_pattern: str = None, limit: int = 10) -> List[MemoryEntry]:
        """Поиск в памяти"""
        results = self.entries
        
        if agent:
            results = [e for e in results if e.agent == agent]
        
        if action:
            results = [e for e in results if action.lower() in e.action.lower()]
        
        if project_pattern:
            results = [e for e in results 
                      if project_pattern.lower() in e.project_name.lower()]
        
        return results[-limit:]
    
    def get_lessons(self, agent: str = None) -> List[str]:
        """Получить все уроки"""
        lessons = []
        entries = self.entries
        if agent:
            entries = [e for e in entries if e.agent == agent]
        
        for e in entries:
            lessons.extend(e.lessons)
        
        return list(set(lessons))
    
    def get_common_errors(self, agent: str = None) -> Dict[str, int]:
        """Частые ошибки"""
        error_counts = {}
        entries = self.entries
        if agent:
            entries = [e for e in entries if e.agent == agent]
        
        for e in entries:
            for error in e.errors:
                error_key = hashlib.md5(error.encode()).hexdigest()[:8]
                error_counts[error_key] = error_counts.get(error_key, 0) + 1
        
        return dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True))
    
    def get_context_for_agent(self, agent: str, current_task: str) -> str:
        """Получить релевантный контекст для агента"""
        entries = self.search(agent=agent, limit=5)
        
        if not entries:
            return "Нет предыдущего опыта."
        
        lessons = []
        for e in entries:
            if e.lessons:
                lessons.extend(e.lessons)
        
        errors = []
        for e in entries:
            if e.errors:
                errors.extend(e.errors[:2])
        
        context = f"Предыдущий опыт ({len(entries)} записей):\n\n"
        
        if lessons:
            context += "Уроки:\n" + "\n".join(f"- {l}" for l in lessons[:5]) + "\n\n"
        
        if errors:
            context += "Частые ошибки (избегай):\n" + "\n".join(f"- {e}" for e in errors[:3]) + "\n\n"
        
        context += "Созданные файлы ранее:\n"
        all_files = []
        for e in entries:
            all_files.extend(e.files_created)
        for f in list(set(all_files))[:10]:
            context += f"- {f}\n"
        
        return context
    
    def stats(self) -> Dict[str, Any]:
        """Статистика памяти"""
        agents = set(e.agent for e in self.entries)
        projects = set(e.project_name for e in self.entries)
        total_lessons = sum(len(e.lessons) for e in self.entries)
        total_errors = sum(len(e.errors) for e in self.entries)
        
        return {
            "total_entries": len(self.entries),
            "agents": list(agents),
            "projects": list(projects),
            "total_lessons": total_lessons,
            "total_errors": total_errors,
            "memory_file": str(self.memory_dir / "memory.json")
        }
