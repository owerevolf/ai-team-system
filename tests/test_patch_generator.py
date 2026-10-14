"""
Тесты генератора правок (WP6, шаг 1).

Проверяют главное свойство: правка от модели применяется только тогда, когда она
проверяема — старый фрагмент найден в файле ровно один раз.
"""

import json

from core.project_manager.runtime.developer.patch_generator import generate_changes

FILES = {"core/demo.py": "def add(a, b):\n    return a - b\n"}


def _answer(changes):
    return json.dumps({"changes": changes}, ensure_ascii=False)


def test_valid_change_is_applied_to_content():
    result = generate_changes(
        "исправь вычитание на сложение",
        FILES,
        lambda prompt: _answer([{"path": "core/demo.py", "find": "return a - b", "replace": "return a + b"}]),
    )

    assert result.ok
    change = result.changes[0]
    assert "return a + b" in change.new_content
    assert change.old_content != change.new_content


def test_fragment_missing_is_rejected():
    result = generate_changes(
        "задача",
        FILES,
        lambda prompt: _answer([{"path": "core/demo.py", "find": "такого текста нет", "replace": "x"}]),
    )

    assert not result.changes
    assert "встречается 0 раз" in result.errors[0]


def test_ambiguous_fragment_is_rejected():
    files = {"a.py": "x = 1\nx = 1\n"}
    result = generate_changes(
        "задача",
        files,
        lambda prompt: _answer([{"path": "a.py", "find": "x = 1", "replace": "x = 2"}]),
    )

    assert not result.changes
    assert "2 раз" in result.errors[0]


def test_path_outside_context_is_rejected():
    result = generate_changes(
        "задача",
        FILES,
        lambda prompt: _answer([{"path": "секреты.txt", "find": "a", "replace": "b"}]),
    )

    assert not result.changes
    assert "нет в контексте" in result.errors[0]


def test_non_json_answer_is_reported_honestly():
    result = generate_changes("задача", FILES, lambda prompt: "просто текст без json")

    assert not result.changes
    assert "не JSON" in result.errors[0]


def test_model_failure_is_reported_honestly():
    def broken(prompt):
        raise RuntimeError("нет модели")

    result = generate_changes("задача", FILES, broken)

    assert not result.changes
    assert "модель недоступна" in result.errors[0]
