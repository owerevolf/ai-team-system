"""
Тест подключения генератора правок в исполнение (WP6, шаг 1b).

Проверяет два режима:
* с вызовом модели — патч несёт НАСТОЯЩУЮ правку (содержимое файла изменилось);
* без модели — работает прежний мок (содержимое неизменно), поток не ломается.
"""

import json

from core.project_manager.runtime.developer.task_executor import TaskExecutor

FILE = "core/demo.py"
CONTENT = "def add(a, b):\n    return a - b\n"


class FakeSandbox:
    def read_file(self, path):
        return type("ReadResult", (), {"success": True, "output": CONTENT})()


class FakePatches:
    def __init__(self):
        self.file_changes = None

    def generate_patch(self, task_id, file_changes, created_by, summary):
        self.file_changes = file_changes
        return type("Patch", (), {"patch_id": "p1", "file_changes": file_changes})()


def _contract():
    return type("Contract", (), {
        "task_id": "t1",
        "allowed_files": [FILE],
        "owner_agent": "backend",
        "title": "исправить вычитание",
    })()


def _executor():
    executor = TaskExecutor.__new__(TaskExecutor)
    executor._sandbox = FakeSandbox()
    executor._patches = FakePatches()
    return executor


def test_patch_contains_real_change_when_model_is_available():
    executor = _executor()
    executor._model_call = lambda prompt: json.dumps({
        "changes": [{"path": FILE, "find": "return a - b", "replace": "return a + b"}]
    })

    patch = executor._generate_patch(_contract(), "контекст задачи", None)

    assert patch.file_changes[FILE] != CONTENT
    assert "return a + b" in patch.file_changes[FILE]


def test_mock_path_keeps_content_untouched_without_model():
    executor = _executor()

    patch = executor._generate_patch(_contract(), "контекст задачи", None)

    assert patch.file_changes[FILE] == CONTENT


def test_unverifiable_model_answer_falls_back_to_mock():
    executor = _executor()
    executor._model_call = lambda prompt: json.dumps({
        "changes": [{"path": FILE, "find": "такого фрагмента нет", "replace": "x"}]
    })

    patch = executor._generate_patch(_contract(), "контекст задачи", None)

    assert patch.file_changes[FILE] == CONTENT
