"""
Тест настоящего отката рабочего пространства (WP6, шаг 3).

Раньше `restore_snapshot` только менял состояние: снапшот хранил лишь md5-хэши,
восстанавливать было нечего. Теперь содержимое сохраняется и возвращается,
а файлы, появившиеся после снапшота, убираются.

Объект собирается через `__new__` и лёгкие заглушки: тесту нужны только
`_workspaces` и реальная математика отката.
"""

from pathlib import Path

from core.project_manager.runtime.developer.workspace_runtime import WorkspaceRuntime


class _FakeWorkspace:
    def __init__(self, base_path):
        self.base_path = str(base_path)
        self.snapshots = []
        self.state = "active"


def _runtime(tmp_path):
    runtime = WorkspaceRuntime.__new__(WorkspaceRuntime)
    workspace = _FakeWorkspace(tmp_path)
    runtime._workspaces = {"w1": workspace}
    return runtime, workspace


def test_rollback_restores_content_and_removes_new_files(tmp_path):
    runtime, _ = _runtime(tmp_path)

    (tmp_path / "a.txt").write_text("версия 1", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("тоже первая", encoding="utf-8")

    snapshot = runtime.create_snapshot("w1", "до правок")

    (tmp_path / "a.txt").write_text("версия 2", encoding="utf-8")
    (tmp_path / "sub" / "b.txt").write_text("испорчено", encoding="utf-8")
    (tmp_path / "new.txt").write_text("появился после снапшота", encoding="utf-8")

    assert runtime.restore_snapshot("w1", snapshot.snapshot_id) is True

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "версия 1"
    assert (tmp_path / "sub" / "b.txt").read_text(encoding="utf-8") == "тоже первая"
    assert not (tmp_path / "new.txt").exists()


def test_rollback_marks_state_and_reports_unknown_snapshot(tmp_path):
    runtime, workspace = _runtime(tmp_path)

    (tmp_path / "a.txt").write_text("данные", encoding="utf-8")
    snapshot = runtime.create_snapshot("w1")

    assert runtime.restore_snapshot("w1", snapshot.snapshot_id) is True
    assert workspace.state == "rolled_back"
    assert runtime.restore_snapshot("w1", "нет-такого") is False
    assert runtime.restore_snapshot("нет-такого", snapshot.snapshot_id) is False
