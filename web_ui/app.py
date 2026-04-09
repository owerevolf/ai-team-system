"""
AI Team System Web UI — FastAPI приложение с SSE-стримингом
Версия: 2.0
"""

import os
import sys
import json
import uuid
import queue
import hashlib
import time
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="AI Team System", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "web_ui" / "static"
TEMPLATES_DIR = BASE_DIR / "web_ui" / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

logger.remove()
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.add(sys.stderr, level=log_level, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add(BASE_DIR / ".logs" / "web_ui.log", rotation="10 MB", level="DEBUG", encoding="utf-8")

sessions: Dict[str, Dict[str, Any]] = {}
session_lock = threading.Lock()


class AgentQueryRequest(BaseModel):
    query: str
    agent_role: str = "teamlead"
    user_level: str = "beginner"
    session_id: Optional[str] = None


class CreateProjectRequest(BaseModel):
    project_name: str
    query: str
    clarifications: Optional[Dict] = {}
    level: Optional[str] = "beginner"


class AgentQueryResponse(BaseModel):
    status: str
    response: str
    metadata: Dict[str, Any]


class SessionManager:
    def __init__(self) -> None:
        self.active: Dict[str, Dict[str, Any]] = {}

    def create(self, user_level: str = "beginner", profile: str = "medium") -> str:
        session_id = str(uuid.uuid4())
        event_queue: queue.Queue[Dict[str, Any]] = queue.Queue()

        self.active[session_id] = {
            "user_level": user_level,
            "profile": profile,
            "events": event_queue,
            "created": datetime.now().isoformat(),
            "status": "idle",
            "history": [],
        }

        logger.info(f"Сессия создана: {session_id} (уровень={user_level})")
        return session_id

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.active.get(session_id)

    def add_event(self, session_id: str, event: Dict[str, Any]) -> None:
        sess = self.active.get(session_id)
        if sess:
            sess["events"].put(event)
            sess["history"].append(event)

    def cleanup(self, session_id: str) -> None:
        self.active.pop(session_id, None)


session_manager = SessionManager()


def validate_env() -> bool:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        example = BASE_DIR / ".env.example"
        if example.exists():
            import shutil
            shutil.copy2(example, env_file)
            logger.warning(".env не найден, скопирован из .env.example")
            return True
        logger.error("Нет .env и .env.example")
        return False
    return True


@app.on_event("startup")
async def startup() -> None:
    validate_env()
    logger.info("AI Team System Web UI запущен на порту 8000")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    return templates.TemplateResponse("welcome.html", {"request": request})


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": "2.0.0"})


@app.get("/favicon.ico")
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/sw.js")
async def service_worker() -> Response:
    return Response(status_code=204)


@app.get("/api/start")
async def start_tour(user_level: str = "beginner") -> JSONResponse:
    profile = os.getenv("HARDWARE_PROFILE", "medium")
    session_id = session_manager.create(user_level=user_level, profile=profile)
    return JSONResponse({"session_id": session_id, "status": "started", "user_level": user_level})


@app.get("/api/stream")
async def stream_events(session_id: str) -> Response:
    sess = session_manager.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    async def event_generator():
        while True:
            try:
                event = sess["events"].get(timeout=1.0)
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
                if event.get("type") == "complete":
                    break
            except queue.Empty:
                yield ": keepalive\n\n"

    return Response(event_generator(), media_type="text/event-stream")


@app.post("/api/export")
async def export_lesson(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Невалидный JSON")

    session_id = body.get("session_id", "")
    sess = session_manager.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    from core.export_lesson import ExportLesson
    exporter = ExportLesson()
    lesson_path = exporter.generate(sess["history"], body.get("title", "Урок"))

    return JSONResponse({"path": str(lesson_path), "status": "exported"})


@app.post("/api/lesson/step")
async def lesson_step(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Невалидный JSON")

    session_id = body.get("session_id", "")
    step = body.get("step", 0)
    sess = session_manager.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    from core.learning_mode import LearningMode
    lm = LearningMode()
    beginner = sess["user_level"] == "beginner"
    step_data = lm.get_step(step, beginner_mode=beginner)

    session_manager.add_event(session_id, {
        "type": "step",
        "data": step_data,
        "time": datetime.now().isoformat(),
    })

    return JSONResponse(step_data)


@app.get("/api/hardware")
async def hardware_info() -> JSONResponse:
    from core.hardware_detector import HardwareDetector
    detector = HardwareDetector()
    info = detector.detect()
    return JSONResponse(info)


@app.get("/api/progress")
async def get_progress(session_id: str) -> JSONResponse:
    sess = session_manager.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    from core.learning_mode import LearningMode
    lm = LearningMode()
    progress = lm.get_progress_report()
    return JSONResponse(progress)


@app.post("/api/agent/query", response_model=AgentQueryResponse)
async def agent_query(req: AgentQueryRequest) -> AgentQueryResponse:
    logger.info(f"Запрос агента: role={req.agent_role}, level={req.user_level}, query_len={len(req.query)}")

    beginner = req.user_level == "beginner"
    profile = os.getenv("HARDWARE_PROFILE", "medium")

    prompt = f"Роль: {req.agent_role}. Задача: {req.query}"
    if beginner:
        prompt = f"[BEGINNER] {prompt}"

    prompt_hash = hashlib.sha256(f"{prompt}:{beginner}".encode()).hexdigest()[:12]

    from core.model_router import ModelRouter
    router = ModelRouter(profile=profile, beginner_mode=beginner)

    cached = router.get_cached(prompt_hash)
    if cached:
        logger.debug(f"Кэш-попадение: {prompt_hash}")
        return AgentQueryResponse(
            status="success",
            response=cached,
            metadata={
                "agent_role": req.agent_role,
                "model_used": router.ollama_model,
                "timestamp": datetime.now().isoformat(),
                "beginner_mode": beginner,
                "cached": True,
            },
        )

    if not router.check_rate_limit():
        raise HTTPException(status_code=429, detail="Слишком много запросов. Подождите.")

    try:
        answer = router.generate(prompt=prompt, agent=req.agent_role, beginner_mode=beginner)
        router.cache_set(prompt_hash, answer)

        if req.session_id:
            session_manager.add_event(req.session_id, {
                "type": "agent_response",
                "data": {"role": req.agent_role, "query": req.query, "response_len": len(answer)},
                "time": datetime.now().isoformat(),
            })

        logger.info(f"Ответ агента получен: {len(answer)} символов")
        return AgentQueryResponse(
            status="success",
            response=answer,
            metadata={
                "agent_role": req.agent_role,
                "model_used": router.ollama_model,
                "timestamp": datetime.now().isoformat(),
                "beginner_mode": beginner,
                "cached": False,
            },
        )
    except RuntimeError as e:
        logger.error(f"Ошибка маршрутизации: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка агента: {e}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {e}")


def _parse_and_write_files(response: str, project_dir: Path) -> list:
    """
    Парсим ответ агента, находим tool_call с create_file
    и реально пишем файлы на диск.
    Возвращает список созданных файлов.
    """
    import re
    created = []

    # Ищем все JSON-блоки с "tool": "create_file"
    # Модель может выдать как <tool_call>{...}</tool_call> так и голый JSON
    patterns = [
        r'<tool_call>\s*(\{[\s\S]*?\})\s*</tool_call>',  # обёрнутый
        r'(\{"tool"\s*:\s*"create_file"[\s\S]*?\})(?=\s*\{|\s*$)',  # голый JSON
    ]

    candidates = []
    for pattern in patterns:
        candidates.extend(re.findall(pattern, response))

    for raw in candidates:
        # Пробуем распарсить — JSON может быть обрезан
        # Добиваем закрывающие скобки если не хватает
        for suffix in ['', '}', '}}', '}}}']:
            try:
                data = json.loads(raw + suffix)
                if data.get('tool') == 'create_file' and 'path' in data and 'content' in data:
                    rel_path = data['path'].lstrip('/')
                    # Защита от path traversal
                    target = (project_dir / rel_path).resolve()
                    if not str(target).startswith(str(project_dir)):
                        logger.warning(f"Path traversal попытка: {rel_path}")
                        break
                    target.parent.mkdir(parents=True, exist_ok=True)
                    content = data['content']
                    # Убираем markdown-обёртку если есть (```python ... ```)
                    content = re.sub(r'^```\w*\n', '', content)
                    content = re.sub(r'\n```$', '', content)
                    target.write_text(content, encoding='utf-8')
                    created.append(str(rel_path))
                    logger.info(f"Файл создан: {rel_path}")
                    break
            except (json.JSONDecodeError, KeyError):
                continue

    return created


def _level_hint(level: str) -> str:
    """Добавляем подсказку агентам о уровне пользователя"""
    hints = {
        "zero": "ВАЖНО: Пользователь — абсолютный новичок. Объясняй каждый шаг простыми словами с аналогиями.",
        "beginner": "ВАЖНО: Пользователь — начинающий. Объясняй логику решений.",
        "advanced": "Пользователь — продвинутый. Минимум объяснений, максимум конкретики.",
    }
    return hints.get(level, hints["beginner"])


@app.post("/api/create_project_stream")
async def create_project_stream(req: CreateProjectRequest):
    """SSE-стриминг работы агентов с реальной записью файлов на диск"""

    async def event_stream():
        agents = ["teamlead", "architect", "backend", "frontend", "devops", "tester", "documentalist"]
        full_query = f"Создай проект '{req.project_name}': {req.query}"
        if req.clarifications:
            full_query += f"\nДополнения: {json.dumps(req.clarifications, ensure_ascii=False)}"

        level_hint = _level_hint(req.level)
        query_with_level = f"{level_hint}\n\n{full_query}"

        # Папка проекта — ~/ai-team-projects/<project_name>/
        projects_root = Path.home() / "ai-team-projects"
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in req.project_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = projects_root / f"{safe_name}_{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Папка проекта: {project_dir}")

        # Сообщаем UI где будет проект
        yield f"data: {json.dumps({'type': 'project_dir', 'path': str(project_dir)})}\n\n"

        results = {}
        all_files = []

        # Инициализируем AgentManager и ModelRouter один раз
        from core.agent_manager import AgentManager
        from core.model_router import ModelRouter
        router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
        manager = AgentManager(model_router=router)

        for agent in agents:
            yield f"data: {json.dumps({'type': 'agent_start', 'agent': agent})}\n\n"
            await asyncio.sleep(0)

            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda a=agent: manager.run_agent(a, query_with_level)
                )
                raw_response = result.get('response', result.get('summary', str(result)))

                # Пишем файлы на диск
                created_files = await asyncio.get_event_loop().run_in_executor(
                    None, lambda r=raw_response: _parse_and_write_files(r, project_dir)
                )
                all_files.extend(created_files)

                results[agent] = raw_response

                yield f"data: {json.dumps({'type': 'agent_done', 'agent': agent, 'response': raw_response, 'files': created_files}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"Агент {agent} ошибка: {e}")
                results[agent] = f"Ошибка: {str(e)}"
                yield f"data: {json.dumps({'type': 'agent_done', 'agent': agent, 'response': str(e), 'files': []})}\n\n"

            await asyncio.sleep(0.1)

        # Финал
        yield f"data: {json.dumps({'type': 'done', 'project': req.project_name, 'project_dir': str(project_dir), 'total_files': len(all_files), 'files': all_files})}\n\n"

        # Экспорт markdown
        try:
            from core.export_lesson import ExportLesson
            exporter = ExportLesson()
            exporter.generate([{"type": "project", "data": results}], req.project_name)
        except Exception:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Скачать Markdown-результат проекта"""
    from core.export_lesson import ExportLesson
    exporter = ExportLesson()
    lessons = exporter.list_lessons()
    
    for lesson in lessons:
        if filename in lesson.get("name", ""):
            return FileResponse(lesson["path"], media_type="text/markdown", filename=filename)
    
    raise HTTPException(status_code=404, detail=f"Файл {filename} не найден")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_ui.app:app", host="0.0.0.0", port=8000, reload=False)