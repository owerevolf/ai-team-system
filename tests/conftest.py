"""Общие настройки тестов.

Очередь подтверждений по умолчанию живёт в `.cache/approvals.json` проекта.
В тестах её надо уводить в tmp: иначе один тест видит заявки другого, и проверки
вида «ожидали одну заявку» падают на «получили семь» — при этом настоящая очередь
разработчика засоряется тестовыми записями.
"""

import pytest

from core.project_manager.runtime.developer.approval_runtime import ApprovalRuntime


@pytest.fixture(autouse=True)
def _isolated_approvals(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ApprovalRuntime,
        "_state_path",
        lambda self: tmp_path / "approvals.json",
    )
