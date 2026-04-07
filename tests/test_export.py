"""
Тесты ExportLesson
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.export_lesson import ExportLesson


class TestExportLesson:
    def test_generate_creates_file(self, tmp_path: Path) -> None:
        exporter = ExportLesson(output_dir=tmp_path)
        history = [
            {"type": "step", "data": {"title": "Тест"}, "time": "2024-01-01T00:00:00"},
            {"type": "complete", "data": {}, "time": "2024-01-01T00:01:00"},
        ]

        filepath = exporter.generate(history, "Тестовый урок")

        assert filepath.exists()
        assert filepath.suffix == ".md"
        content = filepath.read_text(encoding="utf-8")
        assert "Тестовый урок" in content
        assert "AI Team System" in content

    def test_generate_valid_markdown(self, tmp_path: Path) -> None:
        exporter = ExportLesson(output_dir=tmp_path)
        history = [
            {"type": "intro", "data": {"info": "Введение"}, "time": "2024-01-01T00:00:00"},
        ]

        filepath = exporter.generate(history, "Markdown тест")
        content = filepath.read_text(encoding="utf-8")

        assert content.startswith("# Markdown тест")
        assert "Содержание" in content
        assert "## Ход урока" in content
        assert "## Результат" in content
        assert "## Полезные ссылки" in content

    def test_generate_with_empty_history(self, tmp_path: Path) -> None:
        exporter = ExportLesson(output_dir=tmp_path)
        filepath = exporter.generate([], "Пустой урок")

        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        assert "Пустой урок" in content

    def test_list_lessons(self, tmp_path: Path) -> None:
        exporter = ExportLesson(output_dir=tmp_path)
        history = [{"type": "test", "data": {}, "time": "2024-01-01T00:00:00"}]

        exporter.generate(history, "Урок 1")
        exporter.generate(history, "Урок 2")

        lessons = exporter.list_lessons()
        assert len(lessons) == 2
        assert lessons[0]["size_kb"] > 0
        assert "created" in lessons[0]

    def test_list_lessons_empty_dir(self, tmp_path: Path) -> None:
        exporter = ExportLesson(output_dir=tmp_path)
        lessons = exporter.list_lessons()
        assert lessons == []
