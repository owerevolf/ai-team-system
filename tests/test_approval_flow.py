"""
Тест потока подтверждения (WP6, шаг 2).

Проверяет главное: одобренный человеком патч получает флаг `approved` до применения.
Раньше флага не выставлял никто, поэтому `patch_engine.apply_patch` отказывался
применять изменения — то есть подтверждённый патч не применялся никогда.

Объект создаётся через `__new__` без конструктора: тесту нужны только два поля,
и это дешевле, чем тянуть движок патчей целиком.
"""

from core.project_manager.runtime.developer.task_executor import TaskExecutor


class _FakeApproval:
    def approve(self, request_id):
        return type("Request", (), {"patch_id": "p1"})()


class _FakePatches:
    def __init__(self):
        self.seen_approved = None

    def get_patch(self, patch_id):
        return type("Patch", (), {"approved": False})()

    def apply_patch(self, patch):
        self.seen_approved = patch.approved
        return True


def test_approve_patch_sets_approved_flag_before_applying():
    executor = TaskExecutor.__new__(TaskExecutor)
    executor._approval = _FakeApproval()
    executor._patches = _FakePatches()

    assert executor.approve_patch("req1") is True
    assert executor._patches.seen_approved is True


def test_approve_patch_reports_unknown_request():
    executor = TaskExecutor.__new__(TaskExecutor)

    class NoSuchRequest:
        def approve(self, request_id):
            return None

    executor._approval = NoSuchRequest()
    executor._patches = _FakePatches()

    assert executor.approve_patch("missing") is False
