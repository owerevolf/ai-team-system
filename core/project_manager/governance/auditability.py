"""
P15 — Platform Auditability.

Tracks all security-relevant events for audit readiness:
- Policy violations
- Unsafe execution attempts
- Protected resource access
- Workflow overrides
- Approval bypass attempts
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class AuditEventType(Enum):
    POLICY_VIOLATION = "policy_violation"
    UNSAFE_EXECUTION = "unsafe_execution"
    PROTECTED_ACCESS = "protected_access"
    WORKFLOW_OVERRIDE = "workflow_override"
    APPROVAL_BYPASS = "approval_bypass"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"
    AUTH_FAILURE = "auth_failure"


@dataclass
class AuditEntry:
    """A single audit log entry."""
    event_id: str
    event_type: AuditEventType
    timestamp: float
    actor: str  # who performed the action
    action: str  # what was attempted
    target: str  # what was targeted
    result: str  # allowed, denied, blocked
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # info, warning, critical


class PlatformAuditability:
    """
    Audit log for all security-relevant events.
    Immutable — entries cannot be modified or deleted.
    """

    def __init__(self, max_entries: int = 100000):
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def log(self, event_type: AuditEventType, actor: str, action: str,
            target: str, result: str, details: Optional[Dict[str, Any]] = None,
            severity: str = "info") -> AuditEntry:
        """Log an audit event."""
        import uuid
        entry = AuditEntry(
            event_id=str(uuid.uuid4())[:12],
            event_type=event_type,
            timestamp=time.time(),
            actor=actor,
            action=action,
            target=target,
            result=result,
            details=details or {},
            severity=severity,
        )

        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

        return entry

    def get_entries(self, event_type: Optional[AuditEventType] = None,
                    actor: Optional[str] = None, target: Optional[str] = None,
                    severity: Optional[str] = None,
                    since: float = 0.0, limit: int = 100) -> List[AuditEntry]:
        """Get audit entries, optionally filtered."""
        entries = self._entries
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        if actor:
            entries = [e for e in entries if e.actor == actor]
        if target:
            entries = [e for e in entries if target in e.target]
        if severity:
            entries = [e for e in entries if e.severity == severity]
        if since > 0:
            entries = [e for e in entries if e.timestamp >= since]
        return entries[-limit:]

    def get_violations(self, limit: int = 100) -> List[AuditEntry]:
        """Get all policy violation entries."""
        return self.get_entries(event_type=AuditEventType.POLICY_VIOLATION, limit=limit)

    def get_unsafe_attempts(self, limit: int = 100) -> List[AuditEntry]:
        """Get all unsafe execution attempts."""
        return self.get_entries(event_type=AuditEventType.UNSAFE_EXECUTION, limit=limit)

    def get_bypass_attempts(self, limit: int = 100) -> List[AuditEntry]:
        """Get all approval bypass attempts."""
        return self.get_entries(event_type=AuditEventType.APPROVAL_BYPASS, limit=limit)

    def get_stats(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        by_result = defaultdict(int)
        for e in self._entries:
            by_type[e.event_type.value] += 1
            by_severity[e.severity] += 1
            by_result[e.result] += 1

        return {
            'total_entries': len(self._entries),
            'by_type': dict(by_type),
            'by_severity': dict(by_severity),
            'by_result': dict(by_result),
        }
