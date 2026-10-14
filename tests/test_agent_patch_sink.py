"""
Тест точки подключения патчей в записи файлов (WP6, шаг 4).

Если агентскому менеджеру подключили «сток» патчей, запись на диск не происходит:
изменение уходит на подтверждение. Без стока поведение прежнее — прямое сохранение.
"""

from unittest.mock import Mock, patch

from core.agent_manager import AgentManager


def _manager(tmp_path):
    with patch("core.agent_manager.Database"):
        manager = AgentManager(Mock())
    manager.set_project_path(tmp_path)
    return manager


def test_write_is_routed_to_patch_sink(tmp_path):
    manager = _manager(tmp_path)
    routed = []

    def sink(file_path, content):
        routed.append((file_path.name, content))
        return True

    manager._patch_sink = sink
    result = manager._create_file({"path": "новый.py", "content": "print('привет')\n"})

    assert result.get("pending") is True
    assert result["success"] is False
    assert routed == [("новый.py", "print('привет')\n")]
    assert not (tmp_path / "новый.py").exists(), "файл не должен появиться без подтверждения"


def test_write_stays_direct_without_sink(tmp_path):
    manager = _manager(tmp_path)
    result = manager._create_file({"path": "обычный.py", "content": "x = 1\n"})

    assert result["success"] is True
    assert (tmp_path / "обычный.py").read_text(encoding="utf-8") == "x = 1\n"
