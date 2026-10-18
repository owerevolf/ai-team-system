"""
Дополнительные эндпоинты: словарь терминов и агент истины.

Вынесены отдельным роутером, чтобы не разрастался `web_ui/app.py`
(в нём уже больше 1500 строк). Подключаются одной строкой:

    from web_ui.extras_api import router as extras_router
    app.include_router(extras_router)

Что даёт:
* `GET  /api/glossary`          — весь глоссарий для панели «Словарь»;
* `GET  /api/glossary/explain`  — короткое объяснение одного термина;
* `POST /api/truth/ask`         — факты о коде со ссылками `файл:строка`;
* `POST /api/truth/verify`      — проверка текста на выдуманные имена.

Правило агента истины: пустой список фактов — это честный ответ
«в коде этого нет», а не повод догадываться.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

router = APIRouter()

_UI_STATE = Path(__file__).resolve().parent.parent / ".cache" / "ui_settings.json"


@router.post("/api/ui/language")
async def set_ui_language(request: Request) -> Dict[str, Any]:
    """Запоминает выбранный язык интерфейса.

    Этот же выбор просит у модели агент (см. core/agent_manager): на русском —
    отвечай по-русски, код остаётся кодом.
    """
    body = await request.json()
    language = str(body.get("lang", "")).strip().lower()[:8]
    if language not in {"ru", "en"}:
        raise HTTPException(status_code=400, detail="поддерживаются ru и en")

    _UI_STATE.parent.mkdir(parents=True, exist_ok=True)
    _UI_STATE.write_text(
        json.dumps({"language": language}, ensure_ascii=False), encoding="utf-8"
    )
    return {"status": "ok", "language": language}


@router.get("/api/ui/language")
def get_ui_language() -> Dict[str, Any]:
    """Отдаёт сохранённый язык интерфейса — без файла считается русский."""
    try:
        saved = json.loads(_UI_STATE.read_text(encoding="utf-8"))
        language = str(saved.get("language", "ru"))
    except Exception:  # noqa: BLE001 — нет файла или испорчен: считаем русский
        language = "ru"
    return {"language": language}


# Тот же адрес, куда пишет сборка проекта: иначе список сеансов окажется пустым.
_SESSIONS_DIR = Path(os.getenv("USERPROFILE") or Path.home()) / "ai-team-projects"


@router.get("/api/file")
def read_project_file(path: str) -> Dict[str, Any]:
    """Отдаёт содержимое файла для панели кода — только внутри папки проектов.

    Границы проверяются: иначе панель кода стала бы дырой наружу.
    """
    root = _SESSIONS_DIR.resolve()
    target = Path(path).resolve()
    if root != target and root not in target.parents:
        raise HTTPException(status_code=403, detail="файл вне папки проектов")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="файла нет")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"не прочитать: {exc}")
    return {
        "path": str(target),
        "name": target.name,
        "content": content[:20000],
        "truncated": len(content) > 20000,
    }


@router.post("/api/agent/ask")
async def ask_agent(request: Request) -> Dict[str, Any]:
    """Вопрос агенту на паузе: только объяснение, без файлов и без следующего шага.

    Человек спрашивает Архитектора (или любого) столько, сколько нужно, прежде
    чем нажать «Дальше». Сборка при этом стоит.
    """
    from core.agent_manager import AgentManager
    from core.model_router import ModelRouter

    body = await request.json()
    agent = str(body.get("agent", "architect"))
    question = str(body.get("question", "")).strip()[:2000]
    level = str(body.get("level", "zero"))
    if not question:
        raise HTTPException(status_code=400, detail="пустой вопрос")

    manager = AgentManager(ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium")))
    prompt = (
        manager.get_agent_prompt(agent, level)
        + "\n\nСейчас ты НЕ создаёшь и НЕ меняешь файлы: ты объясняешь человеку то, что он спросил. "
        + "Ответь коротко и простыми словами.\n\nВопрос: "
        + question
    )
    answer = manager.model_router.generate(prompt=prompt, agent=agent)
    return {"status": "ok", "agent": agent, "answer": str(answer or "")[:4000]}


@router.post("/api/build/continue")
async def build_continue(request: Request) -> Dict[str, Any]:
    """Продолжает сборку после паузы «Дальше».

    Человек читает объяснение агента столько, сколько нужно, и только потом
    отправляет следующего — или продолжает разговор с текущим.
    """
    from core.build_gates import gate

    body = await request.json()
    build_id = str(body.get("build", ""))
    released = gate.release(build_id)
    return {"status": "ok", "released": released, "build": build_id}


@router.post("/api/approvals/export")
def export_pending() -> Dict[str, Any]:
    """Складывает неподтверждённые правки в отдельную папку для просмотра.

    Зачем: качество работы надо оценивать по настоящим файлам, а не по описаниям.
    Проект при этом не трогается, а папка просмотра удаляется одной командой.
    """
    from core.project_manager.runtime.developer.developer_api import (
        approvals_runtime,
        patch_engine,
    )

    root = Path(os.getenv("USERPROFILE") or Path.home()) / "ai-team-projects" / "_просмотр"
    target = root / datetime.now().strftime("%Y%m%d_%H%M%S")
    written = []

    for request in approvals_runtime().get_pending():
        patch = patch_engine().get_patch(getattr(request, "patch_id", ""))
        if not patch:
            continue
        folder = target / request.request_id[:8]
        for change in getattr(patch, "files", []) or []:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / Path(change.file_path).name
            path.write_text(change.new_content or "", encoding="utf-8")
            written.append(str(path))

    return {"folder": str(target) if written else "", "files": written, "count": len(written)}


@router.get("/api/health/model")
def health_model() -> Dict[str, Any]:
    """Проверяет, отвечает ли модель из того же процесса, что и приложение.

    Сообщение «модель не ответила» одинаковое, а причины разные: модель не запущена
    или приложение её не видит. Эта проверка показывает, что именно.
    """
    try:
        from core.model_router import ModelRouter

        router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
        answer = str(
            router.generate(
                prompt="Ответь одним коротким предложением: ты работаешь и готов помогать?",
                agent="teamlead",
            )
            or ""
        )[:300]
        failed = "не ответила" in answer or "не настроены" in answer
        return {
            "ok": not failed,
            "model": os.getenv("OLLAMA_MODEL", "не задана в .env"),
            "answer": answer,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}


def _session_title(folder_name: str) -> str:
    """Читаемое имя проекта: без временной метки и подчёркиваний.

    Папка называется «идея_20261016_223525» — человеку нужно «идея».
    """
    import re

    cleaned = re.sub(r"_\d{8}_\d{6}$", "", folder_name)
    return cleaned.replace("_", " ").strip() or folder_name


@router.get("/api/sessions")
def list_sessions() -> Dict[str, Any]:
    """Прошлые проекты: имя, когда делали, сколько файлов внутри.

    История лежит рядом с приложением, поэтому не исчезает вместе с вкладкой
    браузера — можно вернуться к любому проекту и посмотреть, что в нём.
    """
    items = []
    if _SESSIONS_DIR.exists():
        folders = sorted(
            (p for p in _SESSIONS_DIR.iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:50]
        for folder in folders:
            files = [f for f in folder.rglob("*") if f.is_file()]
            items.append(
                {
                    "name": folder.name,
                    "title": _session_title(folder.name),
                    "path": str(folder),
                    "modified": datetime.fromtimestamp(folder.stat().st_mtime).isoformat(
                        timespec="minutes"
                    ),
                    "file_count": len(files),
                    "files": [str(f.relative_to(folder)) for f in files[:20]],
                }
            )
    return {"sessions": items}


@router.get("/api/providers")
def providers_status(request: Request) -> Dict[str, Any]:
    """Каталог облачных провайдеров и результат живой пробы.

    Ключи не читаются и не отдаются: проба сообщает только «доступно / нет ключа / не отвечает».
    Без параметра отдаётся последний сохранённый результат, с `?refresh=1` — свежая проверка.
    """
    from core import provider_probe as probe

    refresh = str(request.query_params.get("refresh", "")).lower() in {"1", "true", "yes"}
    if refresh:
        state = probe.probe_all()
        probe.save_state(state)
    else:
        state = probe.load_state()

    return {
        "providers": probe.catalogue_for_ui(),
        "probe": state,
        "free_available": probe.free_available(state),
        "checked_now": refresh,
    }

_index = None


def get_index():
    """Индекс фактов о репозитории: строится один раз за жизнь процесса."""
    global _index
    if _index is None:
        from core.truth import CodeIndex

        root = Path(__file__).resolve().parent.parent
        _index = CodeIndex(root).build()
    return _index


@router.get("/api/glossary")
async def glossary_terms():
    """Глоссарий терминов — для панели «Словарь»."""
    from core.glossary import list_terms

    terms = list_terms()
    return JSONResponse({"total": len(terms), "terms": terms})


@router.get("/api/glossary/explain")
async def glossary_explain(term: str = ""):
    """Короткое объяснение одного термина: «термин — простыми словами …»."""
    from core.glossary import explain, find_term

    item = find_term(term)
    if not item:
        return JSONResponse({"found": False, "term": term})

    payload: Dict[str, Any] = dict(item)
    payload["explanation"] = explain(term)
    return JSONResponse({"found": True, "term": payload})


@router.post("/api/truth/ask")
async def truth_ask(request: Request):
    """
    Ищет факты о коде по вопросу и возвращает их со ссылками `файл:строка`.

    Пустой ответ `found: 0` — сигнал «в репозитории этого нет»: вызывающая сторона
    обязана так и сказать пользователю, а не придумывать.
    """
    from core.truth import ask

    payload = await request.json()
    question = str(payload.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    facts: List[Dict[str, Any]] = [fact.to_dict() for fact in ask(question, get_index())]
    return JSONResponse({"question": question, "found": len(facts), "facts": facts})


@router.post("/api/truth/verify")
async def truth_verify(request: Request):
    """Проверяет текст на имена, которых нет в репозитории."""
    from core.truth import verify_text

    payload = await request.json()
    text = str(payload.get("text") or "")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    issues = [issue.to_dict() for issue in verify_text(text, get_index())]
    return JSONResponse({"unverified": len(issues), "issues": issues})


@router.get("/api/tour")
async def tour_steps(lang: str = "ru"):
    """
    Шаги обучающего Тура из ресурса `config/tour/<язык>.json`.

    Тексты вынесены из JavaScript: добавить язык — значит добавить файл,
    код при этом не меняется. Если файла языка нет — отдаём русский.
    """
    base = Path(__file__).resolve().parent.parent / "config" / "tour"
    for candidate in (base / f"{str(lang).strip().lower()}.json", base / "ru.json"):
        if candidate.exists():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            steps = data.get("steps", [])
            return JSONResponse({
                "language": data.get("language", lang),
                "total": len(steps),
                "steps": steps,
            })
    return JSONResponse({"language": lang, "total": 0, "steps": []})
