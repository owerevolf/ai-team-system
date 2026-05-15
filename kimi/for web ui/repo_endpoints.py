"""
Repo Mode API Endpoints for Web UI.

Add these endpoints to your FastAPI app (web_ui/app.py).
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio

# These will be imported from your existing modules
# from core.main import AITeamSystem
# from core.project_manager import ProjectManager

router = APIRouter(prefix="/api/repo", tags=["repo"])

# Global reference to orchestrator (set during startup)
orchestrator = None


def set_orchestrator(orch):
    """Set the orchestrator instance."""
    global orchestrator
    orchestrator = orch


# ═══════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class OpenProjectRequest(BaseModel):
    path: str  # Absolute path or "github:owner/repo"
    level: str = "advanced"  # zero | beginner | advanced


class ExploreRequest(BaseModel):
    question: str  # What user wants to know
    level: str = "advanced"


class ModifyRequest(BaseModel):
    task: str  # What to do (e.g., "Add Stripe payments")
    level: str = "advanced"
    auto_apply: bool = False  # If True, apply without confirmation


class ProjectResponse(BaseModel):
    status: str
    project_path: Optional[str]
    stats: Optional[Dict[str, Any]]
    message: str


class ExploreResponse(BaseModel):
    status: str
    answer: str
    files_referenced: List[str]
    level: str


class ModifyResponse(BaseModel):
    status: str
    plan: Optional[str]
    changes: Optional[List[Dict]]
    requires_confirmation: bool
    message: str


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/open", response_model=ProjectResponse)
async def open_project(request: OpenProjectRequest):
    """
    Open an existing project for exploration or modification.

    - Scans and indexes the project
    - Returns project stats
    - Initializes ProjectManager
    """
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    try:
        # Handle GitHub URLs
        if request.path.startswith("github:"):
            # Clone repository first
            repo_path = request.path.replace("github:", "")
            # You would implement git clone here
            # For now, return error
            return ProjectResponse(
                status="error",
                project_path=None,
                stats=None,
                message="GitHub clone not yet implemented. Use local path."
            )

        path = Path(request.path)
        if not path.exists():
            return ProjectResponse(
                status="error",
                project_path=None,
                stats=None,
                message=f"Path not found: {request.path}"
            )

        # Open project via orchestrator
        result = orchestrator.open_project(str(path))

        return ProjectResponse(
            status="success",
            project_path=result["project_path"],
            stats=result["stats"],
            message=f"Project indexed: {result['stats']['total_files']} files"
        )

    except Exception as e:
        return ProjectResponse(
            status="error",
            project_path=None,
            stats=None,
            message=str(e)
        )


@router.get("/status")
async def get_status():
    """Get current project indexing status."""
    if orchestrator is None or orchestrator.project_manager is None:
        return {
            "status": "no_project",
            "message": "No project is currently open"
        }

    pm = orchestrator.project_manager
    stats = pm.get_stats()

    return {
        "status": "indexed" if pm.is_indexed else "indexing",
        "project_path": str(pm.project_path),
        "stats": stats
    }


@router.post("/explore", response_model=ExploreResponse)
async def explore_project(request: ExploreRequest):
    """
    Explore project and answer user questions.

    Uses Repo Explorer agent with ProjectManager context.
    """
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open. Call /open first.")

    try:
        # Get project summary from PM
        pm = orchestrator.project_manager
        summary = pm.get_repo_summary(level=request.level)

        # If user asks specific question, query PM
        if request.question and request.question.lower() not in ["what is this", "explain", "overview"]:
            context = pm.query(
                agent="repo_explorer",
                question=request.question,
                max_tokens=6000
            )
        else:
            context = summary

        # Run Repo Explorer agent
        # This would use your existing agent_manager.run_agent()
        # For now, return the PM context directly

        return ExploreResponse(
            status="success",
            answer=context,
            files_referenced=[],  # Would be populated by agent
            level=request.level
        )

    except Exception as e:
        return ExploreResponse(
            status="error",
            answer=f"Error: {str(e)}",
            files_referenced=[],
            level=request.level
        )


@router.post("/modify", response_model=ModifyResponse)
async def modify_project(request: ModifyRequest):
    """
    Modify existing project.

    Steps:
    1. TeamLead creates plan
    2. PM validates plan
    3. Agents execute modifications
    4. Tests run
    5. Git commit
    """
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open. Call /open first.")

    try:
        # Create snapshot before modifications
        pm = orchestrator.project_manager
        snapshot_id = pm.create_snapshot()

        # Run TeamLead to create plan
        # This would use your existing orchestrator flow
        # For now, return plan for confirmation

        plan = f"""
## Modification Plan: {request.task}

### 1. Analysis
ProjectManager will analyze impact on existing code.

### 2. Plan
TeamLead will create detailed task breakdown.

### 3. Implementation
Agents will modify code safely.

### 4. Validation
Tests will run to ensure nothing breaks.

### 5. Commit
Changes will be committed to git.

### Safety
- Snapshot created: {snapshot_id}
- Can rollback if needed
- All changes in separate branch
        """

        return ModifyResponse(
            status="pending",
            plan=plan,
            changes=None,
            requires_confirmation=not request.auto_apply,
            message="Plan created. Confirm to proceed."
        )

    except Exception as e:
        return ModifyResponse(
            status="error",
            plan=None,
            changes=None,
            requires_confirmation=False,
            message=str(e)
        )


@router.post("/modify/confirm")
async def confirm_modification(task: str):
    """Confirm and execute modification plan."""
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    # This would trigger the full agent workflow
    # Similar to create_project but with PM context

    return {
        "status": "started",
        "task": task,
        "message": "Modification started. Check status endpoint for progress."
    }


@router.post("/rollback")
async def rollback_changes(snapshot_id: Optional[str] = None):
    """Rollback to previous snapshot."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    try:
        pm = orchestrator.project_manager
        success = pm.rollback(snapshot_id)

        if success:
            return {
                "status": "success",
                "message": f"Rolled back to snapshot: {snapshot_id or 'latest'}"
            }
        else:
            return {
                "status": "error",
                "message": "Rollback failed"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/tree")
async def get_file_tree(max_depth: int = 3):
    """Get project file tree."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    tree = pm.get_file_tree(max_depth=max_depth)

    return {
        "status": "success",
        "tree": tree,
        "project_path": str(pm.project_path)
    }


@router.get("/file/{file_path:path}")
async def get_file_content(file_path: str):
    """Get content of a specific file."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    content = pm.get_file_content(file_path)

    if content is None:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    return {
        "status": "success",
        "file_path": file_path,
        "content": content,
        "size": len(content)
    }


@router.get("/search")
async def search_symbols(name: str):
    """Search for symbols across the project."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    results = pm.search_symbols(name)

    return {
        "status": "success",
        "query": name,
        "results": results,
        "count": len(results)
    }


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET FOR REAL-TIME UPDATES (optional)
# ═══════════════════════════════════════════════════════════════

from fastapi import WebSocket

@router.websocket("/ws")
async def repo_websocket(websocket: WebSocket):
    """WebSocket for real-time repo updates."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "explore":
                # Handle explore request
                question = data.get("question", "")
                if orchestrator and orchestrator.project_manager:
                    context = orchestrator.project_manager.query(
                        agent="repo_explorer",
                        question=question,
                        max_tokens=4000
                    )
                    await websocket.send_json({
                        "type": "explore_response",
                        "answer": context
                    })

            elif action == "status":
                if orchestrator and orchestrator.project_manager:
                    stats = orchestrator.project_manager.get_stats()
                    await websocket.send_json({
                        "type": "status",
                        "stats": stats
                    })

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
