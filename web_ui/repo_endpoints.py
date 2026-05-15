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


# ═══════════════════════════════════════════════════════════════
# PHASE 2 ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/git/state")
async def get_git_state():
    """Get current git state."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    return pm.get_git_state()


@router.get("/git/recent")
async def get_recently_active_files(days: int = 7, limit: int = 20):
    """Get recently modified files from git history."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    return {
        "status": "success",
        "files": pm.get_recently_active_files(days=days, limit=limit)
    }


@router.post("/impact")
async def analyze_impact(file_path: str):
    """
    Analyze the impact of changing a file.
    Returns affected files, broken imports, risk level.
    """
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.analyze_impact(file_path)
    return result


@router.get("/dependencies/{file_path:path}")
async def get_dependencies(file_path: str, direction: str = "both"):
    """
    Get dependencies for a file.
    direction: 'imports' (what this file imports), 'dependents' (what imports this), 'both'
    """
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = {"file": file_path}

    if direction in ("imports", "both"):
        result["imports"] = pm.dependencies.get(file_path, [])

    if direction in ("dependents", "both"):
        result["dependents"] = pm._dep_graph.get_dependents(pm.dependencies, file_path)
        result["all_dependents"] = pm._dep_graph.get_all_dependents(pm.dependencies, file_path)

    return result


@router.post("/reindex")
async def reindex_project(incremental: bool = True):
    """Trigger reindexing. Use incremental=true for fast updates."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager

    if incremental:
        stats = pm.index_incremental()
    else:
        stats = pm.index_project()

    return {
        "status": "success",
        "stats": {
            "total_files": stats.total_files,
            "total_symbols": stats.total_symbols,
            "total_dependencies": stats.total_dependencies,
            "elapsed_seconds": stats.elapsed_seconds,
            "is_incremental": stats.is_incremental,
            "changed_files": stats.changed_files,
            "added_files": stats.added_files,
            "removed_files": stats.removed_files,
        }
    }


@router.get("/snapshots/compare")
async def compare_snapshots(snapshot_a: str, snapshot_b: str):
    """Compare two snapshots and return structural diff."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.compare_snapshots(snapshot_a, snapshot_b)
    return result


@router.get("/metrics/retrieval")
async def get_retrieval_metrics(limit: int = 50):
    """Get retrieval quality metrics."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    return {
        "status": "success",
        "metrics": pm.get_retrieval_metrics(limit=limit)
    }


@router.get("/hot-files")
async def get_hot_files(limit: int = 10):
    """Get most frequently accessed files."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    return {
        "status": "success",
        "files": [{"path": f, "access_count": c} for f, c in pm.get_hot_files(limit=limit)]
    }


# ═══════════════════════════════════════════════════════════════
# PHASE 3 ENDPOINTS — Engineering Safety
# ═══════════════════════════════════════════════════════════════

@router.post("/validate")
async def validate_project(checks: Optional[List[str]] = None):
    """Run validation pipeline on the project."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.validate_project(checks=checks)
    return {"status": "success", "validation": result}


@router.get("/architecture/violations")
async def get_architecture_violations():
    """Check all imports for architecture rule violations."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    violations = pm.check_architecture_rules()
    return {"status": "success", "violations": violations, "count": len(violations)}


@router.get("/architecture/protected-files")
async def get_protected_files():
    """Get list of files protected from agent modifications."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    from core.project_manager.validation.architecture_rules import (
        ArchitectureRulesEngine, ArchitectureRulesConfig
    )
    engine = ArchitectureRulesEngine(
        pm.files, pm.dependencies,
        config=ArchitectureRulesConfig.default_rules(),
    )
    return {"status": "success", "protected_files": engine.get_protected_files()}


@router.post("/tests/impact")
async def get_test_impact(files: List[str]):
    """Find relevant tests for the given file changes."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.find_relevant_tests(files)
    return {"status": "success", "test_impact": result}


@router.post("/risk/assess")
async def assess_risk(request: dict):
    """Assess risk of proposed changes."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    changed_files = request.get("files", [])
    violations = request.get("architecture_violations", [])
    result = pm.assess_risk(changed_files, architecture_violations=violations)
    return {"status": "success", "risk": result}


@router.get("/modules/stability")
async def get_module_stability():
    """Get stability metrics for all modules."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.get_module_stability()
    return {"status": "success", "modules": result[:50]}  # Top 50 least stable


# ═══════════════════════════════════════════════════════════════
# PHASE 4 ENDPOINTS — Collaborative Runtime
# ═══════════════════════════════════════════════════════════════

@router.post("/tasks/create")
async def create_task(request: dict):
    """Create a new engineering task."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    task_id = pm.create_task(
        title=request.get("title", ""),
        agent=request.get("agent", ""),
        description=request.get("description", ""),
        priority=request.get("priority", "normal"),
        workflow=request.get("workflow", "default"),
    )

    if task_id is None:
        raise HTTPException(status_code=500, detail="Failed to create task")

    return {"status": "success", "task_id": task_id}


@router.get("/tasks")
async def get_active_tasks():
    """Get all active tasks."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    tasks = pm.get_active_tasks()
    return {"status": "success", "tasks": tasks, "count": len(tasks)}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    task = pm.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"status": "success", "task": task}


@router.post("/tasks/{task_id}/lock")
async def acquire_lock(task_id: str, request: dict):
    """Acquire a resource lock for a task."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    success = pm.acquire_resource_lock(
        task_id=task_id,
        resource=request.get("resource", ""),
        lock_type=request.get("lock_type", "write"),
    )

    return {"status": "success" if success else "failed", "locked": success}


@router.post("/tasks/{task_id}/conflicts")
async def detect_conflicts(task_id: str):
    """Detect conflicts for a task."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    conflicts = pm.detect_task_conflicts(task_id)
    return {"status": "success", "conflicts": conflicts, "count": len(conflicts)}


@router.post("/tasks/{task_id}/evaluate-approval")
async def evaluate_approval(task_id: str, request: dict):
    """Evaluate whether a task requires approval."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.evaluate_approval(
        task_id=task_id,
        risk_level=request.get("risk_level", "low"),
        risk_score=request.get("risk_score", 0.0),
        files_affected=request.get("files_affected", []),
        architecture_violations=request.get("architecture_violations", []),
    )

    return {"status": "success", "approval": result}


@router.get("/audit-log")
async def get_audit_log(task_id: Optional[str] = None, limit: int = 100):
    """Get workflow audit log."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    entries = pm.get_audit_log(task_id=task_id, limit=limit)
    return {"status": "success", "entries": entries, "count": len(entries)}


@router.get("/coordination/stats")
async def get_coordination_stats():
    """Get task coordination statistics."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    stats = pm.get_coordination_stats()
    return {"status": "success", "stats": stats}


# ═══════════════════════════════════════════════════════════════
# PHASE 5 ENDPOINTS — Execution Optimization
# ═══════════════════════════════════════════════════════════════

@router.post("/retrieve/optimized")
async def retrieve_optimized(request: dict):
    """Multi-stage optimized retrieval with caching and compression."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.retrieve_optimized(
        query=request.get("query", ""),
        agent=request.get("agent", "unknown"),
        use_cache=request.get("use_cache", True),
        compress=request.get("compress", True),
        max_files=request.get("max_files", 15),
        token_budget=request.get("token_budget", 12000),
    )

    return {"status": "success", "result": result}


@router.post("/validate/incremental")
async def validate_incremental(request: dict):
    """Run validation only on affected files."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.validate_incremental(
        changed_files=request.get("changed_files", []),
        max_depth=request.get("max_depth", 1),
    )

    return {"status": "success", "validation": result}


@router.post("/impact/optimized")
async def get_optimized_impact(request: dict):
    """Get impact analysis using optimized graph traversal."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    result = pm.get_optimized_impact(
        changed_files=request.get("changed_files", []),
        max_depth=request.get("max_depth", 3),
    )

    return {"status": "success", "impact": result}


@router.get("/optimization/profile")
async def get_execution_profile():
    """Get execution profiling statistics."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    return {"status": "success", "profile": pm.get_execution_profile()}


@router.get("/optimization/cache")
async def get_cache_stats():
    """Get execution cache statistics."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    return {"status": "success", "cache": pm.get_cache_stats()}


@router.get("/optimization/tokens")
async def get_token_economy():
    """Get token economy statistics."""
    if orchestrator is None or orchestrator.project_manager is None:
        raise HTTPException(status_code=400, detail="No project open")

    pm = orchestrator.project_manager
    return {"status": "success", "tokens": pm.get_token_economy()}
