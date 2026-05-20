"""
Tooling API — FastAPI endpoints for Phase 19E.

Endpoints:
    POST /api/tooling/test          — run tests
    POST /api/tooling/lint          — run lint
    POST /api/tooling/build         — run build
    POST /api/tooling/git           — git operations
    POST /api/tooling/deps          — dependency analysis
    POST /api/tooling/search        — repo search
    GET  /api/tooling/metrics       — runtime metrics
    GET  /api/tooling/governor      — governor status
    GET  /api/tooling/logs          — execution logs
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from loguru import logger

from ..tooling.test_runner import TestRunner
from ..tooling.lint_runner import LintRunner
from ..tooling.build_runner import BuildRunner
from ..tooling.git_runtime import GitRuntime
from ..tooling.dependency_inspector import DependencyInspector
from ..tooling.repo_search import RepoSearch
from ..tooling.execution_governor import ExecutionGovernor, GovernorPolicy
from ..tooling.runtime_metrics import RuntimeMetrics, TaskMetric
from ..tooling.tool_runtime import ToolRuntime, ToolType


# ── Router ──

router = APIRouter(prefix="/api/tooling", tags=["tooling"])


# ── Shared instances ──

PROJECT_ROOT = str(Path(__file__).resolve().resolve().parent.parent.parent)

_metrics = RuntimeMetrics()
_governor = ExecutionGovernor(GovernorPolicy(
    name="default",
    description="Default tooling policy",
    max_executions_per_minute=30,
    max_concurrent=3,
    max_failures_before_block=3,
    cooldown_seconds=0.5,
))
_runtime = ToolRuntime(project_root=PROJECT_ROOT, governor=_governor)


# ── Request models ──

class TestRequest(BaseModel):
    framework: str = ""
    test_path: str = ""
    timeout: int = 0


class LintRequest(BaseModel):
    tool: str = ""
    target_path: str = ""


class BuildRequest(BaseModel):
    builder: str = ""


class GitRequest(BaseModel):
    operation: str = ""
    args: List[str] = []
    agent_id: str = "api"
    task_id: str = ""


class SearchRequest(BaseModel):
    query: str = ""
    search_type: str = "text"
    max_results: int = 50


# ── Test Endpoints ──

@router.post("/test")
async def run_tests(req: TestRequest) -> Dict[str, Any]:
    """Run tests with the specified framework."""
    runner = TestRunner(PROJECT_ROOT)
    result = runner.run(
        framework=req.framework,
        test_path=req.test_path,
        timeout=req.timeout,
    )

    # Record metrics
    _metrics.record_tool_run(
        tool_type="test_runner",
        success=result.all_passed,
        blocked=False,
        duration_ms=result.duration_ms,
    )

    if not result.all_passed:
        _metrics.record_failure(
            task_id="manual",
            agent_id="api",
            failure_type="test_failure",
            reason=f"{result.failed} tests failed",
            tool_type="test_runner",
        )

    return {"status": "ok" if result.all_passed else "failed", "result": result.to_dict()}


@router.get("/test/frameworks")
async def detect_test_frameworks() -> Dict[str, Any]:
    """Detect available test frameworks."""
    runner = TestRunner(PROJECT_ROOT)
    framework = runner.detect_framework()
    return {"status": "ok", "detected": framework}


# ── Lint Endpoints ──

@router.post("/lint")
async def run_lint(req: LintRequest) -> Dict[str, Any]:
    """Run lint tool."""
    runner = LintRunner(PROJECT_ROOT)
    result = runner.run(tool=req.tool, target_path=req.target_path)

    _metrics.record_tool_run(
        tool_type="lint_runner",
        success=result.passed,
        blocked=False,
        duration_ms=result.duration_ms,
    )

    return {"status": "ok" if result.passed else "failed", "result": result.to_dict()}


@router.get("/lint/tools")
async def detect_lint_tools() -> Dict[str, Any]:
    """Detect available lint tools."""
    runner = LintRunner(PROJECT_ROOT)
    tools = runner.detect_linters()
    return {"status": "ok", "tools": tools}


# ── Build Endpoints ──

@router.post("/build")
async def run_build(req: BuildRequest) -> Dict[str, Any]:
    """Run a verification build."""
    runner = BuildRunner(PROJECT_ROOT)
    result = runner.run(builder=req.builder)

    _metrics.record_tool_run(
        tool_type="build_runner",
        success=result.success,
        blocked=False,
        duration_ms=result.duration_ms,
    )

    if not result.success:
        _metrics.record_failure(
            task_id="manual",
            agent_id="api",
            failure_type="build_failure",
            reason=result.error or "Build failed",
            tool_type="build_runner",
        )

    return {"status": "ok" if result.success else "failed", "result": result.to_dict()}


@router.get("/build/detect")
async def detect_builders() -> Dict[str, Any]:
    """Detect available builders."""
    runner = BuildRunner(PROJECT_ROOT)
    builders = runner.detect_builders()
    return {"status": "ok", "builders": builders}


# ── Git Endpoints ──

@router.post("/git")
async def git_operation(req: GitRequest) -> Dict[str, Any]:
    """Execute a git operation."""
    runtime = GitRuntime(PROJECT_ROOT)
    result = runtime.execute(
        operation=req.operation,
        args=req.args,
        agent_id=req.agent_id,
        task_id=req.task_id,
    )

    _metrics.record_tool_run(
        tool_type="git_tool",
        success=result.success,
        blocked=result.status == "blocked",
        duration_ms=0,
    )

    if result.status == "blocked":
        _metrics.record_failure(
            task_id=req.task_id,
            agent_id=req.agent_id,
            failure_type="git_blocked",
            reason=result.blocked_reason,
            tool_type="git_tool",
        )

    return {"status": result.status, "result": result.to_dict()}


@router.get("/git/status")
async def git_status() -> Dict[str, Any]:
    """Get git status."""
    runtime = GitRuntime(PROJECT_ROOT)
    result = runtime.status()
    return {"status": result.status, "result": result.to_dict()}


@router.get("/git/branch")
async def git_branch() -> Dict[str, Any]:
    """Get current branch."""
    runtime = GitRuntime(PROJECT_ROOT)
    branch = runtime.current_branch()
    return {"status": "ok", "branch": branch}


@router.get("/git/modified")
async def git_modified() -> Dict[str, Any]:
    """Get modified files."""
    runtime = GitRuntime(PROJECT_ROOT)
    files = runtime.get_modified_files()
    return {"status": "ok", "files": files, "count": len(files)}


# ── Dependency Endpoints ──

@router.post("/deps")
async def analyze_dependencies() -> Dict[str, Any]:
    """Analyze project dependencies."""
    inspector = DependencyInspector(PROJECT_ROOT)
    report = inspector.analyze()

    _metrics.record_tool_run(
        tool_type="dependency_inspector",
        success=True,
        blocked=False,
        duration_ms=0,
    )

    return {"status": "ok", "report": report.to_dict()}


# ── Search Endpoints ──

@router.post("/search")
async def search_repo(req: SearchRequest) -> Dict[str, Any]:
    """Search the repository."""
    search = RepoSearch(PROJECT_ROOT)
    result = search.search(
        query=req.query,
        search_type=req.search_type,
        max_results=req.max_results,
    )

    _metrics.record_tool_run(
        tool_type="repo_search",
        success=True,
        blocked=False,
        duration_ms=result.duration_ms,
    )

    return {"status": "ok", "result": result.to_dict()}


@router.get("/search/symbols")
async def search_symbols(name: str = Query(...)) -> Dict[str, Any]:
    """Search for a symbol."""
    search = RepoSearch(PROJECT_ROOT)
    result = search.find_symbol(name)
    return {"status": "ok", "result": result.to_dict()}


@router.get("/search/routes")
async def search_routes(pattern: str = Query("")) -> Dict[str, Any]:
    """Search for API routes."""
    search = RepoSearch(PROJECT_ROOT)
    result = search.find_routes(pattern)
    return {"status": "ok", "result": result.to_dict()}


# ── Metrics Endpoints ──

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get runtime metrics snapshot."""
    snapshot = _metrics.get_snapshot()
    return {"status": "ok", "metrics": snapshot.to_dict()}


@router.get("/metrics/failures")
async def get_failures(limit: int = 50) -> Dict[str, Any]:
    """Get recent failures."""
    failures = _metrics.get_failure_log(limit=limit)
    return {"status": "ok", "failures": failures, "count": len(failures)}


# ── Governor Endpoints ──

@router.get("/governor")
async def get_governor_status() -> Dict[str, Any]:
    """Get governor status."""
    stats = _governor.get_stats()
    return {"status": "ok", "governor": stats}


@router.get("/governor/agents")
async def get_agent_states() -> Dict[str, Any]:
    """Get all agent states."""
    states = _governor.get_all_agent_states()
    return {
        "status": "ok",
        "agents": {
            agent_id: {
                "execution_count": s.execution_count,
                "failure_count": s.failure_count,
                "active_executions": s.active_executions,
                "blocked_until": s.blocked_until,
                "total_blocked": s.total_blocked,
            }
            for agent_id, s in states.items()
        },
    }


@router.post("/governor/unblock")
async def unblock_agent(agent_id: str = Query(...)) -> Dict[str, Any]:
    """Manually unblock an agent."""
    success = _governor.unblock_agent(agent_id)
    return {"status": "ok" if success else "not_found", "agent_id": agent_id}


# ── Execution Logs ──

@router.get("/logs")
async def get_execution_logs(
    agent_id: str = "",
    tool_type: str = "",
    task_id: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    """Get execution logs."""
    logs = _runtime.get_execution_log(
        agent_id=agent_id,
        tool_type=tool_type,
        task_id=task_id,
        limit=limit,
    )
    return {
        "status": "ok",
        "logs": [
            {
                "execution_id": log.execution_id,
                "tool_type": log.tool_type,
                "agent_id": log.agent_id,
                "task_id": log.task_id,
                "status": log.status,
                "started_at": log.started_at,
                "duration_ms": log.duration_ms,
                "error": log.error,
                "blocked_reason": log.blocked_reason,
            }
            for log in logs
        ],
        "count": len(logs),
    }


# ── Runtime Stats ──

@router.get("/stats")
async def get_runtime_stats() -> Dict[str, Any]:
    """Get tool runtime statistics."""
    stats = _runtime.get_stats()
    return {"status": "ok", "stats": stats}
