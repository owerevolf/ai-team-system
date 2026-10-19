"""Источник правды проекта: замысел, факты, статус и история.

Зачем это нужно
---------------
Агенты работают по очереди и не видят друг друга. Раньше «источником правды» был
список имён файлов (`_truth.json`): он говорил, что файл существует, но не говорил,
что внутри и зачем. Маленькая модель достраивала остальное догадками.

Правило, на котором держится этот модуль
---------------------------------------
**Факты считают инструменты, а не модель.** Что файл существует, какие в нём
функции и импорты, что сломала проверка сборки — берётся с диска, из AST и из
результата `check_build`. Модель пишет только «зачем»: назначение файла.

Что хранится
------------
1. `intent`  — что просил человек, его уровень, уточнения;
2. `plan`    — какие файлы и зачем задуманы (контракт для остальных);
3. `files`   — факты по каждому файлу: назначение, автор, функции, импорты;
4. `checks`  — последняя проверка сборки: ошибки, тесты;
5. `reviews` — вердикты TeamLead;
6. `events`  — журнал в `.ai-team/events.jsonl`, из него можно собрать историю.

Снимок (`_state.json`) — производная от журнала и диска. Старый `_truth.json`
читается и переносится, чтобы текущие проекты не потерялись.
"""

from __future__ import annotations

import ast
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

STATE_NAME = "_state.json"
LEGACY_NAME = "_truth.json"
EVENTS_DIR = ".ai-team"
EVENTS_NAME = "events.jsonl"
VERSION = 2
SLICE_LIMIT = 1200

# Что вообще считается файлом проекта (для сверки с диском).
CODE_SUFFIXES = {".py", ".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".sql"}
TEXT_SUFFIXES = {".md", ".txt", ".yml", ".yaml", ".sh", ".conf", ".toml", ".ini", ".cfg", ".rst"}
SPECIAL_NAMES = {"dockerfile", "makefile", ".gitignore", "requirements.txt", ".env.example"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _empty(root: Path) -> Dict[str, Any]:
    return {
        "version": VERSION,
        "project": root.name,
        "intent": {"idea": "", "level": "", "clarifications": [], "updated": ""},
        "plan": {"files": {}, "author": "", "updated": ""},
        "files": {},
        "checks": {},
        "reviews": [],
        "updated": "",
    }


def _state_path(root: Path) -> Path:
    return Path(root) / STATE_NAME


def _events_path(root: Path) -> Path:
    return Path(root) / EVENTS_DIR / EVENTS_NAME


# ── запись и чтение ──────────────────────────────────────────────────


def save(root: Optional[Path], state: Dict[str, Any]) -> bool:
    """Пишет снимок атомарно: сбой посреди записи не оставит половину файла."""
    if not root:
        return False
    try:
        root = Path(root)
        state["version"] = VERSION
        state["updated"] = _now()
        target = _state_path(root)
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, target)
        return True
    except Exception:  # noqa: BLE001 — состояние не должно ломать работу агента
        return False


def event(root: Optional[Path], kind: str, **data: Any) -> None:
    """Дописывает событие в журнал. Журнал — источник истории, его не переписываем."""
    if not root:
        return
    try:
        path = _events_path(Path(root))
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"at": _now(), "event": kind, **data}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _migrate_legacy(root: Path) -> Optional[Dict[str, Any]]:
    """Переносит старый `_truth.json` (список файлов) в новое состояние."""
    legacy = root / LEGACY_NAME
    if not legacy.is_file():
        return None
    try:
        data = json.loads(legacy.read_text(encoding="utf-8"))
        files = data.get("files", {}) if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return None

    state = _empty(root)
    for name, info in files.items():
        info = info or {}
        facts = scan_file(root, name)
        state["files"][name] = {
            "purpose": str(info.get("purpose") or "")[:200],
            "author": str(info.get("author") or ""),
            "updated_by": "",
            "api": facts["api"],
            "imports": facts["imports"],
            "at": str(info.get("at") or ""),
        }
    state["updated"] = _now()
    return state


def load(root: Optional[Path]) -> Dict[str, Any]:
    """Читает состояние. Нет файла — собирает из старого формата или с нуля."""
    if not root:
        return _empty(Path("."))
    root = Path(root)
    path = _state_path(root)
    if path.is_file():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(state, dict):
                state.setdefault("version", VERSION)
                state.setdefault("files", {})
                state.setdefault("intent", {"idea": "", "level": "", "clarifications": [], "updated": ""})
                state.setdefault("plan", {"files": {}, "author": "", "updated": ""})
                state.setdefault("checks", {})
                state.setdefault("reviews", [])
                return state
        except Exception:  # noqa: BLE001 — испорченный снимок: пробуем старый формат
            pass

    migrated = _migrate_legacy(root)
    if migrated is not None:
        save(root, migrated)
        return migrated
    return _empty(root)


# ── факты из кода ────────────────────────────────────────────────────


def scan_file(root: Path, rel: str) -> Dict[str, List[str]]:
    """Публичные функции/классы и импорты файла — только для Python."""
    result: Dict[str, List[str]] = {"api": [], "imports": []}
    path = Path(root) / rel
    if path.suffix.lower() != ".py" or not path.is_file():
        return result
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return result

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            args = [arg.arg for arg in node.args.args][:4]
            result["api"].append(f"{node.name}({', '.join(args)})")
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            result["api"].append(node.name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                if name not in result["imports"]:
                    result["imports"].append(name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            name = node.module.split(".")[0]
            if name not in result["imports"]:
                result["imports"].append(name)

    result["api"] = result["api"][:8]
    result["imports"] = result["imports"][:8]
    return result


def record_file(
    root: Optional[Path],
    rel: str,
    author: str = "",
    purpose: str = "",
) -> bool:
    """Записывает файл: кто, зачем и что в нём есть на самом деле."""
    if not root:
        return False
    root = Path(root)
    rel = str(rel).replace("\\", "/")
    state = load(root)
    entry = state["files"].get(rel, {})
    facts = scan_file(root, rel)

    entry.update(
        {
            "purpose": (purpose or entry.get("purpose") or "")[:200],
            # Создателя не перезаписываем: поздний агент — это «кто обновил».
            "author": entry.get("author") or author or "",
            "updated_by": author or entry.get("updated_by") or "",
            "api": facts["api"],
            "imports": facts["imports"],
            "at": _now(),
        }
    )
    state["files"][rel] = entry
    event(root, "file_written", path=rel, author=author, api=len(facts["api"]))
    return save(root, state)


def record_plan(root: Optional[Path], files: Dict[str, str], author: str = "architect") -> bool:
    """План архитектора: какие файлы и зачем. Остальные агенты на него опираются."""
    if not root:
        return False
    root = Path(root)
    state = load(root)
    state["plan"] = {
        "files": {str(k).replace("\\", "/"): str(v)[:160] for k, v in files.items()},
        "author": author,
        "updated": _now(),
    }
    event(root, "plan_recorded", files=len(files), author=author)
    return save(root, state)


def record_intent(root: Optional[Path], idea: str, level: str = "", clarifications: Optional[list] = None) -> bool:
    """Замысел: что человек попросил и на каком уровне. Без него агенты теряют смысл."""
    if not root:
        return False
    root = Path(root)
    state = load(root)
    state["intent"] = {
        "idea": str(idea)[:600],
        "level": str(level),
        "clarifications": [str(item)[:200] for item in (clarifications or [])][:10],
        "updated": _now(),
    }
    event(root, "intent_recorded", level=level)
    return save(root, state)


def record_check(root: Optional[Path], report: Dict[str, Any]) -> bool:
    """Последняя проверка сборки: факты, а не пересказ модели."""
    if not root:
        return False
    root = Path(root)
    state = load(root)
    state["checks"] = {
        "ok": bool(report.get("ok")),
        "errors": list(report.get("errors") or [])[:10],
        "warnings": list(report.get("warnings") or [])[:10],
        "tests": report.get("tests") or {},
        "files": report.get("files"),
        "at": _now(),
    }
    event(root, "check_recorded", ok=state["checks"]["ok"], errors=len(state["checks"]["errors"]))
    return save(root, state)


def record_review(root: Optional[Path], verdict: str, summary: str = "") -> bool:
    """Вердикт TeamLead: что он решил после проверки."""
    if not root:
        return False
    root = Path(root)
    state = load(root)
    state["reviews"] = (state.get("reviews") or [])[-9:] + [
        {"at": _now(), "verdict": verdict, "summary": str(summary)[:400]}
    ]
    event(root, "review_recorded", verdict=verdict)
    return save(root, state)


# ── сверка с диском ─────────────────────────────────────────────────


def _project_files(root: Path) -> List[str]:
    found: List[str] = []
    for path in Path(root).rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if any(part in {".git", "__pycache__", ".ai-team", ".pytest_cache", ".cache", "venv", ".venv", "node_modules"} for part in parts[:-1]):
            continue
        name = path.name.lower()
        if name == STATE_NAME or name == LEGACY_NAME:
            continue
        if path.suffix.lower() in CODE_SUFFIXES | TEXT_SUFFIXES or name in SPECIAL_NAMES:
            found.append("/".join(path.relative_to(root).parts))
    return found


def reconcile(root: Optional[Path], state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Приводит записи в согласие с диском: удалённые убирает, новые добавляет."""
    if not root:
        return state or {}
    root = Path(root)
    state = state or load(root)
    on_disk = set(_project_files(root))
    known = set(state.get("files", {}))

    changed = False
    for missing in known - on_disk:
        state["files"].pop(missing, None)
        event(root, "file_missing", path=missing)
        changed = True
    for new in on_disk - known:
        facts = scan_file(root, new)
        state["files"][new] = {
            "purpose": "",
            "author": "",
            "updated_by": "",
            "api": facts["api"],
            "imports": facts["imports"],
            "at": _now(),
        }
        event(root, "file_found", path=new)
        changed = True

    if changed:
        save(root, state)
    return state


# ── срезы для промпта ───────────────────────────────────────────────


def _clip(text: str, limit: int = SLICE_LIMIT) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _intent_line(state: Dict[str, Any]) -> str:
    intent = state.get("intent") or {}
    idea = (intent.get("idea") or "").strip().replace("\n", " ")
    if not idea:
        return ""
    level = intent.get("level") or ""
    suffix = f" (уровень: {level})" if level else ""
    return f"Замысел: {idea}{suffix}"


def slice_for(root: Optional[Path], agent: str = "", limit: int = SLICE_LIMIT) -> str:
    """Короткая справка под конкретного агента: только то, что ему нужно сейчас.

    Всем подряд одно и то же показывать нельзя: у маленькой модели каждый лишний
    абзац отнимает место для работы.
    """
    if not root:
        return ""
    root = Path(root)
    state = reconcile(root, load(root))
    files = state.get("files", {})
    if not files:
        return "СОСТОЯНИЕ ПРОЕКТА: пока пусто — ты первый, кто создаёт файлы."

    checks = state.get("checks") or {}
    errors = checks.get("errors") or []
    lines: List[str] = []

    intent = _intent_line(state)
    if intent and agent in {"teamlead", "architect", "documentalist", ""}:
        lines.append(intent)

    if agent == "tester":
        lines.append("Что можно проверить (факты из кода):")
        for name, info in sorted(files.items())[:10]:
            if info.get("api"):
                lines.append(f"- {name}: " + ", ".join(info["api"][:5]))
        if errors:
            lines.append("Что сломано сейчас:")
            lines += [f"- {item}" for item in errors[:4]]
        tests = checks.get("tests") or {}
        if tests.get("ran"):
            lines.append(f"Прошлый прогон тестов: {tests.get('passed', 0)} прошло, {tests.get('failed', 0)} упало.")
        lines.append("Проверяй поведение этих функций, а не наличие пакетов.")
        return _clip("\n".join(lines), limit)

    if agent in {"backend", "frontend"}:
        own = [name for name in files if _owns(agent, name)]
        if own:
            lines.append("Твои файлы уже есть:")
            for name in own[:6]:
                info = files[name]
                api = f": {', '.join(info['api'][:4])}" if info.get("api") else ""
                lines.append(f"- {name}{api}")
        if errors:
            lines.append("Сломано (правь это, а не переписывай всё):")
            lines += [f"- {item}" for item in errors[:4]]
        plan = (state.get("plan") or {}).get("files") or {}
        if plan:
            planned = ", ".join(list(plan)[:5])
            lines.append(f"План проекта: {planned}.")
        return _clip("\n".join(lines), limit)

    if agent == "teamlead":
        lines.append(f"Файлов в проекте: {len(files)}.")
        lines.append("Проверка сборки: " + ("ошибок нет." if checks.get("ok") else f"{len(errors)} ошибок."))
        for item in errors[:4]:
            lines.append(f"- {item}")
        plan = (state.get("plan") or {}).get("files") or {}
        if plan:
            outside = [name for name in files if name not in plan]
            lines.append(f"В плане {len(plan)} файлов" + (f"; вне плана: {', '.join(outside[:4])}." if outside else "."))
        return _clip("\n".join(lines), limit)

    if agent == "documentalist":
        entry = next((name for name in ("main.py", "app.py", "index.html") if name in files), "")
        lines.append("Файлы проекта:")
        for name in sorted(files)[:10]:
            purpose = files[name].get("purpose") or ""
            lines.append(f"- {name}" + (f" — {purpose}" if purpose else ""))
        if entry:
            lines.append(f"Точка входа: {entry}.")
        return _clip("\n".join(lines), limit)

    # Архитектор и все остальные: кто что сделал и зачем.
    plan = (state.get("plan") or {}).get("files") or {}
    if plan:
        lines.append("План проекта: " + ", ".join(f"{name}" for name in list(plan)[:6]) + ".")
    lines.append("Файлы проекта:")
    for name, info in sorted(files.items())[:12]:
        author = info.get("author") or "агент"
        purpose = info.get("purpose") or ""
        lines.append(f"- {name} — {author}" + (f": {purpose}" if purpose else ""))
    lines.append("Не создавай эти файлы повторно: дополняй своими.")
    return _clip("\n".join(lines), limit)


def _owns(agent: str, name: str) -> bool:
    suffix = Path(name).suffix.lower()
    if agent == "backend":
        return suffix == ".py" and not name.startswith("tests/")
    if agent == "frontend":
        return suffix in {".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx"}
    return False


def snapshot_for_human(root: Optional[Path]) -> Dict[str, Any]:
    """Состояние для интерфейса и отладки: без обрезки и служебных полей."""
    if not root:
        return {}
    return reconcile(Path(root), load(Path(root)))
