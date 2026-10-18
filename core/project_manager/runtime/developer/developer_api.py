"""
Developer API — FastAPI endpoints for Developer Mode.

Endpoints:
    POST /api/developer/create_project — create a new project brain
    POST /api/developer/message        — send a message (understanding phase)
    GET  /api/developer/project/{id}   — get project brain state
    POST /api/developer/understand     — analyze a request (understanding phase)
    GET  /api/developer/projects       — list all projects
    POST /api/developer/snapshot       — create a brain snapshot
    POST /api/developer/orchestrate    — full orchestration flow
    GET  /api/developer/timeline       — get event timeline
    GET  /api/developer/agents         — list agents
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from loguru import logger

from .orchestrator import Orchestrator
from .task_executor import TaskExecutor, ExecutionResult
from .approval_runtime import ApprovalRuntime
from .patch_engine import PatchEngine, Patch, PatchStatus, RiskLevel
from .repo_scanner import RepoScanner
from .knowledge_index import KnowledgeIndex
from .workspace_runtime import WorkspaceRuntime
from .execution_sandbox import ExecutionSandbox, SandboxPolicy
from .developer_terminal import DeveloperTerminal
from .project_brain import ProjectBrain, RuntimeState, brain_to_dict
from .brain_store import BrainStore
from .understanding_engine import UnderstandingEngine
from .task_contracts import TaskContract, TaskContractBuilder
from .context_layers import ContextLayers


# ── Router ──

router = APIRouter(prefix="/api/developer", tags=["developer"])


# ── Shared instances ──

_store = BrainStore()
_engine = UnderstandingEngine()


# ── Request/Response models ──

class CreateProjectRequest(BaseModel):
    project_id: str = ""
    project_name: str = ""
    project_summary: str = ""


class MessageRequest(BaseModel):
    project_id: str = ""
    message: str = ""


class UnderstandRequest(BaseModel):
    message: str = ""
    project_id: str = ""


class CreateTaskRequest(BaseModel):
    project_id: str = ""
    title: str = ""
    objective: str = ""
    allowed_files: List[str] = []
    owner_agent: str = ""
    priority: str = "medium"


class SnapshotResponse(BaseModel):
    project_id: str
    snapshot_path: str
    timestamp: str


# ── Endpoints ──

@router.post("/create_project")
async def create_project(req: CreateProjectRequest) -> Dict[str, Any]:
    """Create a new project brain."""
    project_id = req.project_id or req.project_name.lower().replace(" ", "-")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id or project_name required")

    if _store.brain_exists(project_id):
        raise HTTPException(status_code=409, detail=f"Project '{project_id}' already exists")

    brain = _store.create_brain(project_id, req.project_name or project_id)
    if req.project_summary:
        brain.project_summary = req.project_summary
        _store.save_brain(brain)

    logger.info(f"Developer project created: {project_id}")
    return {
        "status": "created",
        "project_id": project_id,
        "brain": brain_to_dict(brain),
    }


@router.post("/message")
async def developer_message(req: MessageRequest) -> Dict[str, Any]:
    """
    Send a message in Developer Mode.

    This triggers the understanding phase.
    The system analyzes the request BEFORE any execution.
    """
    if not req.message:
        raise HTTPException(status_code=400, detail="message is required")

    # Load project brain if specified
    brain = None
    project_context = None
    if req.project_id:
        brain = _store.load_brain(req.project_id)
        if brain:
            project_context = brain_to_dict(brain)

    # Run understanding engine
    understanding = _engine.analyze(req.message, project_context)

    # Update brain if exists
    if brain:
        brain.set_runtime_state(RuntimeState.UNDERSTANDING)
        brain.current_focus = understanding.objective
        _store.save_brain(brain)

    return {
        "status": "understood",
        "understanding": {
            "objective": understanding.objective,
            "interpreted_goal": understanding.interpreted_goal,
            "affected_areas": understanding.affected_areas,
            "required_changes": understanding.required_changes,
            "dependencies": understanding.dependencies,
            "risks": understanding.risks,
            "unknowns": understanding.unknowns,
            "clarification_questions": understanding.clarification_questions,
            "execution_hypothesis": understanding.execution_hypothesis,
            "estimated_complexity": understanding.estimated_complexity,
            "suggested_agent": understanding.suggested_agent,
            "is_ready": understanding.is_ready,
            "formatted": understanding.format_for_display(),
        },
        "project_id": req.project_id,
        "can_execute": understanding.is_ready,
    }


@router.post("/understand")
async def understand_request(req: UnderstandRequest) -> Dict[str, Any]:
    """
    Analyze a request without side effects.
    Pure understanding — no brain updates.
    """
    if not req.message:
        raise HTTPException(status_code=400, detail="message is required")

    project_context = None
    if req.project_id:
        brain = _store.load_brain(req.project_id)
        if brain:
            project_context = brain_to_dict(brain)

    understanding = _engine.analyze(req.message, project_context)

    return {
        "status": "analyzed",
        "understanding": {
            "objective": understanding.objective,
            "interpreted_goal": understanding.interpreted_goal,
            "affected_areas": understanding.affected_areas,
            "risks": understanding.risks,
            "unknowns": understanding.unknowns,
            "clarification_questions": understanding.clarification_questions,
            "execution_hypothesis": understanding.execution_hypothesis,
            "estimated_complexity": understanding.estimated_complexity,
            "suggested_agent": understanding.suggested_agent,
            "is_ready": understanding.is_ready,
            "formatted": understanding.format_for_display(),
        },
    }


@router.get("/project/{project_id}")
async def get_project(project_id: str) -> Dict[str, Any]:
    """Get project brain state."""
    brain = _store.load_brain(project_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    return {
        "status": "ok",
        "brain": brain_to_dict(brain),
        "token_usage": _build_token_usage(brain),
    }


@router.get("/projects")
async def list_projects() -> Dict[str, Any]:
    """List all developer projects."""
    brains = _store.list_brains()
    return {
        "status": "ok",
        "projects": brains,
        "count": len(brains),
    }


@router.post("/snapshot/{project_id}")
async def create_snapshot(project_id: str) -> Dict[str, Any]:
    """Create a brain snapshot."""
    snap_path = _store.snapshot_brain(project_id)
    if not snap_path:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    return {
        "status": "snapshotted",
        "project_id": project_id,
        "snapshot_path": snap_path,
    }


@router.post("/task")
async def create_task(req: CreateTaskRequest) -> Dict[str, Any]:
    """Create a task contract for a project."""
    if not req.title or not req.objective:
        raise HTTPException(status_code=400, detail="title and objective are required")

    brain = _store.load_brain(req.project_id) if req.project_id else None

    builder = TaskContractBuilder(req.title, req.objective)
    builder.with_agent(req.owner_agent or "teamlead")
    builder.with_priority(req.priority)
    if req.allowed_files:
        builder.with_allowed_files(req.allowed_files)

    contract = builder.build()

    if brain:
        brain.add_task(req.title, req.objective)
        _store.save_brain(brain)

    return {
        "status": "created",
        "contract": {
            "task_id": contract.task_id,
            "title": contract.title,
            "objective": contract.objective,
            "owner_agent": contract.owner_agent,
            "priority": contract.priority,
            "status": contract.status,
            "is_valid": contract.is_valid(),
            "validation_issues": contract.validate(),
        },
    }


@router.get("/context/{project_id}")
async def get_context(project_id: str) -> Dict[str, Any]:
    """Get layered context for a project."""
    brain = _store.load_brain(project_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    layers = ContextLayers()
    layers.set_system_identity(
        "AI Team System Developer Mode — AI Engineering Workspace. "
        "Human controls. AI assists. No autonomous changes."
    )
    layers.set_project_brain(brain_to_dict(brain))

    return {
        "status": "ok",
        "context": layers.build_context(),
        "token_usage": layers.get_token_usage(),
        "layers": [l.name for l in layers.get_active_layers()],
    }


# ── Helpers ──

def _build_token_usage(brain: ProjectBrain) -> Dict[str, Any]:
    """Estimate token usage for a brain state."""
    brain_dict = brain_to_dict(brain)
    layers = ContextLayers()
    layers.set_system_identity("AI Team System Developer Mode")
    layers.set_project_brain(brain_dict)
    return layers.get_token_usage()


# ── Shared instances ──

_approval_runtime = ApprovalRuntime()


def approvals_runtime() -> ApprovalRuntime:
    """Единая очередь подтверждений на процесс.

    Панель «Подтверждения» и правки агентов обязаны видеть одни и те же запросы:
    раньше сборка проекта создавала собственный ApprovalRuntime, и запросы
    уходили в объект, который никто не мог открыть.
    """
    return _approval_runtime


def patch_engine() -> PatchEngine:
    """Единый движок патчей на процесс.

    Сборка проекта создавала свой PatchEngine — и панель не находила по номеру
    ни одного патча: применение отвечало «успех», не записав ничего.
    """
    return _patch_engine
_patch_engine = PatchEngine()
_workspace_runtime = WorkspaceRuntime()
_knowledge_index = KnowledgeIndex()
_terminal = DeveloperTerminal()


# ── Execution endpoints ──

class ExecuteTaskRequest(BaseModel):
    project_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    title: str = ""
    objective: str = ""
    allowed_files: List[str] = []
    forbidden_files: List[str] = []


class ApprovalActionRequest(BaseModel):
    request_id: str = ""
    action: str = ""
    comments: str = ""


@router.post("/execute")
async def execute_task(req: ExecuteTaskRequest) -> Dict[str, Any]:
    """Execute a task: contract → workspace → patch → validation → approval queue."""
    if not _dev_exec_enabled():
        raise HTTPException(
            status_code=403,
            detail="Исполнение задач выключено. Включи AITEAM_DEV_EXEC=1 в .env, если понимаешь риск.",
        )
    if not req.title or not req.objective:
        raise HTTPException(status_code=400, detail="title and objective required")

    project_id = req.project_id or "default"
    orch = _get_orchestrator(project_id)
    brain = orch.brain
    if not brain:
        raise HTTPException(status_code=404, detail="Project brain not initialized")

    builder = TaskContractBuilder(req.title, req.objective)
    builder.with_agent(req.agent_id or "backend")
    if req.allowed_files:
        builder.with_allowed_files(req.allowed_files)
    if req.forbidden_files:
        builder.with_forbidden_files(req.forbidden_files)
    contract = builder.build()

    executor = TaskExecutor(
        project_brain=brain,
        workspace_runtime=_workspace_runtime,
        patch_engine=_patch_engine,
        approval_runtime=_approval_runtime,
        knowledge_index=_knowledge_index,
    )

    # Подключаем модель: правку предлагает она, а генератор проверяет её по файлам.
    # Без модели исполнитель возвращается к прежнему пути — роут не падает.
    try:
        from core.model_router import ModelRouter

        router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
        executor._model_call = lambda prompt: router.generate(prompt=prompt, agent="backend")
    except Exception as exc:  # noqa: BLE001 — недоступная модель не должна ломать запуск
        logger.warning(f"Модель для генерации патча недоступна: {exc}")

    result = executor.execute_task(contract)

    return {
        "status": result.status,
        "result": result.to_dict(),
        "approval_queue_size": _approval_runtime.get_queue_size(),
    }


@router.get("/approvals")
async def get_approval_queue() -> Dict[str, Any]:
    """Get all pending approval requests."""
    pending = _approval_runtime.get_pending()
    return {
        "status": "ok",
        "pending": [r.to_dict() for r in pending],
        "count": len(pending),
    }


@router.post("/approvals/action")
async def approval_action(req: ApprovalActionRequest) -> Dict[str, Any]:
    """Approve or reject a pending patch."""
    if req.action == "approve":
        success = _approval_runtime.approve(req.request_id, comments=req.comments)
        applied = False
        note = ""
        if success:
            for h in _approval_runtime.get_history():
                if h.request_id != req.request_id:
                    continue
                patch = _patch_engine.get_patch(h.patch_id)
                if not patch:
                    # Движок мог не знать этот патч — но содержимое лежит в самой заявке.
                    contents = getattr(h, "files_content", {}) or {}
                    if contents:
                        from pathlib import Path as _Path

                        for file_path, content in contents.items():
                            target = _Path(file_path)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_text(content, encoding="utf-8")
                            applied = True
                        note = "записано из заявки"
                        break
                    note = "патч недоступен: он создан в другом экземпляре движка, файлы не записаны"
                    break
                # Проверка обязана быть здесь: без неё применение молча отказывает.
                passed, errors, _ = _patch_engine.validate_patch(patch)
                patch.validation_passed = passed
                if not passed:
                    note = "патч не прошёл проверку: " + "; ".join(errors[:2])
                    break
                patch.approved = True
                applied = bool(_patch_engine.apply_patch(patch))
                if not applied:
                    note = "применение не удалось — правка не записана"
                break
        return {
            "status": "approved",
            "success": success and applied,
            "applied": applied,
            "note": note,
        }
    elif req.action == "reject":
        success = _approval_runtime.reject(req.request_id, comments=req.comments)
        return {"status": "rejected", "success": success}
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")


@router.get("/repo/scan")
async def scan_repo(project_root: str = ".") -> Dict[str, Any]:
    """Scan the project repository."""
    scanner = RepoScanner(project_root)
    repo_map = scanner.scan()
    return {
        "status": "ok",
        "repo_map": {
            "total_files": repo_map.total_files,
            "total_lines": repo_map.total_lines,
            "languages": repo_map.languages,
            "frameworks": repo_map.frameworks,
            "entrypoints": repo_map.entrypoints,
            "has_docker": repo_map.has_docker,
            "has_ci": repo_map.has_ci,
        },
        "summary": scanner.get_summary(repo_map),
    }


@router.get("/knowledge")
async def get_knowledge() -> Dict[str, Any]:
    """Get the knowledge index."""
    return {
        "status": "ok",
        "knowledge": _knowledge_index.build_context(),
        "entries": _knowledge_index.to_dict()["entries"],
    }


def _dev_exec_enabled() -> bool:
    """
    Опасные роуты (терминал и исполнение задач) по умолчанию выключены.

    Они запускают команды и патчи от имени пользователя, поэтому включаются
    осознанно: AITEAM_DEV_EXEC=1 в .env.
    """
    return os.getenv("AITEAM_DEV_EXEC", "0").strip().lower() in ("1", "true", "yes", "on")


@router.post("/terminal")
async def terminal_command(command: str = "") -> Dict[str, Any]:
    """Execute a safe terminal command (только при AITEAM_DEV_EXEC=1)."""
    if not _dev_exec_enabled():
        raise HTTPException(
            status_code=403,
            detail="Терминал выключен. Включи AITEAM_DEV_EXEC=1 в .env, если понимаешь риск.",
        )
    if not command:
        raise HTTPException(status_code=400, detail="command is required")
    result = _terminal.execute(command)
    return {
        "status": "ok" if result.allowed else "blocked",
        "allowed": result.allowed,
        "block_reason": result.block_reason,
        "output": result.output[:1000] if result.output else "",
        "exit_code": result.exit_code,
    }


# ── Orchestration state (per-project) ──

_orchestrators: Dict[str, Orchestrator] = {}


def _get_orchestrator(project_id: str) -> Orchestrator:
    """Get or create an orchestrator for a project."""
    if project_id not in _orchestrators:
        orch = Orchestrator(project_id=project_id)
        orch.initialize(project_id)
        _orchestrators[project_id] = orch
    return _orchestrators[project_id]


# ── Orchestration endpoints ──

class OrchestrateRequest(BaseModel):
    project_id: str = ""
    message: str = ""


@router.post("/orchestrate")
async def orchestrate(req: OrchestrateRequest) -> Dict[str, Any]:
    """
    Full orchestration flow: understanding → planning → task assignment.

    This is the main endpoint for Developer Mode execution.
    Currently: PLANNING ONLY. No actual code execution.
    """
    if not req.message:
        raise HTTPException(status_code=400, detail="message is required")

    project_id = req.project_id or "default"
    orch = _get_orchestrator(project_id)

    result = orch.process_message(req.message)
    return result


@router.get("/timeline")
async def get_timeline(project_id: str = "", limit: int = 20) -> Dict[str, Any]:
    """Get the event timeline for a project."""
    project_id = project_id or "default"
    orch = _get_orchestrator(project_id)
    timeline = orch.get_timeline(limit=limit)
    return {
        "status": "ok",
        "timeline": timeline,
        "count": len(timeline),
    }


@router.get("/agents")
async def list_agents(project_id: str = "") -> Dict[str, Any]:
    """List all registered agents."""
    project_id = project_id or "default"
    orch = _get_orchestrator(project_id)
    agents = orch.get_agent_status()
    return {
        "status": "ok",
        "agents": agents,
        "count": len(agents),
    }


@router.get("/status")
async def get_orchestrator_status(project_id: str = "") -> Dict[str, Any]:
    """Get the current orchestrator status."""
    project_id = project_id or "default"
    orch = _get_orchestrator(project_id)
    return {
        "status": "ok",
        "orchestrator": orch.status.to_dict(),
        "plan": orch.get_plan_status(),
    }
