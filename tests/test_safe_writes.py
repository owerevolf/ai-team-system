"""
Тесты безопасной записи файлов (шаг 0.3).

До этой правки путь от модели подставлялся в project_path без проверок:
`..` уводил запись за пределы проекта, а существующий файл затирался молча.
Здесь же проверяется `set_project_path` — метод, который вызывался из
`web_ui/app.py` и `core/main.py`, но не был определён, из-за чего кнопка
«Создать проект» падала с AttributeError.
"""

from unittest.mock import Mock, patch

import pytest

from core.agent_manager import AgentManager


@pytest.fixture()
def manager(tmp_path):
    """AgentManager с папкой проекта; модель и база для записи файлов не нужны."""
    with patch("core.agent_manager.Database"):
        mgr = AgentManager(Mock())
    mgr.set_project_path(tmp_path)
    return mgr


class TestProjectPath:
    def test_set_project_path_stores_resolved_path(self, manager, tmp_path):
        assert manager.project_path == tmp_path.resolve()

    def test_set_project_path_has_no_attribute_error(self, tmp_path):
        """Регрессия: метод вызывался из роута, но не существовал."""
        with patch("core.agent_manager.Database"):
            mgr = AgentManager(Mock())
        assert hasattr(mgr, "set_project_path")
        mgr.set_project_path(tmp_path)
        assert mgr.project_path == tmp_path.resolve()


class TestPathContainment:
    def test_relative_path_inside_project(self, manager, tmp_path):
        result = manager._create_file({"path": "src/app/main.py", "content": "print('ok')\n"})
        assert result["success"] is True
        assert (tmp_path / "src" / "app" / "main.py").read_text(encoding="utf-8") == "print('ok')\n"

    def test_dotdot_path_rejected(self, manager, tmp_path):
        result = manager._create_file({"path": "../escape.txt", "content": "x"})
        assert result["success"] is False
        assert "escapes project root" in result["error"]
        assert not (tmp_path.parent / "escape.txt").exists()

    def test_absolute_path_rejected(self, manager, tmp_path):
        target = tmp_path.parent / "absolute_escape.txt"
        result = manager._create_file({"path": str(target), "content": "x"})
        assert result["success"] is False
        assert not target.exists()

    def test_empty_path_rejected(self, manager):
        result = manager._create_file({"path": "   ", "content": "x"})
        assert result["success"] is False
        assert "path is empty" in result["error"]


class TestOverwriteProtection:
    def test_existing_file_not_overwritten_without_flag(self, manager, tmp_path):
        first = manager._create_file({"path": "README.md", "content": "версия 1"})
        assert first["success"] is True

        second = manager._create_file({"path": "README.md", "content": "версия 2"})
        assert second["success"] is False
        assert "overwrite" in second["error"]
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == "версия 1"

    def test_overwrite_with_flag_creates_backup(self, manager, tmp_path):
        manager._create_file({"path": "README.md", "content": "версия 1"})
        result = manager._create_file({
            "path": "README.md",
            "content": "версия 2",
            "overwrite": True,
        })

        assert result["success"] is True
        assert result.get("backup")
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == "версия 2"

        backup_file = tmp_path / result["backup"]
        assert backup_file.exists()
        assert backup_file.read_text(encoding="utf-8") == "версия 1"

    def test_writes_are_journalled(self, manager, tmp_path):
        manager._create_file({"path": "app.py", "content": "x = 1\n"})
        log = tmp_path / ".ai-team" / "writes.log"
        assert log.exists()

        last_line = log.read_text(encoding="utf-8").strip().splitlines()[-1]
        assert "app.py" in last_line
        assert '"bytes"' in last_line
