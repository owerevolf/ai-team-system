"""
session_continuity.py — Session Continuity Runtime.

Purpose: Continue work after restart, new session, or long pause.
System should be able to say: "Here's where we left off."

Saves:
- current objective
- unfinished tasks
- important decisions
- active constraints
- dangerous zones
- current architecture assumptions
"""

from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class SessionState:
    """Complete state of a session for continuity."""
    session_id: str = ""
    project_id: str = ""
    current_objective: str = ""
    unfinished_tasks: List[Dict[str, Any]] = field(default_factory=list)
    completed_tasks: List[Dict[str, Any]] = field(default_factory=list)
    important_decisions: List[Dict[str, str]] = field(default_factory=list)
    active_constraints: List[str] = field(default_factory=list)
    dangerous_zones: List[str] = field(default_factory=list)
    architecture_assumptions: Dict[str, str] = field(default_factory=dict)
    active_files: List[str] = field(default_factory=list)
    last_action: str = ""
    timestamp: str = ""


class SessionContinuity:
    """
    Manages session state for continuity across restarts.
    System can say: "Here's where we left off."
    """

    def __init__(self, state_dir: str = ".ai-team/sessions"):
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._current_state: Optional[SessionState] = None
        self._lock = threading.Lock()

    def create_session(self, session_id: str, project_id: str,
                       objective: str) -> SessionState:
        """Create a new session."""
        state = SessionState(
            session_id=session_id,
            project_id=project_id,
            current_objective=objective,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self._current_state = state
        self._save_state(state)
        logger.info(f"Session created: {session_id}")
        return state

    def save_progress(self, state: SessionState) -> None:
        """Save current progress."""
        state.timestamp = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            self._current_state = state
        self._save_state(state)

    def resume_session(self, session_id: str) -> Optional[SessionState]:
        """Resume a previous session."""
        state = self._load_state(session_id)
        if state:
            with self._lock:
                self._current_state = state
            logger.info(f"Session resumed: {session_id}")
        return state

    def get_current_state(self) -> Optional[SessionState]:
        """Get current session state."""
        return self._current_state

    def add_unfinished_task(self, task: Dict[str, Any]) -> None:
        """Add an unfinished task."""
        with self._lock:
            if self._current_state:
                self._current_state.unfinished_tasks.append(task)
                self._save_state(self._current_state)

    def complete_task(self, task_id: str, summary: str = "") -> None:
        """Mark a task as completed."""
        with self._lock:
            if self._current_state:
                # Move from unfinished to completed
                remaining = []
                for t in self._current_state.unfinished_tasks:
                    if t.get("id") == task_id:
                        t["completed_at"] = datetime.utcnow().isoformat() + "Z"
                        t["summary"] = summary
                        self._current_state.completed_tasks.append(t)
                    else:
                        remaining.append(t)
                self._current_state.unfinished_tasks = remaining

    def add_decision(self, decision: str, reason: str) -> None:
        """Record an important decision."""
        with self._lock:
            if self._current_state:
                self._current_state.important_decisions.append({
                    "decision": decision,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
                self._save_state(self._current_state)

    def add_constraint(self, constraint: str) -> None:
        """Add an active constraint."""
        with self._lock:
            if self._current_state:
                if constraint not in self._current_state.active_constraints:
                    self._current_state.active_constraints.append(constraint)
                self._save_state(self._current_state)

    def add_dangerous_zone(self, zone: str) -> None:
        """Add a dangerous zone."""
        with self._lock:
            if self._current_state:
                if zone not in self._current_state.dangerous_zones:
                    self._current_state.dangerous_zones.append(zone)
                self._save_state(self._current_state)

    def get_resume_summary(self) -> str:
        """Generate a summary of where we left off."""
        state = self._current_state
        if not state:
            return "No active session."

        lines = [
            f"# Session: {state.session_id}",
            f"Project: {state.project_id}",
            f"Last active: {state.timestamp}",
            "",
            f"## Objective",
            state.current_objective,
            "",
        ]

        if state.unfinished_tasks:
            lines.append("## Unfinished Tasks")
            for t in state.unfinished_tasks[:10]:
                lines.append(f"- {t.get('title', 'Unknown')}")
            lines.append("")

        if state.important_decisions:
            lines.append("## Important Decisions")
            for d in state.important_decisions[:5]:
                lines.append(f"- {d['decision']}")
            lines.append("")

        if state.active_constraints:
            lines.append("## Active Constraints")
            for c in state.active_constraints[:5]:
                lines.append(f"- {c}")
            lines.append("")

        if state.dangerous_zones:
            lines.append("## Dangerous Zones")
            for z in state.dangerous_zones[:5]:
                lines.append(f"- {z}")
            lines.append("")

        if state.active_files:
            lines.append("## Active Files")
            for f in state.active_files[:10]:
                lines.append(f"- {f}")
            lines.append("")

        return "\n".join(lines)

    def list_sessions(self, project_id: str = "") -> List[Dict[str, str]]:
        """List available sessions."""
        sessions = []
        for f in self._state_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if not project_id or data.get("project_id") == project_id:
                    sessions.append({
                        "session_id": data.get("session_id", ""),
                        "project_id": data.get("project_id", ""),
                        "timestamp": data.get("timestamp", ""),
                        "objective": data.get("current_objective", "")[:50],
                    })
            except (json.JSONDecodeError, IOError):
                continue
        return sorted(sessions, key=lambda s: s.get("timestamp", ""), reverse=True)

    def _save_state(self, state: SessionState) -> None:
        """Save state to disk."""
        path = self._state_dir / f"{state.session_id}.json"
        try:
            data = {
                "session_id": state.session_id,
                "project_id": state.project_id,
                "current_objective": state.current_objective,
                "unfinished_tasks": state.unfinished_tasks,
                "completed_tasks": state.completed_tasks,
                "important_decisions": state.important_decisions,
                "active_constraints": state.active_constraints,
                "dangerous_zones": state.dangerous_zones,
                "architecture_assumptions": state.architecture_assumptions,
                "active_files": state.active_files,
                "last_action": state.last_action,
                "timestamp": state.timestamp,
            }
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except IOError as e:
            logger.error(f"Failed to save session state: {e}")

    def _load_state(self, session_id: str) -> Optional[SessionState]:
        """Load state from disk."""
        path = self._state_dir / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return SessionState(
                session_id=data.get("session_id", ""),
                project_id=data.get("project_id", ""),
                current_objective=data.get("current_objective", ""),
                unfinished_tasks=data.get("unfinished_tasks", []),
                completed_tasks=data.get("completed_tasks", []),
                important_decisions=data.get("important_decisions", []),
                active_constraints=data.get("active_constraints", []),
                dangerous_zones=data.get("dangerous_zones", []),
                architecture_assumptions=data.get("architecture_assumptions", {}),
                active_files=data.get("active_files", []),
                last_action=data.get("last_action", ""),
                timestamp=data.get("timestamp", ""),
            )
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load session state: {e}")
            return None
