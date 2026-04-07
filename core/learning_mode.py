"""
Learning Mode — режим обучения для новичков (5 шагов)
Версия: 2.0
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path.home() / ".ai_team" / "learning"


@dataclass
class TutorialStep:
    id: int
    title: str
    description: str
    visual: str
    hint: str
    action: str
    beginner_analogy: str = ""


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
    total_steps: int = 5
    concepts_learned: List[str] = field(default_factory=list)

    @property
    def progress_percent(self) -> float:
        return (len(self.completed_steps) / self.total_steps) * 100 if self.total_steps > 0 else 0

    @property
    def is_complete(self) -> bool:
        return len(self.completed_steps) >= self.total_steps


class LearningMode:
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir or DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.progress = self._load_progress()
        self.tutorials = self._build_tutorials()
        self.glossary = self._build_glossary()

    def _load_progress(self) -> LearningProgress:
        progress_file = self.data_dir / "progress.json"
        if progress_file.exists():
            try:
                data = json.loads(progress_file.read_text())
                return LearningProgress(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return LearningProgress(user_id="default")

    def _save_progress(self) -> None:
        progress_file = self.data_dir / "progress.json"
        data = {
            "user_id": self.progress.user_id,
            "started_at": self.progress.started_at,
            "completed_steps": self.progress.completed_steps,
            "total_steps": self.progress.total_steps,
            "concepts_learned": self.progress.concepts_learned,
        }
        progress_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _build_tutorials(self) -> List[TutorialStep]:
        return [
            TutorialStep(
                id=1,
                title="Что такое AI-агенты?",
                description="AI-агенты — это программы, которые выполняют задачи самостоятельно. В AI Team System их 7, и каждый специализируется на своём.",
                visual="🤖 × 7",
                hint="Подумай об агенте как о цифровом помощнике с конкретной ролью.",
                action="intro",
                beginner_analogy="Как в ресторане: повар готовит, официант подаёт, бармен делает напитки. Каждый делает своё дело.",
            ),
            TutorialStep(
                id=2,
                title="TeamLead и Architect — планирование",
                description="TeamLead разбирает твою задачу на части, Architect выбирает технологии и проектирует структуру проекта.",
                visual="👑 → 🏗️",
                hint="Сначала план, потом код. Без плана — хаос.",
                action="planning",
                beginner_analogy="Архитектор рисует чертёж дома, прораб (TeamLead) решает кто и когда будет строить.",
            ),
            TutorialStep(
                id=3,
                title="Разработка — Backend, Frontend, DevOps",
                description="Три агента работают параллельно: Backend — сервер и API, Frontend — интерфейс, DevOps — Docker и настройка сервера.",
                visual="⚙️ 🎨 🚀",
                hint="Параллельная работа ускоряет разработку в 3 раза.",
                action="development",
                beginner_analogy="Как на стройке: электрик, сантехник и отделочник работают одновременно в разных комнатах.",
            ),
            TutorialStep(
                id=4,
                title="Тестирование и документация",
                description="Tester проверяет что код работает правильно. Documentalist пишет README и инструкции. Без этого проект неполноценный.",
                visual="🧪 ✅ 📝",
                hint="Хороший код без тестов — как мост без проверки прочности.",
                action="testing",
                beginner_analogy="Tester — как контролёр в метро: проверяет что всё в порядке. Documentalist — как инструкция к прибору.",
            ),
            TutorialStep(
                id=5,
                title="Результат — готовый проект!",
                description="Все агенты завершили работу. Ты получаешь готовый проект с кодом, тестами, документацией и Markdown-урок с объяснениями.",
                visual="🎉 📦 ✨",
                hint="Каждый урок сохраняется. Возвращайся к нему когда угодно.",
                action="complete",
                beginner_analogy="Как получить ключи от новой квартиры: всё готово, осталось заселиться!",
            ),
        ]

    def _build_glossary(self) -> List[GlossaryEntry]:
        return [
            GlossaryEntry("Агент", "AI-программа, которая выполняет задачи самостоятельно", "TeamLead анализирует требования и создаёт план"),
            GlossaryEntry("Промпт", "Инструкция для AI модели", "Создай REST API с JWT аутентификацией"),
            GlossaryEntry("RAG", "Retrieval Augmented Generation — поиск информации перед генерацией ответа", "Агент ищет похожие проекты перед созданием кода"),
            GlossaryEntry("Fallback", "Переключение на другой провайдер если текущий не работает", "Ollama не отвечает → переключение на Groq"),
            GlossaryEntry("Pipeline", "Последовательность фаз разработки", "Planning → Architecture → Development → Testing → Docs"),
            GlossaryEntry("Sandbox", "Безопасная среда для выполнения кода", "Код проверяется перед запуском"),
            GlossaryEntry("Ollama", "Локальный сервер для запуска AI моделей", "ollama pull qwen3:8b"),
            GlossaryEntry("Docker", "Контейнеризация — упаковка приложения в контейнер", "docker-compose up -d"),
        ]

    def get_step(self, step_id: int, beginner_mode: bool = False) -> Dict[str, Any]:
        step = None
        for s in self.tutorials:
            if s.id == step_id:
                step = s
                break

        if not step:
            return {"error": "Шаг не найден", "step_id": step_id}

        if beginner_mode:
            prompt = (
                f"РЕЖИМ НОВИЧКА: Объясни простыми словами, как будто говоришь с человеком без опыта программирования.\n"
                f"Тема: {step.title}\n"
                f"Описание: {step.description}\n"
                f"Аналогия: {step.beginner_analogy}\n"
                f"Подсказка: {step.hint}"
            )
        else:
            prompt = (
                f"СТАНДАРТНЫЙ РЕЖИМ: {step.title}\n"
                f"{step.description}\n"
                f"Подсказка: {step.hint}"
            )

        result: Dict[str, Any] = {
            "step": step.id,
            "title": step.title,
            "description": step.description,
            "visual": step.visual,
            "hint": step.hint,
            "action": step.action,
            "prompt": prompt,
            "progress": self.progress.progress_percent,
        }

        if beginner_mode and step.beginner_analogy:
            result["analogy"] = step.beginner_analogy

        return result

    def complete_step(self, step_id: int, concept: Optional[str] = None) -> Dict[str, Any]:
        if step_id not in self.progress.completed_steps:
            self.progress.completed_steps.append(step_id)
            if concept and concept not in self.progress.concepts_learned:
                self.progress.concepts_learned.append(concept)
            self._save_progress()
            logger.info(f"Шаг {step_id} завершён. Прогресс: {self.progress.progress_percent:.0f}%")

        return {
            "completed": step_id,
            "progress": self.progress.progress_percent,
            "is_complete": self.progress.is_complete,
        }

    def reset_progress(self) -> None:
        self.progress.completed_steps = []
        self.progress.concepts_learned = []
        self._save_progress()
        logger.info("Прогресс обучения сброшен")

    def get_current_step(self) -> Optional[TutorialStep]:
        for step in self.tutorials:
            if step.id not in self.progress.completed_steps:
                return step
        return None

    def get_next_action(self) -> Dict[str, Any]:
        step = self.get_current_step()
        if not step:
            return {"status": "complete", "message": "Все шаги пройдены!"}
        return {
            "status": "in_progress",
            "step": step.id,
            "title": step.title,
            "action": step.action,
        }

    def get_glossary(self) -> List[Dict[str, str]]:
        return [
            {"term": e.term, "definition": e.definition, "example": e.example}
            for e in self.glossary
        ]

    def search_glossary(self, query: str) -> List[Dict[str, str]]:
        query_lower = query.lower()
        return [
            {"term": e.term, "definition": e.definition, "example": e.example}
            for e in self.glossary
            if query_lower in e.term.lower() or query_lower in e.definition.lower()
        ]

    def get_progress_report(self) -> Dict[str, Any]:
        return {
            "completed": len(self.progress.completed_steps),
            "total": self.progress.total_steps,
            "percent": round(self.progress.progress_percent, 1),
            "concepts": self.progress.concepts_learned,
            "is_complete": self.progress.is_complete,
            "started_at": self.progress.started_at,
        }

    def generate_agent_prompt(
        self,
        agent_role: str,
        task: str,
        beginner_mode: bool = False,
    ) -> str:
        system_prompt = f"Ты — AI-агент '{agent_role}' в команде AI Team System.\n\n"

        if beginner_mode:
            system_prompt += """РЕЖИМ НОВИЧКА (ОБЯЗАТЕЛЬНО СЛЕДОВАТЬ):
1. Пиши простым языком, объясняй термины при первом использовании
2. Объясняй "почему так", а не только "как"
3. Ссылайся только на официальную документацию (MDN, docs.python.org и т.д.)
4. НЕ выдумывай несуществующие библиотеки или функции
5. Приводи конкретные примеры кода с комментариями к каждой строке
6. Разбивай сложные концепции на простые шаги
7. Аналогии из жизни — только если они реально помогают понять концепцию, не более 1 на раздел. НЕ используй аналогии для очевидных вещей.
8. Стиль ответа: сначала краткий ответ, потом объяснение, потом пример кода

"""

        system_prompt += f"Задача: {task}\n\n"
        system_prompt += "Ответь структурированно, с примерами кода если уместно."

        return system_prompt
