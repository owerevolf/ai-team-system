"""
Approval Workflows — workflow-aware approval system.

Rules:
- LOW risk + validation passed → auto-apply
- MEDIUM risk → auto-apply with notification
- HIGH risk → requires explicit approval
- CRITICAL risk → requires approval + architecture review
- Protected files → always require approval
- Architecture violations → always require approval
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


class ApprovalStatus(Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    EXPIRED = "expired"


class ApprovalTrigger(Enum):
    RISK_LEVEL = "risk_level"
    PROTECTED_FILE = "protected_file"
    ARCHITECTURE_VIOLATION = "architecture_violation"
    PUBLIC_API_CHANGE = "public_api_change"
    BREAKING_CHANGE = "breaking_change"
    MANUAL = "manual"


@dataclass
class ApprovalRequest:
    """A request for approval."""
    id: str = ""
    task_id: str = ""
    trigger: ApprovalTrigger = ApprovalTrigger.MANUAL
    status: ApprovalStatus = ApprovalStatus.PENDING
    risk_level: str = "low"
    risk_score: float = 0.0
    files_affected: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    description: str = ""
    requested_at: str = ""
    resolved_at: str = ""
    resolved_by: str = ""
    resolution_note: str = ""
    auto_approved: bool = False


@dataclass
class AuditEntry:
    """An immutable audit log entry."""
    id: str = ""
    timestamp: str = ""
    task_id: str = ""
    action: str = ""  # task_created, patch_applied, approval_requested, etc.
    agent: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    file_changes: List[str] = field(default_factory=list)
    validation_result: Optional[Dict] = None
    risk_level: str = ""
    snapshot_id: str = ""


class ApprovalWorkflowEngine:
    """
    Determines when approval is needed and manages approval flow.
    """

    def __init__(self):
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._audit_log: List[AuditEntry] = []

    def evaluate_approval_need(
        self,
        task_id: str,
        risk_level: str,
        risk_score: float,
        files_affected: List[str],
        architecture_violations: List[str],
        public_api_changes: int,
        breaking_changes: int,
        protected_files_touched: List[str],
    ) -> ApprovalRequest:
        """
        Evaluate whether a task requires approval.

        Returns:
            ApprovalRequest with status and reason
        """
        request = ApprovalRequest(
            id=f"apr-{task_id}",
            task_id=task_id,
            risk_level=risk_level,
            risk_score=risk_score,
            files_affected=files_affected,
            violations=architecture_violations,
            requested_at=self._now(),
        )

        # Determine if approval is needed
        triggers = []

        if risk_level == "critical":
            triggers.append(ApprovalTrigger.RISK_LEVEL)
            request.description = "CRITICAL risk level requires approval"

        elif risk_level == "high":
            triggers.append(ApprovalTrigger.RISK_LEVEL)
            request.description = "HIGH risk level requires approval"

        if protected_files_touched:
            triggers.append(ApprovalTrigger.PROTECTED_FILE)
            request.description = f"Protected files modified: {', '.join(protected_files_touched[:3])}"

        if architecture_violations:
            triggers.append(ApprovalTrigger.ARCHITECTURE_VIOLATION)
            request.description = f"Architecture violations: {len(architecture_violations)}"

        if breaking_changes > 0:
            triggers.append(ApprovalTrigger.BREAKING_CHANGE)
            request.description = f"Breaking changes detected: {breaking_changes}"

        if public_api_changes > 2:
            triggers.append(ApprovalTrigger.PUBLIC_API_CHANGE)
            request.description = f"Public API changes: {public_api_changes}"

        # Auto-approve low risk with no violations
        if not triggers and risk_level in ("low", "medium"):
            request.status = ApprovalStatus.AUTO_APPROVED
            request.auto_approved = True
            request.resolved_at = self._now()
            request.resolved_by = "system"
        elif triggers:
            request.status = ApprovalStatus.PENDING
            request.trigger = triggers[0]
        else:
            request.status = ApprovalStatus.NOT_REQUIRED

        self._approvals[request.id] = request

        # Audit log
        self._add_audit_entry(
            task_id=task_id,
            action="approval_evaluated",
            details={
                'approval_id': request.id,
                'status': request.status.value,
                'triggers': [t.value for t in triggers],
                'auto_approved': request.auto_approved,
            },
        )

        return request

    def approve(self, approval_id: str, approved_by: str, note: str = "") -> bool:
        """Approve a request."""
        request = self._approvals.get(approval_id)
        if not request:
            return False

        request.status = ApprovalStatus.APPROVED
        request.resolved_at = self._now()
        request.resolved_by = approved_by
        request.resolution_note = note

        self._add_audit_entry(
            task_id=request.task_id,
            action="approval_granted",
            details={'approval_id': approval_id, 'by': approved_by, 'note': note},
        )

        return True

    def reject(self, approval_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a request."""
        request = self._approvals.get(approval_id)
        if not request:
            return False

        request.status = ApprovalStatus.REJECTED
        request.resolved_at = self._now()
        request.resolved_by = rejected_by
        request.resolution_note = reason

        self._add_audit_entry(
            task_id=request.task_id,
            action="approval_rejected",
            details={'approval_id': approval_id, 'by': rejected_by, 'reason': reason},
        )

        return True

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID."""
        return self._approvals.get(approval_id)

    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return [a for a in self._approvals.values()
                if a.status == ApprovalStatus.PENDING]

    # ── AUDIT LOG ──

    def _add_audit_entry(
        self,
        task_id: str,
        action: str,
        agent: str = "",
        details: Optional[Dict] = None,
        file_changes: Optional[List[str]] = None,
        validation_result: Optional[Dict] = None,
        risk_level: str = "",
        snapshot_id: str = "",
    ) -> AuditEntry:
        """Add an immutable audit log entry."""
        import uuid

        entry = AuditEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=self._now(),
            task_id=task_id,
            action=action,
            agent=agent,
            details=details or {},
            file_changes=file_changes or [],
            validation_result=validation_result,
            risk_level=risk_level,
            snapshot_id=snapshot_id,
        )

        self._audit_log.append(entry)
        return entry

    def log_task_created(self, task_id: str, agent: str, title: str) -> AuditEntry:
        return self._add_audit_entry(task_id, "task_created", agent, {'title': title})

    def log_patch_applied(self, task_id: str, file_path: str, patch_type: str) -> AuditEntry:
        return self._add_audit_entry(task_id, "patch_applied", details={
            'file': file_path, 'type': patch_type
        }, file_changes=[file_path])

    def log_validation_run(self, task_id: str, result: Dict) -> AuditEntry:
        return self._add_audit_entry(task_id, "validation_run", validation_result=result)

    def log_merge(self, task_id: str, merged_files: List[str], conflicts: int) -> AuditEntry:
        return self._add_audit_entry(task_id, "merge", details={
            'merged': len(merged_files), 'conflicts': conflicts
        }, file_changes=merged_files)

    def log_rollback(self, task_id: str, reason: str) -> AuditEntry:
        return self._add_audit_entry(task_id, "rollback", details={'reason': reason})

    def get_audit_log(
        self,
        task_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get audit log entries."""
        entries = self._audit_log
        if task_id:
            entries = [e for e in entries if e.task_id == task_id]

        return [
            {
                'id': e.id,
                'timestamp': e.timestamp,
                'task_id': e.task_id,
                'action': e.action,
                'agent': e.agent,
                'details': e.details,
                'file_changes': e.file_changes,
                'risk_level': e.risk_level,
            }
            for e in entries[-limit:]
        ]

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get summary of audit log."""
        from collections import Counter
        actions = Counter(e.action for e in self._audit_log)
        return {
            'total_entries': len(self._audit_log),
            'actions': dict(actions),
            'pending_approvals': len(self.get_pending_approvals()),
        }

    @staticmethod
    def _now() -> str:
        return time.strftime('%Y-%m-%dT%H:%M:%S')
