"""
tool_runtime.py — Unified Tooling Runtime.

Central registry and execution layer for all engineering tools.
Every tool execution goes through:
  1. Capability check (does the agent have access?)
  2. Governor approval (is this execution allowed?)
  3. Execution (run the tool)
  4. Logging (record the result)
  5. Return structured result

NO tool bypasses this pipeline.
"""

from __future__ import annotations

import time
import uuid
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger


class ToolType(Enum):
    TEST_RUNNER = "test_runner"
    LINT_RUNNER = "lint_runner"
    FORMATTER = "formatter"
    GIT_TOOL = "git_tool"
    REPO_SEARCH = "repo_search"
    DEPENDENCY_INSPECTOR = "dependency_inspector"
    BUILD_RUNNER = "build_runner"


class ToolStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class Capability(Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    RUN_TESTS = "run_tests"
    RUN_LINT = "run_lint"
    RUN_BUILD = "run_build"
    GIT_READ = "git_read"
    GIT_WRITE = "git_write"
    GIT_BRANCH = "git_branch"
    SEARCH_REPO = "search_repo"
    INSPECT_DEPS = "inspect_deps"
    FORMAT_CODE = "format_code"


# Map tool types to required capabilities
TOOL_CAPABILITIES: Dict[ToolType, List[Capability]] = {
    ToolType.TEST_RUNNER: [Capability.READ_FILES, Capability.RUN_TESTS],
    ToolType.LINT_RUNNER: [Capability.READ_FILES, Capability.RUN_LINT],
    ToolType.FORMATTER: [Capability.READ_FILES, Capability.WRITE_FILES, Capability.FORMAT_CODE],
    ToolType.GIT_TOOL: [Capability.GIT_READ],
    ToolType.REPO_SEARCH: [Capability.READ_FILES, Capability.SEARCH_REPO],
    ToolType.DEPENDENCY_INSPECTOR: [Capability.READ_FILES, Capability.INSPECT_DEPS],
    ToolType.BUILD_RUNNER: [Capability.READ_FILES, Capability.RUN_BUILD],
}


@dataclass
class ToolResult:
    """Structured result from any tool execution."""
    tool_type: str = ""
    status: str = ToolStatus.SUCCESS.value
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    execution_id: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == ToolStatus.SUCCESS.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_type": self.tool_type,
            "status": self.status,
            "output": self.output[:5000] if self.output else "",
            "error": self.error[:2000] if self.error else "",
            "exit_code": self.exit_code,
            "duration_ms": round(self.duration_ms, 2),
            "execution_id": self.execution_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionLog:
    """A single execution log entry."""
    execution_id: str = ""
    tool_type: str = ""
    agent_id: str = ""
    task_id: str = ""
    status: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float = 0.0
    error: str = ""
    blocked_reason: str = ""


class ToolRegistry:
    """
    Registry of all available tools.
    Maps tool types to their handler functions.
    """

    def __init__(self):
        self._handlers: Dict[ToolType, Callable] = {}
        self._capabilities: Dict[str, set] = {}  # agent_id -> set of Capability
        self._lock = threading.Lock()

    def register(self, tool_type: ToolType, handler: Callable) -> None:
        """Register a tool handler."""
        with self._lock:
            self._handlers[tool_type] = handler
        logger.debug(f"Tool registered: {tool_type.value}")

    def unregister(self, tool_type: ToolType) -> None:
        """Unregister a tool."""
        with self._lock:
            self._handlers.pop(tool_type, None)

    def get_handler(self, tool_type: ToolType) -> Optional[Callable]:
        """Get the handler for a tool type."""
        return self._handlers.get(tool_type)

    def list_tools(self) -> List[ToolType]:
        """List all registered tool types."""
        return list(self._handlers.keys())

    def register_agent_capabilities(self, agent_id: str, capabilities: List[Capability]) -> None:
        """Register what capabilities an agent has."""
        with self._lock:
            self._capabilities[agent_id] = set(capabilities)

    def has_capability(self, agent_id: str, capability: Capability) -> bool:
        """Check if an agent has a specific capability."""
        caps = self._capabilities.get(agent_id, set())
        return capability in caps

    def check_tool_access(self, agent_id: str, tool_type: ToolType) -> Tuple[bool, str]:
        """
        Check if an agent can use a tool.
        Returns (allowed, reason).
        """
        required = TOOL_CAPABILITIES.get(tool_type, [])
        agent_caps = self._capabilities.get(agent_id, set())

        missing = [c for c in required if c not in agent_caps]
        if missing:
            return False, f"Missing capabilities: {', '.join(c.value for c in missing)}"

        return True, "OK"


class ToolRuntime:
    """
    Unified tooling runtime.
    All tool executions go through here.
    """

    def __init__(self, project_root: str = ".", governor: Any = None):
        self._project_root = Path(project_root).resolve()
        self._registry = ToolRegistry()
        self._governor = governor
        self._execution_log: List[ExecutionLog] = []
        self._max_log_size = 10000
        self._lock = threading.Lock()

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    @property
    def governor(self) -> Any:
        return self._governor

    def set_governor(self, governor: Any) -> None:
        """Set the execution governor."""
        self._governor = governor

    def execute(
        self,
        tool_type: ToolType,
        agent_id: str,
        task_id: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        Execute a tool with full governance.

        Pipeline:
        1. Check capability access
        2. Check governor approval
        3. Execute tool
        4. Log result
        5. Return structured result
        """
        execution_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow().isoformat() + "Z"
        t0 = time.monotonic()
        params = params or {}

        result = ToolResult(
            tool_type=tool_type.value,
            execution_id=execution_id,
            timestamp=started_at,
        )

        # Step 1: Capability check
        allowed, reason = self._registry.check_tool_access(agent_id, tool_type)
        if not allowed:
            result.status = ToolStatus.BLOCKED.value
            result.error = reason
            result.duration_ms = (time.monotonic() - t0) * 1000
            self._log_execution(execution_id, tool_type.value, agent_id, task_id,
                              ToolStatus.BLOCKED.value, started_at, result.duration_ms,
                              blocked_reason=reason)
            logger.warning(f"Tool blocked: {tool_type.value} for agent {agent_id}: {reason}")
            return result

        # Step 2: Governor approval
        if self._governor:
            gov_decision = self._governor.check_execution(
                agent_id=agent_id,
                tool_type=tool_type.value,
                task_id=task_id,
                params=params,
            )
            if not gov_decision.allowed:
                result.status = ToolStatus.BLOCKED.value
                result.error = gov_decision.reason
                result.duration_ms = (time.monotonic() - t0) * 1000
                self._log_execution(execution_id, tool_type.value, agent_id, task_id,
                                  ToolStatus.BLOCKED.value, started_at, result.duration_ms,
                                  blocked_reason=gov_decision.reason)
                logger.warning(f"Tool blocked by governor: {tool_type.value}: {gov_decision.reason}")
                return result

        # Step 3: Execute
        handler = self._registry.get_handler(tool_type)
        if not handler:
            result.status = ToolStatus.FAILURE.value
            result.error = f"No handler registered for {tool_type.value}"
            result.duration_ms = (time.monotonic() - t0) * 1000
            self._log_execution(execution_id, tool_type.value, agent_id, task_id,
                              ToolStatus.FAILURE.value, started_at, result.duration_ms,
                              error=result.error)
            return result

        try:
            output, error, exit_code = handler(self._project_root, params)
            result.output = output
            result.error = error
            result.exit_code = exit_code
            result.status = ToolStatus.SUCCESS.value if exit_code == 0 else ToolStatus.FAILURE.value
        except subprocess.TimeoutExpired:
            result.status = ToolStatus.TIMEOUT.value
            result.error = "Tool execution timed out"
        except Exception as e:
            result.status = ToolStatus.FAILURE.value
            result.error = str(e)

        result.duration_ms = (time.monotonic() - t0) * 1000

        # Step 4: Log
        self._log_execution(
            execution_id, tool_type.value, agent_id, task_id,
            result.status, started_at, result.duration_ms,
            error=result.error,
        )

        return result

    def _log_execution(
        self,
        execution_id: str,
        tool_type: str,
        agent_id: str,
        task_id: str,
        status: str,
        started_at: str,
        duration_ms: float,
        error: str = "",
        blocked_reason: str = "",
    ) -> None:
        """Record an execution log entry."""
        log_entry = ExecutionLog(
            execution_id=execution_id,
            tool_type=tool_type,
            agent_id=agent_id,
            task_id=task_id,
            status=status,
            started_at=started_at,
            finished_at=datetime.utcnow().isoformat() + "Z",
            duration_ms=round(duration_ms, 2),
            error=error[:500] if error else "",
            blocked_reason=blocked_reason[:200] if blocked_reason else "",
        )
        with self._lock:
            self._execution_log.append(log_entry)
            if len(self._execution_log) > self._max_log_size:
                self._execution_log = self._execution_log[-self._max_log_size:]

    def get_execution_log(
        self,
        agent_id: str = "",
        tool_type: str = "",
        task_id: str = "",
        limit: int = 100,
    ) -> List[ExecutionLog]:
        """Get execution log entries, optionally filtered."""
        with self._lock:
            entries = list(self._execution_log)

        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        if tool_type:
            entries = [e for e in entries if e.tool_type == tool_type]
        if task_id:
            entries = [e for e in entries if e.task_id == task_id]

        return entries[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics."""
        with self._lock:
            entries = list(self._execution_log)

        total = len(entries)
        if total == 0:
            return {"total_executions": 0}

        success = sum(1 for e in entries if e.status == ToolStatus.SUCCESS.value)
        blocked = sum(1 for e in entries if e.status == ToolStatus.BLOCKED.value)
        failed = sum(1 for e in entries if e.status == ToolStatus.FAILURE.value)
        timeouts = sum(1 for e in entries if e.status == ToolStatus.TIMEOUT.value)

        avg_duration = sum(e.duration_ms for e in entries) / total if total > 0 else 0

        by_tool: Dict[str, int] = {}
        for e in entries:
            by_tool[e.tool_type] = by_tool.get(e.tool_type, 0) + 1

        return {
            "total_executions": total,
            "success": success,
            "blocked": blocked,
            "failed": failed,
            "timeouts": timeouts,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
            "avg_duration_ms": round(avg_duration, 2),
            "by_tool": by_tool,
            "registered_tools": [t.value for t in self._registry.list_tools()],
        }
