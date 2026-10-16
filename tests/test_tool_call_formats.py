"""Вызовы инструментов должны распознаваться в обеих формах скобок.

Живые прогоны показали: модель отдаёт вызов в обычных угловых скобках,
а код искал только широкие (U+FF1C/U+FF1E) — и готовые вызовы молча пропадали.
"""

from unittest.mock import Mock, patch

from core.agent_manager import AgentManager


class FakeTool:
    """Подставной инструмент: ничего не пишет, только сообщает, что вызов дошёл."""

    @staticmethod
    def handler(data):
        return {"success": True, "path": data.get("path", "?")}


def make_manager() -> AgentManager:
    with patch("core.agent_manager.Database"):
        manager = AgentManager(Mock())
    manager.tools = {"create_file": FakeTool()}
    return manager


def test_ascii_wrapper_is_recognised():
    manager = make_manager()
    response = '<tool_call>\n{"tool": "create_file", "path": "main.py", "content": "print(1)"}\n</tool_call>'
    assert manager._extract_and_create_files(response) == ["main.py"]


def test_wide_wrapper_is_recognised():
    manager = make_manager()
    response = (
        "\uff1ctool_call\uff1e\n"
        '{"tool": "create_file", "path": "wide.py", "content": "print(2)"}'
        "\n\uff1c/tool_call\uff1e"
    )
    assert manager._extract_and_create_files(response) == ["wide.py"]


def test_unescaped_quotes_inside_code_are_recovered():
    broken = '{"tool": "create_file", "path": "q.py", "content": "print("привет")"}'
    parsed = AgentManager._parse_tool_call(broken)
    assert parsed["path"] == "q.py"
    assert "привет" in parsed["content"]


def test_garbage_returns_nothing_instead_of_raising():
    assert AgentManager._parse_tool_call("просто текст без вызова") is None
