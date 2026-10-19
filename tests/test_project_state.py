"""Источник правды: факты из кода, статус проверки, сверка с диском и срезы.

Правило, которое здесь проверяется: существование и API файла берутся с диска,
а не из слов модели; модель отвечает только за «зачем».
"""

import json
from pathlib import Path

from core import project_state as state


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_records_purpose_author_and_real_api(tmp_path: Path) -> None:
    _write(tmp_path, "calculator.py", "def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n")

    state.record_file(tmp_path, "calculator.py", author="architect", purpose="логика вычислений")
    saved = state.load(tmp_path)

    entry = saved["files"]["calculator.py"]
    assert entry["author"] == "architect"
    assert entry["purpose"] == "логика вычислений"
    assert entry["api"] == ["add(a, b)", "sub(a, b)"]


def test_slice_for_backend_has_its_files_and_errors(tmp_path: Path) -> None:
    _write(tmp_path, "calculator.py", "def add(a, b):\n    return a + b\n")
    state.record_file(tmp_path, "calculator.py", author="architect", purpose="вычисления")
    state.record_check(tmp_path, {
        "ok": False,
        "errors": ["calculator.py — импорт не сходится"],
        "tests": {"ran": True, "passed": 0, "failed": 1},
    })

    block = state.slice_for(tmp_path, "backend")

    assert "calculator.py" in block
    assert "add(a, b)" in block
    assert "правь это" in block


def test_slice_for_tester_shows_functions_and_tests(tmp_path: Path) -> None:
    _write(tmp_path, "calculator.py", "def add(a, b):\n    return a + b\n")
    state.record_file(tmp_path, "calculator.py", author="architect")
    state.record_check(tmp_path, {"ok": False, "errors": ["main.py — нет flask"], "tests": {"ran": True, "passed": 2, "failed": 1}})

    block = state.slice_for(tmp_path, "tester")

    assert "add(a, b)" in block
    assert "2 прошло, 1 упало" in block
    assert "наличие пакетов" in block


def test_deleted_file_disappears_from_state(tmp_path: Path) -> None:
    _write(tmp_path, "old.py", "x = 1\n")
    state.record_file(tmp_path, "old.py", author="backend")
    (tmp_path / "old.py").unlink()

    saved = state.reconcile(tmp_path)

    assert "old.py" not in saved["files"]


def test_new_file_on_disk_appears_in_state(tmp_path: Path) -> None:
    _write(tmp_path, "manual.py", "def run():\n    pass\n")

    saved = state.reconcile(tmp_path)

    assert "manual.py" in saved["files"]
    assert saved["files"]["manual.py"]["api"] == ["run()"]


def test_legacy_truth_is_migrated(tmp_path: Path) -> None:
    _write(tmp_path, "calculator.py", "def add(a, b):\n    return a + b\n")
    (tmp_path / "_truth.json").write_text(json.dumps({
        "files": {"calculator.py": {"author": "architect", "purpose": "вычисления", "at": "2026-10-19T02:03:33"}}
    }), encoding="utf-8")

    saved = state.load(tmp_path)

    assert saved["version"] == state.VERSION
    assert saved["files"]["calculator.py"]["author"] == "architect"
    assert saved["files"]["calculator.py"]["api"] == ["add(a, b)"]
    assert (tmp_path / "_state.json").exists()


def test_slice_is_short(tmp_path: Path) -> None:
    for index in range(40):
        _write(tmp_path, f"file_{index}.py", f"def run_{index}():\n    pass\n")
        state.record_file(tmp_path, f"file_{index}.py", author="backend")

    block = state.slice_for(tmp_path, "architect")

    assert len(block) <= state.SLICE_LIMIT


def test_author_stays_creator_and_update_is_separate(tmp_path: Path) -> None:
    _write(tmp_path, "calculator.py", "def add(a, b):\n    return a + b\n")

    state.record_file(tmp_path, "calculator.py", author="architect", purpose="вычисления")
    state.record_file(tmp_path, "calculator.py", author="backend", purpose="")

    entry = state.load(tmp_path)["files"]["calculator.py"]
    assert entry["author"] == "architect"
    assert entry["updated_by"] == "backend"
    assert entry["purpose"] == "вычисления"


def test_events_journal_is_written(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "x = 1\n")
    state.record_file(tmp_path, "a.py", author="backend")

    lines = (tmp_path / ".ai-team" / "events.jsonl").read_text(encoding="utf-8").splitlines()

    assert any(json.loads(line)["event"] == "file_written" for line in lines)
