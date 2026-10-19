"""Запись файлов в состояние после повторной попытки.

Живой прогон показал: Frontend записал три файла, но в состоянии они появились
без автора — потому что запись шла до повтора, а файлы пришли со второй попытки.
"""

from pathlib import Path

from core import project_state
from core.agent_manager import AgentManager


class RetryRouter:
    """Первая попытка — только слова, вторая — файл."""

    def __init__(self):
        self.calls = 0

    def generate(self, prompt=None, agent=None):
        self.calls += 1
        if self.calls == 1:
            return "Сейчас расскажу, что сделаю, но файлов пока нет."
        return (
            "Калькулятор с историей вычислений.\n\n"
            "=== FILE: calculator.py ===\n"
            "```python\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "```\n"
        )


def test_purpose_skips_code_lines() -> None:
    response = "flask==2.3.2\n<!DOCTYPE html>\nКалькулятор с историей вычислений\n"

    assert AgentManager._purpose_from(response) == "Калькулятор с историей вычислений"


def test_files_from_retry_are_recorded_with_author(tmp_path: Path) -> None:
    manager = AgentManager(RetryRouter())
    manager.set_project_path(tmp_path)

    result = manager.run_agent("backend", "Сделай калькулятор", level="zero")

    assert result["files_created"] == ["calculator.py"]
    saved = project_state.load(tmp_path)
    entry = saved["files"]["calculator.py"]
    assert entry["author"] == "backend"
    assert entry["api"] == ["add(a, b)"]
    assert entry["purpose"] == "Калькулятор с историей вычислений."
