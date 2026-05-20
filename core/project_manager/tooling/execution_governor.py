"""
execution_governor.py — Safety Kernel.

Controls what can be run, by whom, when, and how often.
This is the safety kernel of the entire tooling system.

Blocks:
- Runaway loops (repeated executions)
- Repeated failures (N failures in a row)
- Dangerous tooling (destructive commands)
- Resource exhaustion (too many executions)
- Unrestricted execution (no limits)

All decisions are deterministic and auditable.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class GovernorPolicy:
    """A single governor policy."""
    name: str
    description: str = ""
    max_executions_per_minute: int = 60
    max_concurrent: int = 5
    max_failures_before_block: int = 3
    cooldown_seconds: float = 1.0
    enabled: bool = True


@dataclass
class GovernorDecision:
    """Result of a governor check."""
    allowed: bool
    reason: str
    policy_name: str = ""
    cooldown_remaining: float = 0.0


@dataclass
class AgentState:
    """Track execution state per agent."""
    agent_id: str = ""
    execution_count: int = 0
    failure_count: int = 0
    last_execution_time: float = 0.0
    executions_last_minute: List[float] = field(default_factory=list)
    active_executions: int = 0
    blocked_until: float = 0.0
    total_blocked: int = 0


class ExecutionGovernor:
    """
    Safety kernel for tool execution.

    Enforces:
    - Rate limiting (executions per minute)
    - Concurrency limits (max concurrent per agent)
    - Failure thresholds (block after N failures)
    - Cooldowns (minimum time between executions)
    - Dangerous tool blocking
    """

    # Tool types that are always dangerous
    DANGEROUS_TOOLS = {"destructive_shell", "network_deploy", "self_update"}

    # Maximum executions per minute (global)
    GLOBAL_RATE_LIMIT = 120

    def __init__(self, policy: Optional[GovernorPolicy] = None):
        self._policy = policy or GovernorPolicy(
            name="default",
            description="Default execution policy",
        )
        self._agent_states: Dict[str, AgentState] = {}
        self._global_executions: List[float] = []
        self._violations: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def check_execution(
        self,
        agent_id: str,
        tool_type: str,
        task_id: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> GovernorDecision:
        """
        Check if an execution is allowed.

        Returns GovernorDecision with allowed=True/False and reason.
        """
        now = time.monotonic()
        params = params or {}

        with self._lock:
            # Get or create agent state
            state = self._agent_states.get(agent_id)
            if not state:
                state = AgentState(agent_id=agent_id)
                self._agent_states[agent_id] = state

            # Check if agent is in cooldown block
            if state.blocked_until > now:
                remaining = state.blocked_until - now
                return GovernorDecision(
                    allowed=False,
                    reason=f"Agent blocked for {remaining:.0f}s due to repeated failures",
                    policy_name=self._policy.name,
                    cooldown_remaining=remaining,
                )

            # Check dangerous tools
            if tool_type in self.DANGEROUS_TOOLS:
                self._record_violation(agent_id, tool_type, "dangerous_tool_blocked", params)
                return GovernorDecision(
                    allowed=False,
                    reason=f"Tool '{tool_type}' is classified as dangerous",
                    policy_name=self._policy.name,
                )

            # Check for dangerous patterns in tool_type (e.g. "push --force")
            for dangerous in ("push --force", "push -f", "reset --hard", "rebase", "filter-branch"):
                if dangerous in tool_type:
                    self._record_violation(agent_id, tool_type, "dangerous_pattern_blocked", params)
                    return GovernorDecision(
                        allowed=False,
                        reason=f"Dangerous pattern '{dangerous}' detected in tool type",
                        policy_name=self._policy.name,
                    )

            # Check concurrency
            if state.active_executions >= self._policy.max_concurrent:
                return GovernorDecision(
                    allowed=False,
                    reason=f"Max concurrent executions ({self._policy.max_concurrent}) reached",
                    policy_name=self._policy.name,
                )

            # Check rate limit (per agent)
            self._cleanup_old_executions(state, now)
            if len(state.executions_last_minute) >= self._policy.max_executions_per_minute:
                return GovernorDecision(
                    allowed=False,
                    reason=f"Rate limit exceeded: {self._policy.max_executions_per_minute}/min",
                    policy_name=self._policy.name,
                )

            # Check global rate limit
            self._cleanup_global_executions(now)
            if len(self._global_executions) >= self.GLOBAL_RATE_LIMIT:
                return GovernorDecision(
                    allowed=False,
                    reason=f"Global rate limit exceeded: {self.GLOBAL_RATE_LIMIT}/min",
                    policy_name=self._policy.name,
                )

            # Check cooldown
            time_since_last = now - state.last_execution_time
            if state.last_execution_time > 0 and time_since_last < self._policy.cooldown_seconds:
                remaining = self._policy.cooldown_seconds - time_since_last
                return GovernorDecision(
                    allowed=False,
                    reason=f"Cooldown active: {remaining:.1f}s remaining",
                    policy_name=self._policy.name,
                    cooldown_remaining=remaining,
                )

            # All checks passed — record execution
            state.active_executions += 1
            state.execution_count += 1
            state.last_execution_time = now
            state.executions_last_minute.append(now)
            self._global_executions.append(now)

            return GovernorDecision(
                allowed=True,
                reason="OK",
                policy_name=self._policy.name,
            )

    def record_result(
        self,
        agent_id: str,
        tool_type: str,
        success: bool,
        task_id: str = "",
    ) -> None:
        """Record the result of an execution."""
        now = time.monotonic()

        with self._lock:
            state = self._agent_states.get(agent_id)
            if not state:
                return

            state.active_executions = max(0, state.active_executions - 1)

            if success:
                state.failure_count = 0  # Reset on success
            else:
                state.failure_count += 1
                if state.failure_count >= self._policy.max_failures_before_block:
                    # Block agent
                    block_duration = min(30 * state.failure_count, 300)  # Max 5 min
                    state.blocked_until = now + block_duration
                    state.total_blocked += 1
                    self._record_violation(
                        agent_id, tool_type,
                        f"blocked_after_{state.failure_count}_failures",
                        {"block_duration": block_duration},
                    )
                    logger.warning(
                        f"Agent {agent_id} blocked for {block_duration:.0f}s "
                        f"after {state.failure_count} consecutive failures"
                    )

    def _cleanup_old_executions(self, state: AgentState, now: float) -> None:
        """Remove executions older than 60 seconds."""
        cutoff = now - 60.0
        state.executions_last_minute = [
            t for t in state.executions_last_minute if t > cutoff
        ]

    def _cleanup_global_executions(self, now: float) -> None:
        """Remove global executions older than 60 seconds."""
        cutoff = now - 60.0
        self._global_executions = [
            t for t in self._global_executions if t > cutoff
        ]

    def _record_violation(
        self, agent_id: str, tool_type: str, reason: str, params: Dict[str, Any]
    ) -> None:
        """Record a governor violation."""
        self._violations.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": agent_id,
            "tool_type": tool_type,
            "reason": reason,
            "params": {k: v for k, v in params.items() if k != "password"},
        })
        # Keep last 10000 violations
        if len(self._violations) > 10000:
            self._violations = self._violations[-10000:]

    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get the state for an agent."""
        return self._agent_states.get(agent_id)

    def get_all_agent_states(self) -> Dict[str, AgentState]:
        """Get all agent states."""
        return dict(self._agent_states)

    def get_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent violations."""
        return self._violations[-limit:]

    def unblock_agent(self, agent_id: str) -> bool:
        """Manually unblock an agent."""
        state = self._agent_states.get(agent_id)
        if state:
            state.blocked_until = 0
            state.failure_count = 0
            logger.info(f"Agent {agent_id} manually unblocked")
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get governor statistics."""
        with self._lock:
            total_executions = sum(s.execution_count for s in self._agent_states.values())
            total_blocked = sum(s.total_blocked for s in self._agent_states.values())
            active_agents = sum(
                1 for s in self._agent_states.values() if s.active_executions > 0
            )
            blocked_agents = sum(
                1 for s in self._agent_states.values() if s.blocked_until > time.monotonic()
            )

        return {
            "total_agents": len(self._agent_states),
            "active_agents": active_agents,
            "blocked_agents": blocked_agents,
            "total_executions": total_executions,
            "total_blocked_events": total_blocked,
            "total_violations": len(self._violations),
            "policy": {
                "name": self._policy.name,
                "max_per_minute": self._policy.max_executions_per_minute,
                "max_concurrent": self._policy.max_concurrent,
                "max_failures": self._policy.max_failures_before_block,
                "cooldown_seconds": self._policy.cooldown_seconds,
            },
        }
