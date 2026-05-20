"""
Approval Runtime — human approval flow.

NO HIDDEN EXECUTION.
Every patch must be approved by a human before application.

Flow:
Agent → generates patch → review layer → approval queue → human approve/reject → apply
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ApprovalLevel(Enum):
    LOW = "low"        # comments, docs, formatting — auto-approve
    MEDIUM = "medium"  # feature logic, refactors — needs approval
    HIGH = "high"      # architecture, auth, database — needs approval
    CRITICAL = "critical"  # security, core — needs explicit approval


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """A request for human approval of a patch."""
    request_id: str = ""
    patch_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    summary: str = ""
    risk_level: str = ApprovalLevel.MEDIUM.value
    status: str = ApprovalStatus.PENDING.value
    created_at: str = ""
    resolved_at: str = ""
    resolved_by: str = ""
    comments: str = ""

    # Patch info
    files_changed: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    diff_preview: str = ""

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "patch_id": self.patch_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "summary": self.summary,
            "risk_level": self.risk_level,
            "status": self.status,
            "created_at": self.created_at,
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "diff_preview": self.diff_preview[:500] if self.diff_preview else "",
        }


class ApprovalRuntime:
    """
    Manages the human approval queue.

    Rules:
    - LOW risk: auto-approve (docs, comments, formatting)
    - MEDIUM risk: needs human approval
    - HIGH/CRITICAL risk: needs explicit human approval
    - No patch is applied without approval
    """

    def __init__(self):
        self._queue: Dict[str, ApprovalRequest] = {}
        self._history: List[ApprovalRequest] = []

    def create_request(self, patch_id: str, task_id: str, agent_id: str,
                       summary: str, risk_level: str,
                       files_changed: List[str] = None,
                       lines_added: int = 0, lines_removed: int = 0,
                       diff_preview: str = "") -> ApprovalRequest:
        """Create an approval request for a patch."""
        request = ApprovalRequest(
            patch_id=patch_id,
            task_id=task_id,
            agent_id=agent_id,
            summary=summary,
            risk_level=risk_level,
            files_changed=files_changed if files_changed is not None else [],
            lines_added=lines_added,
            lines_removed=lines_removed,
            diff_preview=diff_preview,
        )

        # Auto-approve low risk
        if risk_level == ApprovalLevel.LOW.value:
            request.status = ApprovalStatus.AUTO_APPROVED.value
            request.resolved_at = datetime.utcnow().isoformat() + "Z"
            request.resolved_by = "system"
            self._history.append(request)
        else:
            self._queue[request.request_id] = request

        return request

    def approve(self, request_id: str, approved_by: str = "user",
                comments: str = "") -> Optional[ApprovalRequest]:
        """Approve a pending request."""
        request = self._queue.get(request_id)
        if not request:
            return None

        request.status = ApprovalStatus.APPROVED.value
        request.resolved_at = datetime.utcnow().isoformat() + "Z"
        request.resolved_by = approved_by
        request.comments = comments

        self._history.append(request)
        del self._queue[request_id]

        return request

    def reject(self, request_id: str, rejected_by: str = "user",
               comments: str = "") -> Optional[ApprovalRequest]:
        """Reject a pending request."""
        request = self._queue.get(request_id)
        if not request:
            return None

        request.status = ApprovalStatus.REJECTED.value
        request.resolved_at = datetime.utcnow().isoformat() + "Z"
        request.resolved_by = rejected_by
        request.comments = comments

        self._history.append(request)
        del self._queue[request_id]

        return request

    def get_pending(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return list(self._queue.values())

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._queue.get(request_id)

    def get_history(self, limit: int = 20) -> List[ApprovalRequest]:
        """Get approval history."""
        return self._history[-limit:]

    def is_approved(self, request_id: str) -> bool:
        """Check if a request is approved (including auto-approved)."""
        # Check history
        for req in self._history:
            if req.request_id == request_id:
                return req.status in (ApprovalStatus.APPROVED.value,
                                     ApprovalStatus.AUTO_APPROVED.value)
        return False

    def get_queue_size(self) -> int:
        return len(self._queue)
