"""
P9 — Engineering Session System.

Persistent engineering sessions that survive across interactions.
A session captures the full state of an engineering workflow.

Session stores:
- Active workflows and their state
- Context state (what PM knows)
- Pending approvals
- Runtime health
- Open risks
- Rollback checkpoints
- Git state (branch, commits)
"""

import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class SessionState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class SessionCheckpoint:
    """A recovery checkpoint within a session."""
    id: str
    timestamp: float
    description: str
    task_states: Dict[str, Any] = field(default_factory=dict)
    git_ref: str = ""
    snapshot_id: str = ""


@dataclass
class EngineeringSession:
    """A single engineering session."""
    id: str
    title: str
    state: SessionState = SessionState.ACTIVE
    created_at: float = 0.0
    updated_at: float = 0.0
    last_activity: float = 0.0

    # Context
    project_path: str = ""
    active_branch: str = ""
    git_state: Dict[str, Any] = field(default_factory=dict)

    # Workflows
    active_workflows: Dict[str, Any] = field(default_factory=dict)
    completed_workflows: List[str] = field(default_factory=list)
    failed_workflows: List[str] = field(default_factory=list)

    # Approvals
    pending_approvals: List[Dict[str, Any]] = field(default_factory=list)
    approved_actions: List[Dict[str, Any]] = field(default_factory=list)
    rejected_actions: List[Dict[str, Any]] = field(default_factory=list)

    # Risks
    open_risks: List[Dict[str, Any]] = field(default_factory=list)
    resolved_risks: List[Dict[str, Any]] = field(default_factory=list)

    # Checkpoints
    checkpoints: List[SessionCheckpoint] = field(default_factory=list)

    # History
    events: List[Dict[str, Any]] = field(default_factory=list)

    # Health
    health_score: float = 1.0
    runtime_metrics: Dict[str, Any] = field(default_factory=dict)


class EngineeringSessionSystem:
    """
    Manages persistent engineering sessions.
    Sessions survive across interactions and can be resumed.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self._sessions: Dict[str, EngineeringSession] = {}
        self._active_session_id: Optional[str] = None
        self._lock = threading.Lock()
        self._storage_path = storage_path
        self._max_events_per_session = 10000

    def create_session(self, title: str, project_path: str = "",
                       session_id: str = "") -> EngineeringSession:
        """Create a new engineering session."""
        import uuid
        sid = session_id or str(uuid.uuid4())[:8]
        now = time.time()
        session = EngineeringSession(
            id=sid,
            title=title,
            state=SessionState.ACTIVE,
            created_at=now,
            updated_at=now,
            last_activity=now,
            project_path=project_path,
        )

        with self._lock:
            self._sessions[sid] = session
            self._active_session_id = sid

        return session

    def get_session(self, session_id: str) -> Optional[EngineeringSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_active_session(self) -> Optional[EngineeringSession]:
        """Get the currently active session."""
        if self._active_session_id:
            return self._sessions.get(self._active_session_id)
        return None

    def set_active_session(self, session_id: str) -> bool:
        """Set the active session."""
        if session_id in self._sessions:
            self._active_session_id = session_id
            return True
        return False

    def pause_session(self, session_id: str) -> bool:
        """Pause a session."""
        session = self._sessions.get(session_id)
        if session and session.state == SessionState.ACTIVE:
            session.state = SessionState.PAUSED
            session.updated_at = time.time()
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session."""
        session = self._sessions.get(session_id)
        if session and session.state == SessionState.PAUSED:
            session.state = SessionState.ACTIVE
            session.updated_at = time.time()
            session.last_activity = time.time()
            return True
        return False

    def complete_session(self, session_id: str) -> bool:
        """Mark a session as completed."""
        session = self._sessions.get(session_id)
        if session:
            session.state = SessionState.COMPLETED
            session.updated_at = time.time()
            return True
        return False

    def add_event(self, session_id: str, event_type: str,
                  data: Dict[str, Any]) -> None:
        """Add an event to a session."""
        session = self._sessions.get(session_id)
        if session:
            event = {
                'timestamp': time.time(),
                'type': event_type,
                'data': data,
            }
            session.events.append(event)
            session.last_activity = time.time()
            # Trim if too many events
            if len(session.events) > self._max_events_per_session:
                session.events = session.events[-self._max_events_per_session:]

    def add_checkpoint(self, session_id: str, description: str,
                       task_states: Dict[str, Any] = None,
                       git_ref: str = "",
                       snapshot_id: str = "") -> Optional[SessionCheckpoint]:
        """Add a recovery checkpoint to a session."""
        import uuid
        session = self._sessions.get(session_id)
        if not session:
            return None

        checkpoint = SessionCheckpoint(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            description=description,
            task_states=task_states or {},
            git_ref=git_ref,
            snapshot_id=snapshot_id,
        )
        session.checkpoints.append(checkpoint)
        session.updated_at = time.time()
        return checkpoint

    def get_latest_checkpoint(self, session_id: str) -> Optional[SessionCheckpoint]:
        """Get the latest checkpoint for a session."""
        session = self._sessions.get(session_id)
        if session and session.checkpoints:
            return session.checkpoints[-1]
        return None

    def add_pending_approval(self, session_id: str,
                              approval: Dict[str, Any]) -> None:
        """Add a pending approval to a session."""
        session = self._sessions.get(session_id)
        if session:
            session.pending_approvals.append(approval)
            session.updated_at = time.time()

    def resolve_approval(self, session_id: str, approval_id: str,
                         approved: bool, resolved_by: str = "",
                         note: str = "") -> bool:
        """Resolve a pending approval."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        for i, approval in enumerate(session.pending_approvals):
            if approval.get('id') == approval_id:
                resolved = session.pending_approvals.pop(i)
                resolved['resolved_at'] = time.time()
                resolved['resolved_by'] = resolved_by
                resolved['note'] = note
                if approved:
                    session.approved_actions.append(resolved)
                else:
                    session.rejected_actions.append(resolved)
                session.updated_at = time.time()
                return True
        return False

    def add_risk(self, session_id: str, risk: Dict[str, Any]) -> None:
        """Add an open risk to a session."""
        session = self._sessions.get(session_id)
        if session:
            session.open_risks.append(risk)
            session.updated_at = time.time()

    def resolve_risk(self, session_id: str, risk_id: str) -> bool:
        """Resolve an open risk."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        for i, risk in enumerate(session.open_risks):
            if risk.get('id') == risk_id:
                resolved = session.open_risks.pop(i)
                resolved['resolved_at'] = time.time()
                session.resolved_risks.append(resolved)
                session.updated_at = time.time()
                return True
        return False

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        return {
            'id': session.id,
            'title': session.title,
            'state': session.state.value,
            'created_at': session.created_at,
            'updated_at': session.updated_at,
            'last_activity': session.last_activity,
            'active_workflows': len(session.active_workflows),
            'completed_workflows': len(session.completed_workflows),
            'failed_workflows': len(session.failed_workflows),
            'pending_approvals': len(session.pending_approvals),
            'open_risks': len(session.open_risks),
            'checkpoints': len(session.checkpoints),
            'events': len(session.events),
            'health_score': session.health_score,
        }

    def list_sessions(self, state: Optional[SessionState] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by state."""
        sessions = self._sessions.values()
        if state:
            sessions = [s for s in sessions if s.state == state]
        return [self.get_session_summary(s.id) for s in sessions]

    def cleanup_expired(self, max_age_hours: float = 24.0) -> int:
        """Remove expired sessions. Returns count removed."""
        now = time.time()
        expired = []
        for sid, session in self._sessions.items():
            if session.state in (SessionState.COMPLETED, SessionState.FAILED):
                if (now - session.updated_at) > max_age_hours * 3600:
                    expired.append(sid)
            elif session.state == SessionState.ACTIVE:
                if (now - session.last_activity) > max_age_hours * 3600:
                    session.state = SessionState.EXPIRED
                    expired.append(sid)

        for sid in expired:
            del self._sessions[sid]

        return len(expired)
