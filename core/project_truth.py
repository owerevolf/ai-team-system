"""Источник правды проекта: что уже есть, кто сделал и зачем.

Зачем: агенты работают по очереди и не видят друг друга. Маленькая модель без
состояния проекта каждый раз придумывает заново — отсюда восемь разных calculator.py.
Здесь хранится одна короткая запись на проект, которая подмешивается в промпт каждому
агенту: список файлов, их назначение и автор.

Правило: писать сюда может только тот, кто действительно создал файл. Запись —
факт, а не намерение.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

STATE_NAME = "_truth.json"


def _state_path(project_path: Path) -> Path:
    return Path(project_path) / STATE_NAME


def load(project_path: Optional[Path]) -> Dict:
    """Загружает состояние проекта. Нет файла или он испорчен — пустое состояние."""
    if not project_path:
        return {"files": {}, "updated": ""}
    path = _state_path(project_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — отсутствие файла это нормальное начало работы
        return {"files": {}, "updated": ""}
    if not isinstance(data, dict):
        return {"files": {}, "updated": ""}
    data.setdefault("files", {})
    return data


def save(project_path: Optional[Path], state: Dict) -> bool:
    """Сохраняет состояние. Не смогли — возвращаем ложь, но не ломаем работу агента."""
    if not project_path:
        return False
    try:
        state["updated"] = datetime.now().isoformat(timespec="seconds")
        _state_path(project_path).write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def record_file(project_path: Optional[Path], name: str, author: str = "", purpose: str = "") -> bool:
    """Записывает факт: файл создан таким-то агентом."""
    state = load(project_path)
    state["files"][name] = {
        "author": author,
        "purpose": purpose[:300],
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    return save(project_path, state)


def existing_files(project_path: Optional[Path]) -> List[str]:
    return sorted(load(project_path).get("files", {}).keys())


def as_prompt_block(project_path: Optional[Path]) -> str:
    """Короткая справка для промпта: что уже существует в проекте.

    Именно короткая: у маленькой модели каждый лишний абзац отнимает место для работы.
    """
    files = load(project_path).get("files", {})
    if not files:
        return "СОСТОЯНИЕ ПРОЕКТА: пока пусто — ты первый, кто предлагает файлы.\n\n"

    lines = ["СОСТОЯНИЕ ПРОЕКТА (файлы уже предложены другими агентами):"]
    for name, info in sorted(files.items())[:40]:
        author = info.get("author") or "агент"
        purpose = info.get("purpose") or ""
        lines.append(f"- {name} — {author}" + (f": {purpose}" if purpose else ""))
    lines.append(
        "Не создавай эти файлы повторно: дополняй своими, которых ещё нет в списке. "
        "Если твой файл уже есть — сделай правку через find/replace, а не копию.\n\n"
    )
    return "\n".join(lines)
