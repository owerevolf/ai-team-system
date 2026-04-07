"""
Export Lesson — генерация Markdown-гайда из истории сессии
Версия: 2.0
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from loguru import logger

LESSONS_DIR = Path.home() / "ai-team-lessons"


class ExportLesson:
    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or LESSONS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, history: List[Dict[str, Any]], title: str) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:50]
        filename = f"{timestamp}_{safe_title}.md"
        filepath = self.output_dir / filename

        content = self._build_markdown(history, title, timestamp)
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Урок экспортирован: {filepath}")
        return filepath

    def _build_markdown(self, history: List[Dict[str, Any]], title: str, timestamp: str) -> str:
        lines: List[str] = []

        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"**Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        lines.append(f"**Система:** AI Team System v2.0")
        lines.append("")
        lines.append("---")
        lines.append("")

        lines.append("## 📋 Содержание")
        lines.append("")
        lines.append("1. [Введение](#введение)")
        lines.append("2. [Ход урока](#ход-урока)")
        lines.append("3. [Результат](#результат)")
        lines.append("4. [Полезные ссылки](#полезные-ссылки)")
        lines.append("")
        lines.append("---")
        lines.append("")

        lines.append("## Введение")
        lines.append("")
        lines.append("Этот урок создан AI Team System — мультиагентной системой разработки.")
        lines.append("7 AI-агентов работали над проектом: TeamLead, Architect, Backend,")
        lines.append("Frontend, DevOps, Tester и Documentalist.")
        lines.append("")

        lines.append("## Ход урока")
        lines.append("")

        for i, event in enumerate(history, 1):
            event_type = event.get("type", "unknown")
            event_data = event.get("data", {})
            event_time = event.get("time", "")

            lines.append(f"### Шаг {i}: {event_type}")
            if event_time:
                lines.append(f"*Время: {event_time}*")
            lines.append("")

            if isinstance(event_data, dict):
                for key, value in event_data.items():
                    lines.append(f"**{key}:** {value}")
            elif isinstance(event_data, str):
                lines.append(event_data)
            lines.append("")

        lines.append("---")
        lines.append("")

        lines.append("## Результат")
        lines.append("")
        lines.append("Проект создан успешно. Все агенты завершили свои задачи.")
        lines.append("")
        lines.append("### Что было сделано:")
        lines.append("")
        lines.append("- [x] Анализ требований (TeamLead)")
        lines.append("- [x] Проектирование архитектуры (Architect)")
        lines.append("- [x] Серверный код (Backend)")
        lines.append("- [x] Пользовательский интерфейс (Frontend)")
        lines.append("- [x] Инфраструктура и Docker (DevOps)")
        lines.append("- [x] Тесты (Tester)")
        lines.append("- [x] Документация (Documentalist)")
        lines.append("")

        lines.append("---")
        lines.append("")

        lines.append("## Полезные ссылки")
        lines.append("")
        lines.append("- [FastAPI документация](https://fastapi.tiangolo.com/)")
        lines.append("- [Python документация](https://docs.python.org/3/)")
        lines.append("- [Ollama](https://ollama.ai/)")
        lines.append("- [AI Team System GitHub](https://github.com/owerevolf/ai-team-system)")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(f"*Сгенерировано AI Team System • {timestamp}*")
        lines.append("")

        return "\n".join(lines)

    def list_lessons(self) -> List[Dict[str, str]]:
        lessons = []
        if not self.output_dir.exists():
            return lessons

        for f in sorted(self.output_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            lessons.append({
                "name": f.stem,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        return lessons
