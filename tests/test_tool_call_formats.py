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


def test_bare_json_without_wrapper_is_recognised():
    manager = make_manager()
    response = '{"tool": "create_file", "path": "bare.py", "content": "print(3)"}'
    assert manager._extract_and_create_files(response) == ["bare.py"]


def test_garbage_returns_nothing_instead_of_raising():
    assert AgentManager._parse_tool_call("просто текст без вызова") is None


def test_file_blocks_are_created_without_json():
    """Модель пишет файлы заголовком и кодом — это должно становиться файлами."""
    manager = make_manager()
    manager.project_path = None
    captured = []
    manager._create_file = lambda params: captured.append(params) or {
        "success": True, "path": params["path"]
    }

    response = (
        "Короткое объяснение.\n\n"
        "=== FILE: calculator.py ===\n```python\ndef add(a, b):\n    return a + b\n```\n\n"
        "=== FILE: src/history.py ===\n```python\ndef save(x):\n    return x\n```\n"
    )

    assert manager._extract_and_create_files(response) == ["calculator.py", "src/history.py"]
    assert captured[0]["content"].startswith("def add")


def test_pending_proposal_counts_as_created():
    """Правка в очереди подтверждений — это созданный файл, а не провал."""
    manager = make_manager()
    manager.project_path = None
    manager._create_file = lambda params: {
        "success": False, "pending": True, "path": params["path"]
    }

    response = "=== FILE: main.py ===\n```python\nprint(1)\n```\n"

    assert manager._extract_and_create_files(response) == ["main.py"]


def test_description_without_code_is_not_a_file():
    """Чертёж с деревом папок — объяснение, а не файлы."""
    manager = make_manager()
    manager.project_path = None
    manager._create_file = lambda params: {"success": True, "path": params["path"]}

    response = (
        "### Сначала — общая картина:\n"
        "```\n📁 проект\n├── 📄 calculator.py\n└── 📄 history.txt\n```\n"
        "**📄 calculator.py**\nСодержит функции add и subtract.\n"
    )

    assert manager._extract_and_create_files(response) == []


def test_broken_python_block_is_rejected():
    manager = make_manager()
    manager.project_path = None
    captured = []
    manager._create_file = lambda params: captured.append(params) or {
        "success": True, "path": params["path"]
    }

    response = "=== FILE: broken.py ===\n```python\ndef broken(:\n    pass\n```\n"

    assert manager._extract_and_create_files(response) == []
    assert captured == []
