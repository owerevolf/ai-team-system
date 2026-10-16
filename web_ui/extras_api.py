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
