"""
Learning Mode - Режим обучения для новичков
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TutorialStep:
    id: int
    title: str
    description: str
    hint: str
    action: str
    completed: bool = False


@dataclass
class GlossaryEntry:
    term: str
    definition: str
    example: str = ""


@dataclass
class LearningProgress:
    user_id: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_steps: List[int] = field(default_factory=list)
    total_steps: int = 10
    concepts_learned: List[str] = field(default_factory=list)
    
    @property
    def progress_percent(self) -> float:
        return (len(self.completed_steps) / self.total_steps) * 100 if self.total_steps > 0 else 0
    
    @property
    def is_complete(self) -> bool:
        return len(self.completed_steps) >= self.total_steps


class LearningMode:
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path.home() / ".ai_team" / "learning"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.progress = self._load_progress()
        self.tutorials = self._load_tutorials()
        self.glossary = self._load_glossary()
    
    def _load_progress(self) -> LearningProgress:
        progress_file = self.data_dir / "progress.json"
        if progress_file.exists():
            data = json.loads(progress_file.read_text())
            return LearningProgress(**data)
        return LearningProgress(user_id="default")
    
    def _save_progress(self):
        progress_file = self.data_dir / "progress.json"
        data = {
            "user_id": self.progress.user_id,
            "started_at": self.progress.started_at,
            "completed_steps": self.progress.completed_steps,
            "total_steps": self.progress.total_steps,
            "concepts_learned": self.progress.concepts_learned
        }
        progress_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    def _load_tutorials(self) -> List[TutorialStep]:
        return [
            TutorialStep(1, "Что такое AI-агенты?", "AI-агенты — это программы, которые могут выполнять задачи самостоятельно.", "Подумай о агенте как о цифровом помощнике.", "create_project", "agent_basics"),
            TutorialStep(2, "TeamLead — главный координатор", "TeamLead анализирует твои требования и создаёт план.", "Он как менеджер проекта, только AI.", "run_teamlead", "teamlead_role"),
            TutorialStep(3, "Architect — проектировщик", "Architect выбирает технологии и создаёт структуру.", "Он решает какие библиотеки использовать.", "run_architect", "architect_role"),
            TutorialStep(4, "Backend — серверный код", "Backend пишет API и работает с базой данных.", "Это 'мозг' твоего приложения.", "run_backend", "backend_role"),
            TutorialStep(5, "Frontend — интерфейс", "Frontend создаёт то, что видит пользователь.", "Кнопки, формы, цвета — всё это frontend.", "run_frontend", "frontend_role"),
            TutorialStep(6, "DevOps — инфраструктура", "DevOps настраивает Docker и CI/CD.", "Без него приложение не запустить на сервере.", "run_devops", "devops_role"),
            TutorialStep(7, "Tester — проверка качества", "Tester пишет тесты чтобы код работал правильно.", "Он находит баги до того как они попадут в продакшен.", "run_tester", "testing_basics"),
            TutorialStep(8, "Documentalist — документация", "Documentalist пишет README и API docs.", "Без документации никто не поймёт как использовать код.", "run_documentalist", "documentation"),
            TutorialStep(9, "Параллельная работа", "Несколько агентов могут работать одновременно!", "Backend, Frontend и DevOps работают параллельно.", "run_parallel", "parallelism"),
            TutorialStep(10, "Твой первый проект!", "Теперь ты готов создать свой первый проект!", "Попробуй создать REST API на FastAPI.", "create_first_project", "first_project"),
        ]
    
    def _load_glossary(self) -> List[GlossaryEntry]:
        return [
            GlossaryEntry("Агент", "AI-программа которая выполняет задачи самостоятельно", "TeamLead анализирует требования и создаёт план"),
            GlossaryEntry("Промпт", "Инструкция для AI модели", "Создай REST API с JWT аутентификацией"),
            GlossaryEntry("RAG", "Retrieval Augmented Generation — поиск информации перед генерацией", "Агент ищет похожие проекты перед созданием кода"),
            GlossaryEntry("Fallback", "Переключение на другой провайдер если текущий не работает", "Ollama не отвечает → переключение на Groq"),
            GlossaryEntry("Tool Calling", "Вызов инструментов агентом (создание файлов, команды)", "Агент создаёт файл через create_file"),
            GlossaryEntry("Pipeline", "Последовательность фаз разработки", "Planning → Architecture → Development → Testing → Docs"),
            GlossaryEntry("Sandbox", "Безопасная среда для выполнения кода", "Код проверяется перед запуском"),
            GlossaryEntry("Context Window", "Максимальный размер входных данных для модели", "8192 токенов = ~6000 слов"),
            GlossaryEntry("Ollama", "Локальный сервер для запуска AI моделей", "ollama pull qwen3:8b"),
            GlossaryEntry("Docker", "Контейнеризация — упаковка приложения в контейнер", "docker-compose up -d"),
        ]
    
    def get_current_step(self) -> Optional[TutorialStep]:
        """Получить текущий шаг"""
        for step in self.tutorials:
            if step.id not in self.progress.completed_steps:
                return step
        return None
    
    def complete_step(self, step_id: int, concept: str = None):
        """Отметить шаг выполненным"""
        if step_id not in self.progress.completed_steps:
            self.progress.completed_steps.append(step_id)
            if concept:
                self.progress.concepts_learned.append(concept)
            self._save_progress()
    
    def get_next_action(self) -> Dict[str, Any]:
        """Получить следующее действие"""
        step = self.get_current_step()
        if not step:
            return {"status": "complete", "message": "🎉 Ты прошёл все шаги!"}
        
        return {
            "status": "in_progress",
            "step": step.id,
            "title": step.title,
            "description": step.description,
            "hint": step.hint,
            "action": step.action,
            "progress": self.progress.progress_percent
        }
    
    def get_glossary(self) -> List[Dict[str, str]]:
        """Получить глоссарий"""
        return [
            {"term": e.term, "definition": e.definition, "example": e.example}
            for e in self.glossary
        ]
    
    def search_glossary(self, query: str) -> List[Dict[str, str]]:
        """Поиск в глоссарии"""
        query_lower = query.lower()
        return [
            {"term": e.term, "definition": e.definition, "example": e.example}
            for e in self.glossary
            if query_lower in e.term.lower() or query_lower in e.definition.lower()
        ]
    
    def get_progress_report(self) -> Dict[str, Any]:
        """Отчёт о прогрессе"""
        return {
            "completed": len(self.progress.completed_steps),
            "total": self.progress.total_steps,
            "percent": round(self.progress.progress_percent, 1),
            "concepts": self.progress.concepts_learned,
            "is_complete": self.progress.is_complete
        }
