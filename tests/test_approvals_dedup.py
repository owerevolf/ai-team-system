"""Очередь подтверждений: один путь — одна заявка, замена не теряется молча.

Раньше сравнивались только имена файлов: `frontend/style.css` исчезал из очереди,
когда DevOps приносил свой `style.css`, — и человек об этом не узнавал.
"""

import json
from pathlib import Path

import pytest

from core.project_manager.runtime.developer.approval_runtime import (
    ApprovalRequest,
    ApprovalRuntime,
)


@pytest.fixture()
def runtime(tmp_path: Path, monkeypatch) -> ApprovalRuntime:
    monkeypatch.setattr(ApprovalRuntime, "_state_path", lambda self: tmp_path / "approvals.json")
    return ApprovalRuntime()


def _propose(runtime: ApprovalRuntime, agent: str, path: str, content: str = "x") -> ApprovalRequest:
    return runtime.create_request(
        patch_id="p",
        task_id="t",
        agent_id=agent,
        summary=f"{agent}: {Path(path).name}",
        risk_level="medium",
        files_changed=[path],
        files_content={path: content},
    )


def test_same_basename_in_different_folders_both_stay(runtime: ApprovalRuntime) -> None:
    _propose(runtime, "frontend", "C:/proj/style.css")
    _propose(runtime, "devops", "C:/proj/deploy/style.css")

    assert runtime.get_queue_size() == 2


def test_same_path_replaces_and_keeps_the_old_version(runtime: ApprovalRuntime) -> None:
    first = _propose(runtime, "frontend", "C:/proj/style.css", "body{color:red}")
    second = _propose(runtime, "devops", "C:/proj/style.css", "body{color:blue}")

    assert runtime.get_queue_size() == 1
    assert second.note == "заменяет версию: frontend"

    history = runtime.get_history()
    assert any(
        item.request_id == first.request_id and item.status == "superseded"
        for item in history
    ), "заменённая версия должна остаться в истории"
    assert runtime.get_pending()[0].request_id == second.request_id


def test_different_slashes_are_the_same_path(runtime: ApprovalRuntime) -> None:
    _propose(runtime, "backend", "C:\\proj\\main.py")
    _propose(runtime, "backend", "C:/proj/main.py")

    assert runtime.get_queue_size() == 1


def test_history_survives_restart(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ApprovalRuntime, "_state_path", lambda self: tmp_path / "approvals.json")
    runtime = ApprovalRuntime()
    _propose(runtime, "frontend", "C:/proj/style.css")
    _propose(runtime, "devops", "C:/proj/style.css")
    runtime.save_state()

    restarted = ApprovalRuntime()

    assert restarted.get_queue_size() == 1
    assert any(item.status == "superseded" for item in restarted.get_history())


def test_old_list_format_still_loads(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "approvals.json"
    old = ApprovalRequest(
        patch_id="p", task_id="t", agent_id="backend", summary="old",
        files_changed=["C:/proj/main.py"], files_content={"C:/proj/main.py": "print(1)"},
    )
    state.write_text(json.dumps([old.__dict__], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(ApprovalRuntime, "_state_path", lambda self: state)

    runtime = ApprovalRuntime()

    assert runtime.get_queue_size() == 1
    assert runtime.get_pending()[0].summary == "old"
