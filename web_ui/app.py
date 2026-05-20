"""
AI Team System Web UI — FastAPI приложение с SSE-стримингом
Версия: 2.0
"""

import os
import re
import sys
import time
import threading
import json
import uuid
import queue
import hashlib
import hmac
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from loguru import logger

# Import repo router (must be before app creation for include_router)
from web_ui.repo_endpoints import router as repo_router

# Import developer router
from core.project_manager.runtime.developer.developer_api import router as developer_router

# Import tooling router
from core.project_manager.tooling.tooling_api import router as tooling_router

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

# Include repo router
app.include_router(repo_router)

# Include developer router
app.include_router(developer_router)

# Include tooling router
app.include_router(tooling_router)

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

# Import webhook manager
from core.webhooks import webhook_manager

# Global orchestrator reference (set during startup)
_ai_team_system = None


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
    # Set orchestrator for repo endpoints
    from web_ui.repo_endpoints import set_orchestrator
    set_orchestrator(_ai_team_system)
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


@app.post("/api/generate_clarify_questions")
async def generate_clarify_questions(request: Request) -> JSONResponse:
    """Генерирует уточняющие вопросы через LLM на основе идеи проекта и уровня"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Невалидный JSON")
    
    project_idea = body.get("project_idea", "")
    level = body.get("level", "beginner")
    
    if not project_idea:
        raise HTTPException(status_code=400, detail="Нет идеи проекта")
    
    # Промт для генерации вопросов
    level_prompts = {
        "zero": (
            "Ты — TeamLead в команде разработки. Пользователь — абсолютный новичок.\n"
            "Сгенерируй 3 простых уточняющих вопроса для проекта. Вопросы должны быть ОЧЕНЬ простыми, "
            "без технических терминов. Используй аналогии.\n\n"
            "Пример стиля: 'Это только для тебя или другие тоже будут пользоваться?'\n\n"
            f"Идея проекта: {project_idea}\n\n"
            "Ответь в формате JSON массива: [\"вопрос 1\", \"вопрос 2\", \"вопрос 3\"]"
        ),
        "beginner": (
            "Ты — TeamLead. Пользователь начинающий, знает основы.\n"
            "Сгенерируй 3-4 уточняющих вопроса. Можно использовать технические термицы, "
            "но кратко объясняй если нужно.\n\n"
            f"Идея проекта: {project_idea}\n\n"
            "Ответь в формате JSON массива: [\"вопрос 1\", \"вопрос 2\", \"вопрос 3\"]"
        ),
        "advanced": (
            "Ты — TeamLead. Пользователь продвинутый.\n"
            "Сгенерируй 3-4 технических уточняющих вопроса: стек, архитектура, БД, авторизация, деплой.\n\n"
            f"Идея проекта: {project_idea}\n\n"
            "Ответь в формате JSON массива: [\"вопрос 1\", \"вопрос 2\", \"вопрос 3\"]"
        ),
    }
    
    prompt = level_prompts.get(level, level_prompts["beginner"])
    
    from core.model_router import ModelRouter
    router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
    
    try:
        response = router.generate(prompt=prompt, agent="teamlead")
        
        # Парсим JSON из ответа
        import re
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
        else:
            # Fallback на хардкод
            questions = [
                "Нужна ли авторизация?",
                "Где будет работать — локально или в интернете?",
                "Есть предпочтения по стеку?"
            ]
        
        return JSONResponse({"questions": questions, "status": "success"})
    except Exception as e:
        logger.error(f"Ошибка генерации вопросов: {e}")
        # Fallback
        raise HTTPException(status_code=503, detail=f"LLM недоступен: {str(e)}")


@app.get("/api/progress")
async def get_progress(session_id: str) -> JSONResponse:
    sess = session_manager.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

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

    Устойчив к обрезанному JSON — модель часто не успевает
    закрыть все скобки из-за лимита токенов.
    """
    created = []

    def try_write(path_str: str, content: str) -> bool:
        """Записываем файл на диск. Возвращает True если успешно."""
        if not path_str or not content:
            return False
        rel_path = path_str.lstrip('/')
        # Защита от path traversal
        target = (project_dir / rel_path).resolve()
        if not str(target).startswith(str(project_dir.resolve())):
            logger.warning(f"Path traversal попытка: {rel_path}")
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        # Убираем markdown-обёртку если есть
        content = re.sub(r'^```[\w]*\n?', '', content.strip())
        content = re.sub(r'\n?```$', '', content)
        target.write_text(content, encoding='utf-8')
        created.append(rel_path)
        logger.info(f"Файл создан: {rel_path}")
        return True

    # ── Метод 1: ищем полные JSON-блоки (обёрнутые в <tool_call> или голые)
    # Сначала разворачиваем <tool_call>...</tool_call>
    unwrapped = re.sub(r'<tool_call>\s*', '', response)
    unwrapped = re.sub(r'\s*</tool_call>', '\n', unwrapped)

    # Находим все начала JSON с "tool": "create_file"
    starts = [m.start() for m in re.finditer(r'\{"tool"\s*:\s*"create_file"', unwrapped)]

    for start in starts:
        chunk = unwrapped[start:]

        # Пробуем распарсить с нарастающим количеством закрывающих скобок
        parsed = None
        for end_offset in range(len(chunk), max(len(chunk)-50, 0), -1):
            candidate = chunk[:end_offset]
            for suffix in ['', '}', '}}']:
                try:
                    obj = json.loads(candidate + suffix)
                    if isinstance(obj, dict) and obj.get('tool') == 'create_file':
                        parsed = obj
                        break
                except json.JSONDecodeError:
                    continue
            if parsed:
                break

        if parsed and 'path' in parsed and 'content' in parsed:
            try_write(parsed['path'], parsed['content'])
            continue

        # ── Метод 2: если JSON обрезан — вытаскиваем path и content регулярками
        path_match = re.search(r'"path"\s*:\s*"([^"]+)"', chunk[:500])
        # content может быть очень длинным — берём всё до конца чанка
        content_match = re.search(r'"content"\s*:\s*"([\s\S]*)', chunk)

        if path_match and content_match:
            raw_content = content_match.group(1)
            # Убираем хвост — незакрытые escape-последовательности
            raw_content = raw_content.rstrip('\\').rstrip('"').rstrip(',')
            # Декодируем \n \t и т.д.
            try:
                raw_content = raw_content.encode().decode('unicode_escape')
            except Exception:
                raw_content = raw_content.replace('\\n', '\n').replace('\\t', '\t')
            try_write(path_match.group(1), raw_content)

    return created


def _level_hint(level: str) -> str:
    """Добавляем подсказку агентам о уровне пользователя"""
    hints = {
        "zero": "ВАЖНО: Пользователь — абсолютный новичок. Объясняй каждый шаг простыми словами с аналогиями.",
        "beginner": "ВАЖНО: Пользователь — начинающий. Объясняй логику решений.",
        "advanced": "Пользователь — продвинутый. Минимум объяснений, максимум конкретики.",
    }
    return hints.get(level, hints["beginner"])


@app.post("/api/teamlead_query")
async def teamlead_query(req: CreateProjectRequest):
    """TeamLead задаёт вопрос и ждёт ответа — НЕ запускает других агентов"""
    
    async def event_stream():
        # UI уже шлёт правильный prompt (первый раз или повторный)
        full_query = req.query
        if req.clarifications:
            full_query += f"\nДополнения: {json.dumps(req.clarifications, ensure_ascii=False)}"

        level_hint = _level_hint(req.level)
        query_with_level = f"{level_hint}\n\n{full_query}"

        from core.agent_manager import AgentManager
        from core.model_router import ModelRouter
        router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
        manager = AgentManager(model_router=router)

        yield f"data: {json.dumps({'type': 'agent_start', 'agent': 'teamlead'})}\n\n"
        await asyncio.sleep(0)

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: manager.run_agent("teamlead", query_with_level, level=req.level)
            )

            raw_response = result.get('response', '')
            yield f"data: {json.dumps({'type': 'agent_done', 'agent': 'teamlead', 'response': raw_response, 'files': [], 'summary': ''}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'waiting_for_user', 'message': 'TeamLead ждёт вашего ответа'})}\n\n"

        except Exception as e:
            logger.error(f"TeamLead ошибка: {e}")
            yield f"data: {json.dumps({'type': 'agent_done', 'agent': 'teamlead', 'response': str(e), 'files': [], 'summary': 'Ошибка'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.post("/api/create_project_stream")
async def create_project_stream(req: CreateProjectRequest):
    """SSE-стриминг работы агентов (БЕЗ TeamLead — он уже был)"""

    async def event_stream():
        # TeamLead уже был, запускаем остальных
        agents = ["architect", "backend", "frontend", "devops", "tester", "documentalist"]
        full_query = f"Продолжаем проект '{req.project_name}': {req.query}"
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
        from core.model_router import ModelRouter
        router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
        manager = AgentManager(model_router=router)
        # Передаём папку проекта — теперь агенты сами пишут файлы
        manager.set_project_path(project_dir)

        for agent in agents:
            yield f"data: {json.dumps({'type': 'agent_start', 'agent': agent})}\n\n"
            await asyncio.sleep(0)

            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda a=agent: manager.run_agent(a, query_with_level, level=req.level)
                )

                raw_response = result.get('response', '')
                created_files = result.get('files_created', [])
                summary = result.get('summary', '')
                all_files.extend(created_files)
                results[agent] = raw_response

                yield f"data: {json.dumps({'type': 'agent_done', 'agent': agent, 'response': raw_response, 'files': created_files, 'summary': summary}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"Агент {agent} ошибка: {e}")
                results[agent] = f"Ошибка: {str(e)}"
                yield f"data: {json.dumps({'type': 'agent_done', 'agent': agent, 'response': str(e), 'files': [], 'summary': 'Ошибка'})}\n\n"

            await asyncio.sleep(0.1)

        # Финал
        yield f"data: {json.dumps({'type': 'done', 'project': req.project_name, 'project_dir': str(project_dir), 'total_files': len(all_files), 'files': all_files})}\n\n"

        # Экспорт markdown
        try:
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
    exporter = ExportLesson()
    lessons = exporter.list_lessons()
    
    for lesson in lessons:
        if filename in lesson.get("name", ""):
            return FileResponse(lesson["path"], media_type="text/markdown", filename=filename)
    
    raise HTTPException(status_code=404, detail=f"Файл {filename} не найден")


@app.post("/api/open_folder")
async def open_folder(request: Request):
    """Открыть папку проекта в файловом менеджере"""
    body = await request.json()
    path = body.get("path", "")
    if path and Path(path).exists():
        import subprocess
        subprocess.Popen(["xdg-open", path])
    return JSONResponse({"status": "ok"})


@app.post("/api/stop_build")
async def stop_build():
    """Остановить текущую сборку"""
    return JSONResponse({"status": "stopped"})


# ══════════════════════════════════════════
#  MODEL REGISTRY & PROVIDER CONFIG
# ══════════════════════════════════════════

@app.get("/api/providers")
async def list_providers(force_refresh: bool = False):
    """
    Список всех провайдеров с бесплатными моделями.
    Парсит OpenRouter, Ollama, OmniRoute.
    """
    from core.model_registry import refresh, get_free_models

    registry = refresh(force=force_refresh)

    result = {}
    for pid, info in registry.items():
        result[pid] = {
            "id": info.id,
            "name": info.name,
            "url": info.url,
            "api_base": info.api_base,
            "requires_key": info.requires_key,
            "is_available": info.is_available,
            "signup_url": info.signup_url,
            "api_key_url": info.api_key_url,
            "description": info.description,
            "models": [
                {
                    "id": m.id,
                    "name": m.name,
                    "context_length": m.context_length,
                    "strength": m.strength,
                    "description": m.description,
                }
                for m in info.models
            ],
            "free_models_count": len([m for m in info.models if m.is_free]),
        }

    return JSONResponse(result)


@app.get("/api/models")
async def list_models(
    provider: Optional[str] = None,
    strength: Optional[str] = None,
    min_context: int = 0,
):
    """
    Список бесплатных моделей с фильтрами.
    
    Args:
        provider: openrouter | ollama | omniroute
        strength: reasoning | coding | fast | strong | general
        min_context: минимальный размер контекста
    """
    from core.model_registry import get_free_models

    models = get_free_models(
        provider=provider,
        strength=strength,
        min_context=min_context,
    )

    return JSONResponse({
        "models": models,
        "total": len(models),
    })


@app.get("/api/agents/config")
async def get_agents_config():
    """
    Возвращает конфигурацию всех агентов:
    - скиллы (system prompt addon)
    - рекомендуемая модель
    - доступные модели для каждой роли
    """
    from core.agent_skills import list_agents, AGENT_SKILL_MAP
    from core.model_registry import get_free_models

    agents = list_agents()

    # Для каждого агента добавляем доступные модели
    for agent in agents:
        strength = agent["preferred_strength"]
        min_ctx = agent["min_context"]
        agent["available_models"] = get_free_models(
            strength=strength,
            min_context=min_ctx,
        )[:10]  # топ-10 моделей для роли

    return JSONResponse({
        "agents": agents,
        "default_assignments": {
            name: {
                "strength": cfg["preferred_strength"],
                "temperature": cfg["temperature"],
            }
            for name, cfg in AGENT_SKILL_MAP.items()
        },
    })


@app.post("/api/config")
async def save_config(request: Request):
    """
    Сохраняет конфигурацию провайдеров/моделей.
    Принимает JSON с настройками для каждого агента.
    
    Формат:
    {
        "openrouter_api_key": "sk-...",
        "ollama_model": "qwen3:8b",
        "agents": {
            "teamlead": {"provider": "openrouter", "model": "deepseek/deepseek-r1:free"},
            "backend": {"provider": "openrouter", "model": "qwen/qwen3-coder:free"}
        }
    }
    """
    body = await request.json()

    # Сохраняем API ключи в .env
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        env_content = env_path.read_text(encoding="utf-8")
    else:
        env_content = ""

    # Обновляем ключи
    key_mappings = {
        "openrouter_api_key": "OPENROUTER_API_KEY",
        "ollama_base_url": "OLLAMA_BASE_URL",
        "ollama_model": "OLLAMA_MODEL",
        "omniroute_api_key": "OMNIROUTE_API_KEY",
        "omniroute_url": "OMNIROUTE_URL",
    }

    for json_key, env_key in key_mappings.items():
        value = body.get(json_key)
        if value:
            pattern = rf'{env_key}=.*'
            if re.search(pattern, env_content):
                env_content = re.sub(pattern, f'{env_key}={value}', env_content)
            else:
                env_content += f'\n{env_key}={value}'

    env_path.write_text(env_content, encoding="utf-8")
    load_dotenv(env_path, override=True)

    # Сохраняем конфигурацию агентов в JSON
    agent_config = body.get("agents", {})
    if agent_config:
        config_path = BASE_DIR / "config" / "agent_models.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(
            json.dumps(agent_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    logger.info(f"Config saved: {list(body.keys())}")

    # Добавляем MCP сервер если указан
    mcp_add = body.get("mcp_add_server")
    if mcp_add:
        mcp_config_path = BASE_DIR / "config" / "mcp_servers.json"
        mcp_data = {"servers": []}
        if mcp_config_path.exists():
            mcp_data = json.loads(mcp_config_path.read_text(encoding="utf-8"))
        mcp_data["servers"].append(mcp_add)
        mcp_config_path.write_text(json.dumps(mcp_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Применяем конфигурацию на лету (без перезагрузки сервера)
    # Обновляем переменные окружения в текущем процессе
    for json_key, env_key in key_mappings.items():
        value = body.get(json_key)
        if value:
            os.environ[env_key] = value

    # Сохраняем AI_MODE
    ai_mode = body.get("ai_mode")
    if ai_mode in ("local", "cloud"):
        pattern = r'AI_MODE=.*'
        if re.search(pattern, env_content):
            env_content = re.sub(pattern, f'AI_MODE={ai_mode}', env_content)
        else:
            env_content += f'\nAI_MODE={ai_mode}'
        os.environ["AI_MODE"] = ai_mode

    env_path.write_text(env_content, encoding="utf-8")
    load_dotenv(env_path, override=True)

    return JSONResponse({
        "status": "saved",
        "message": "Конфигурация сохранена и применена.",
        "applied": list(agent_config.keys()) if agent_config else [],
        "ai_mode": os.getenv("AI_MODE", "local"),
    })


@app.get("/api/config")
async def get_config():
    """Возвращает текущую конфигурацию."""
    config_path = BASE_DIR / "config" / "agent_models.json"
    agent_config = {}
    if config_path.exists():
        agent_config = json.loads(config_path.read_text(encoding="utf-8"))

    # MCP servers config
    mcp_config_path = BASE_DIR / "config" / "mcp_servers.json"
    mcp_servers = []
    if mcp_config_path.exists():
        mcp_data = json.loads(mcp_config_path.read_text(encoding="utf-8"))
        mcp_servers = mcp_data.get("servers", [])

    return JSONResponse({
        "openrouter_api_key_set": bool(os.getenv("OPENROUTER_API_KEY")),
        "ollama_model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "omniroute_api_key_set": bool(os.getenv("OMNIROUTE_API_KEY")),
        "omniroute_url": os.getenv("OMNIROUTE_URL", "http://localhost:21000/v1"),
        "ai_mode": os.getenv("AI_MODE", "local"),
        "agents": agent_config,
        "mcp_servers": mcp_servers,
    })


@app.get("/api/status")
async def system_status():
    """Статус системы: доступность провайдеров, модели, агенты."""
    from core.model_registry import refresh

    registry = refresh()

    providers_status = {}
    for pid, info in registry.items():
        providers_status[pid] = {
            "available": info.is_available,
            "free_models": len([m for m in info.models if m.is_free]),
        }

    return JSONResponse({
        "status": "ok",
        "version": "2.0.0",
        "providers": providers_status,
        "ai_mode": os.getenv("AI_MODE", "local"),
    })


# ══════════════════════════════════════════
#  MCP SERVER ENDPOINTS
# ══════════════════════════════════════════

@app.get("/api/mcp/servers")
async def get_mcp_servers():
    """Получить список MCP серверов"""
    config_path = BASE_DIR / "config" / "mcp_servers.json"
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return JSONResponse({"servers": data.get("servers", [])})
    return JSONResponse({"servers": []})

@app.post("/api/mcp/reload")
async def reload_mcp_servers():
    """Перезагрузить MCP серверы"""
    try:
        from core.mcp_server import mcp_manager
        mcp_manager.disconnect_all()
        mcp_manager._load_config()
        await mcp_manager.connect_all()
        tools_count = len(mcp_manager.get_all_tools())
        return JSONResponse({
            "status": "reloaded",
            "servers": len(mcp_manager.servers),
            "tools": tools_count
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/mcp/call")
async def call_mcp_tool(request: Request):
    """Вызвать инструмент на MCP сервере"""
    body = await request.json()
    server_name = body.get("server")
    tool_name = body.get("tool")
    arguments = body.get("arguments", {})
    
    try:
        result = await mcp_manager.call_tool(server_name, tool_name, arguments)
        return JSONResponse({"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/health/providers")
async def get_providers_health():
    """Получить статистику здоровья провайдеров"""
    try:
        from core.model_router import ModelRouter
        router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
        health_stats = router.health.get_stats()
        return JSONResponse({
            "status": "ok",
            "health": health_stats,
            "priority": router.priority
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ══════════════════════════════════════════
#  MODEL TESTING & AUTO-SELECT API
# ══════════════════════════════════════════

class TestModelRequest(BaseModel):
    model_id: str
    provider: str = "openrouter"

@app.post("/api/models/test")
async def test_model(req: TestModelRequest):
    """Протестировать модель — проверить что она живая"""
    import time
    try:
        from core.model_router import ModelRouter
        router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))

        start = time.time()
        response = router.generate(
            prompt="Reply with just 'ok'",
            model=req.model_id,
            provider=req.provider,
        )
        elapsed = time.time() - start

        return JSONResponse({
            "status": "ok",
            "model_id": req.model_id,
            "latency_ms": round(elapsed * 1000),
            "response": response[:100] if response else None,
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "model_id": req.model_id,
            "error": str(e)[:200],
        }, status_code=200)


class AutoSelectRequest(BaseModel):
    provider: str = "openrouter"

@app.post("/api/models/auto-select")
async def auto_select_models(req: AutoSelectRequest):
    """Автоматически выбрать лучшие живые модели для каждого агента"""
    import asyncio
    from core.model_registry import get_free_models

    # Рекомендации по ролям
    role_recommendations = {
        "teamlead": {"prefer": ["reasoning", "general"], "min_context": 32000},
        "architect": {"prefer": ["reasoning", "strong"], "min_context": 64000},
        "backend": {"prefer": ["coding", "reasoning"], "min_context": 32000},
        "frontend": {"prefer": ["coding", "fast"], "min_context": 32000},
        "devops": {"prefer": ["general", "coding"], "min_context": 16000},
        "tester": {"prefer": ["coding", "fast"], "min_context": 16000},
        "documentalist": {"prefer": ["general", "fast"], "min_context": 16000},
    }

    # Получаем все бесплатные модели провайдера
    all_models = get_free_models(provider=req.provider, min_context=8000)

    # Группируем по strength
    by_strength = {}
    for m in all_models:
        s = m.get("strength", "general")
        if s not in by_strength:
            by_strength[s] = []
        by_strength[s].append(m)

    # Для каждой роли выбираем лучшую модель
    selections = {}
    used_models = set()

    for role, rec in role_recommendations.items():
        candidates = []
        for strength in rec["prefer"]:
            for m in by_strength.get(strength, []):
                if m["context_length"] >= rec["min_context"]:
                    candidates.append(m)

        # Сортируем: сначала по контексту (больше лучше), потом по имени
        candidates.sort(key=lambda x: (-x.get("context_length", 0), x.get("id", "")))

        # Выбираем первую уникальную модель
        chosen = None
        for c in candidates:
            if c["id"] not in used_models:
                chosen = c
                used_models.add(c["id"])
                break

        # Если уникальная не найдена — берём лучшую из кандидатов
        if not chosen and candidates:
            chosen = candidates[0]

        if chosen:
            selections[role] = {
                "model_id": chosen["id"],
                "name": chosen.get("name", chosen["id"]),
                "context_length": chosen.get("context_length", 0),
                "strength": chosen.get("strength", "general"),
            }

    return JSONResponse({
        "provider": req.provider,
        "selections": selections,
        "total_models_tested": len(all_models),
    })


# ══════════════════════════════════════════
#  KANBAN API ENDPOINTS
# ══════════════════════════════════════════

@app.get("/api/kanban/tasks")
async def get_kanban_tasks(project_id: int = None, column_id: str = None):
    """Получить задачи канбан"""
    from core.database import Database
    db = Database()
    tasks = db.get_kanban_tasks(project_id=project_id, column_id=column_id)
    return JSONResponse({"tasks": tasks, "total": len(tasks)})


class CreateKanbanTaskRequest(BaseModel):
    agent: str
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    column_id: Optional[str] = "todo"
    project_id: Optional[int] = None


@app.post("/api/kanban/tasks")
async def create_kanban_task(req: CreateKanbanTaskRequest):
    """Создать задачу канбан"""
    db = Database()
    task_id = db.create_kanban_task(
        agent=req.agent,
        title=req.title,
        description=req.description,
        priority=req.priority,
        column_id=req.column_id,
        project_id=req.project_id,
    )
    return JSONResponse({"id": task_id, "status": "created"})


class UpdateKanbanTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    column_id: Optional[str] = None
    position: Optional[int] = None


@app.patch("/api/kanban/tasks/{task_id}")
async def update_kanban_task(task_id: int, req: UpdateKanbanTaskRequest):
    """Обновить задачу канбан"""
    db = Database()
    updates = {k: v for k, v in req.dict().items() if v is not None}
    success = db.update_kanban_task(task_id, **updates)
    return JSONResponse({"status": "updated" if success else "no_changes"})


@app.delete("/api/kanban/tasks/{task_id}")
async def delete_kanban_task(task_id: int):
    """Удалить задачу канбан"""
    db = Database()
    db.delete_kanban_task(task_id)
    return JSONResponse({"status": "deleted"})


# ══════════════════════════════════════════
#  WEBHOOKS API
# ══════════════════════════════════════════


@app.get("/api/webhooks")
async def get_webhook_subscriptions():
    """Получить все подписки на webhooks"""
    return JSONResponse({
        "subscriptions": webhook_manager.get_subscriptions(),
        "stats": webhook_manager.get_stats(),
    })


class CreateWebhookRequest(BaseModel):
    name: str
    url: str
    events: List[str]
    secret: Optional[str] = None


@app.post("/api/webhooks")
async def create_webhook_subscription(req: CreateWebhookRequest):
    """Создать подписку на webhook"""
    sub_id = webhook_manager.create_subscription(
        name=req.name, url=req.url, events=req.events, secret=req.secret
    )
    return JSONResponse({"id": sub_id, "status": "created"})


@app.delete("/api/webhooks/{sub_id}")
async def delete_webhook_subscription(sub_id: str):
    """Удалить подписку на webhook"""
    success = webhook_manager.delete_subscription(sub_id)
    return JSONResponse({"status": "deleted" if success else "not_found"})


@app.post("/api/webhooks/{sub_id}/receive")
async def receive_webhook_event(sub_id: str, request: Request):
    """Принять webhook event (для GitHub/GitLab/внешних сервисов)"""
    body = await request.json()
    payload = json.dumps(body).encode()
    
    # Get signature from headers (GitHub: X-Hub-Signature-256, GitLab: X-Gitlab-Token)
    signature = (
        request.headers.get("X-Hub-Signature-256") or
        request.headers.get("X-Gitlab-Token") or
        ""
    )
    event_type = (
        request.headers.get("X-GitHub-Event") or
        request.headers.get("X-Gitlab-Event") or
        body.get("event_type", "unknown")
    )
    source_ip = request.client.host if request.client else ""
    
    result = webhook_manager.receive_event(
        sub_id=sub_id, event_type=event_type, payload=body,
        signature=signature, source_ip=source_ip
    )
    return JSONResponse(result)


@app.get("/api/webhooks/events")
async def get_webhook_events(limit: int = 20):
    """Получить последние webhook events"""
    return JSONResponse({"events": webhook_manager.get_recent_events(limit)})


@app.get("/api/webhooks/stats")
async def get_webhook_stats():
    """Статистика webhooks"""
    return JSONResponse(webhook_manager.get_stats())


# ══════════════════════════════════════════
#  ANALYTICS API
# ══════════════════════════════════════════

from core.analytics import analytics_manager


@app.get("/api/analytics")
async def get_analytics(hours: int = 24):
    """Получить аналитику использования"""
    return JSONResponse(analytics_manager.get_summary(hours))


@app.get("/api/analytics/dashboard")
async def get_analytics_dashboard():
    """Получить данные для дашборда аналитики"""
    return JSONResponse(analytics_manager.get_dashboard_data())


@app.get("/api/analytics/hourly")
async def get_analytics_hourly(hours: int = 24):
    """Получить почасовую разбивку"""
    return JSONResponse({"hourly": analytics_manager.get_hourly_breakdown(hours)})


class RecordMetricRequest(BaseModel):
    agent: str
    model: str = "unknown"
    provider: str = "unknown"
    success: bool = True
    duration_ms: float = 0
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    error: Optional[str] = None


@app.post("/api/analytics/record")
async def record_analytics_metric(req: RecordMetricRequest):
    """Записать метрику вызова агента"""
    from core.analytics import AgentCallMetric
    metric = AgentCallMetric(
        agent=req.agent, model=req.model, provider=req.provider,
        success=req.success, duration_ms=req.duration_ms,
        tokens_input=req.tokens_input, tokens_output=req.tokens_output,
        cost=req.cost, error=req.error,
    )
    analytics_manager.record_call(metric)
    return JSONResponse({"status": "recorded"})


# ══════════════════════════════════════════
#  i18n API
# ══════════════════════════════════════════

from core.i18n import t as translate, get_available_languages, set_default_lang


@app.get("/api/i18n")
async def get_translations(lang: str = "ru"):
    """Получить переводы для языка"""
    from core.i18n import _TRANSLATIONS
    return JSONResponse({
        "lang": lang,
        "translations": _TRANSLATIONS.get(lang, {}),
        "available": get_available_languages(),
    })


@app.get("/api/i18n/languages")
async def get_languages():
    """Получить список доступных языков"""
    return JSONResponse({"languages": get_available_languages()})


# ══════════════════════════════════════════
#  CODERCHAT API
# ══════════════════════════════════════════

# Store active chat sessions
chat_sessions: Dict[str, Dict[str, Any]] = {}


class InitChatRequest(BaseModel):
    project_path: Optional[str] = None
    project_name: Optional[str] = None


@app.post("/api/coderchat/init")
async def init_coder_chat(req: InitChatRequest):
    """Инициализировать CoderChat сессию"""
    from core.coder_chat import CoderChatAgent
    from core.model_router import ModelRouter

    session_id = f"chat_{int(time.time())}"

    # Default project path — use ~/projects to avoid permission issues
    project_path = req.project_path or os.path.expanduser("~/projects/coderchat_default")
    project_name = req.project_name or "coderchat_project"

    # Create agent
    router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
    agent = CoderChatAgent(model_router=router)
    try:
        agent.init_project(project_path, project_name)
    except Exception as e:
        return JSONResponse({"error": f"Failed to init project: {e}"}, status_code=500)
    
    chat_sessions[session_id] = {
        "agent": agent,
        "project_path": project_path,
        "project_name": project_name,
        "created_at": datetime.now().isoformat(),
    }
    
    return JSONResponse({
        "session_id": session_id,
        "project_path": project_path,
        "project_name": project_name,
        "file_tree": agent.get_file_tree_display().split('\n')[:30],
        "tech_stack": agent.project.tech_stack if agent.project else [],
    })


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/coderchat/message")
async def send_chat_message(req: ChatMessageRequest):
    """Отправить сообщение в чат"""
    session = chat_sessions.get(req.session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    agent: CoderChatAgent = session["agent"]
    result = await agent.process_message(req.message)
    
    return JSONResponse(result)


@app.get("/api/coderchat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Получить историю чата"""
    session = chat_sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    agent: CoderChatAgent = session["agent"]
    return JSONResponse({
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in agent.messages
        ],
        "stats": agent.get_stats(),
    })


@app.get("/api/coderchat/files/{session_id}")
async def get_project_files(session_id: str):
    """Получить структуру файлов проекта"""
    session = chat_sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    agent: CoderChatAgent = session["agent"]
    return JSONResponse({
        "file_tree": agent.get_file_tree_display().split('\n'),
        "project_path": session["project_path"],
    })


@app.get("/api/coderchat/file/{session_id}")
async def read_project_file(session_id: str, path: str):
    """Прочитать файл проекта"""
    session = chat_sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    agent: CoderChatAgent = session["agent"]
    content = agent.read_project_file(path)
    
    if content is None:
        return JSONResponse({"error": "File not found"}, status_code=404)
    
    return JSONResponse({"path": path, "content": content})


@app.delete("/api/coderchat/{session_id}")
async def delete_chat_session(session_id: str):
    """Удалить сессию чата"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return JSONResponse({"status": "deleted"})


# ══════════════════════════════════════════
#  PROMPT ARCHITECT API
# ══════════════════════════════════════════

pa_sessions: Dict[str, Dict[str, Any]] = {}


class PAInitRequest(BaseModel):
    pass  # No params needed — fresh start each time


class PAMessageRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/promptarchitect/init")
async def init_prompt_architect(req: PAInitRequest):
    """Инициализировать сессию Prompt Architect."""
    from core.prompt_architect import PromptArchitectAgent
    from core.model_router import ModelRouter

    session_id = f"pa_{int(time.time())}"

    router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
    agent = PromptArchitectAgent(model_router=router)

    pa_sessions[session_id] = {
        "agent": agent,
        "created_at": datetime.now().isoformat(),
    }

    return JSONResponse({
        "session_id": session_id,
        "welcome": "👋 Привет. Я Prompt Architect.\n\nМоя работа — помочь тебе научиться превращать хаотичные мысли в чёткие задачи для ИИ-агентов.\n\nС чего начнём?\n  А) Объясни мне что такое промт и зачем это вообще\n  Б) У меня есть идея — помоги оформить в нормальную задачу\n  В) Вот мой промт — скажи что с ним не так",
    })


@app.post("/api/promptarchitect/message")
async def send_pa_message(req: PAMessageRequest):
    """Отправить сообщение в Prompt Architect."""
    session = pa_sessions.get(req.session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    agent: PromptArchitectAgent = session["agent"]
    result = await agent.process_message(req.message)

    return JSONResponse(result)


@app.get("/api/promptarchitect/history/{session_id}")
async def get_pa_history(session_id: str):
    """Получить историю диалога."""
    session = pa_sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    agent: PromptArchitectAgent = session["agent"]
    return JSONResponse({
        "messages": agent.get_history(),
        "stats": agent.get_stats(),
    })


@app.post("/api/promptarchitect/clear/{session_id}")
async def clear_pa_history(session_id: str):
    """Очистить историю (начать новый диалог)."""
    session = pa_sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    agent: PromptArchitectAgent = session["agent"]
    agent.clear_history()
    return JSONResponse({"status": "cleared"})


@app.delete("/api/promptarchitect/{session_id}")
async def delete_pa_session(session_id: str):
    """Удалить сессию Prompt Architect."""
    if session_id in pa_sessions:
        del pa_sessions[session_id]
    return JSONResponse({"status": "deleted"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_ui.app:app", host="0.0.0.0", port=8000, reload=False)
