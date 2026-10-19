"""Роль отвечает за свою часть работы: чужие файлы не создаются.

Живой прогон показал, как DevOps приносил `style.css` и затирал версию Frontend,
а Тестер — `README.md`. Теперь такой файл отклоняется с объяснением.
"""

from unittest.mock import Mock, patch

from core.agent_manager import AgentManager


def make_manager(tmp_path, agent: str) -> AgentManager:
    with patch("core.agent_manager.Database"):
        manager = AgentManager(Mock())
    manager.set_project_path(tmp_path)
    manager._current_agent = agent
    return manager


def test_frontend_cannot_write_backend_file(tmp_path):
    manager = make_manager(tmp_path, "frontend")

    result = manager._create_file({"path": "app.py", "content": "print(1)"})

    assert result["success"] is False
    assert "не пишет" in result["error"]
    assert not (tmp_path / "app.py").exists()


def test_devops_cannot_write_styles(tmp_path):
    manager = make_manager(tmp_path, "devops")

    result = manager._create_file({"path": "style.css", "content": "body{}"})

    assert result["success"] is False
    assert not (tmp_path / "style.css").exists()


def test_frontend_writes_its_own_files(tmp_path):
    manager = make_manager(tmp_path, "frontend")

    result = manager._create_file({"path": "ui/style.css", "content": "body{color:red}"})

    assert result["success"] is True
    assert (tmp_path / "ui" / "style.css").read_text(encoding="utf-8") == "body{color:red}"


def test_common_files_are_allowed_for_any_role(tmp_path):
    manager = make_manager(tmp_path, "tester")

    result = manager._create_file({"path": "requirements.txt", "content": "pytest\n"})

    assert result["success"] is True


def test_unknown_role_is_not_restricted(tmp_path):
    manager = make_manager(tmp_path, "")

    result = manager._create_file({"path": "anything.bin", "content": "x"})

    assert result["success"] is True
