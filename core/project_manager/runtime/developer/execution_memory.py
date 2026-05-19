"""
Execution Memory — stores execution timeline.

Foundation for replay and debugging.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionRecord:
    """A single record in the execution timeline."""
    record_id: str = ""
    timestamp: str = ""
    record_type: str = ""  # task_assignment, output, failure, retry, review, decision
    task_id: str = ""
    agent_id: str = ""
    plan_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def __post_init__(self):
        if not self.record_id:
            self.record_id = str(uuid.uuid4())[:8]
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "record_type": self.record_type,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "plan_id": self.plan_id,
            "data": self.data,
            "message": self.message,
        }


class ExecutionMemory:
    """
    Stores the full execution timeline.

    Used for:
    - replay (reconstruct what happened)
    - debugging (find where things went wrong)
    - audit (who did what and when)
    - UI (show execution progress)
    """

    def __init__(self, plan_id: str = "", project_id: str = ""):
        self.plan_id = plan_id
        self.project_id = project_id
        self._records: List[ExecutionRecord] = []
        self._created_at = datetime.utcnow().isoformat() + "Z"

    def record(self, record_type: str, message: str = "",
               task_id: str = "", agent_id: str = "",
               data: Optional[Dict[str, Any]] = None) -> ExecutionRecord:
        """Add a record to the timeline."""
        rec = ExecutionRecord(
            record_type=record_type,
            message=message,
            task_id=task_id,
            agent_id=agent_id,
            plan_id=self.plan_id,
            data=data or {},
        )
        self._records.append(rec)
        return rec

    def record_task_assignment(self, task_id: str, agent_id: str,
                                skills: Optional[List[str]] = None) -> ExecutionRecord:
        return self.record(
            "task_assignment",
            f"Task {task_id} assigned to {agent_id}",
            task_id=task_id,
            agent_id=agent_id,
            data={"skills": skills or []},
        )

    def record_task_start(self, task_id: str, agent_id: str) -> ExecutionRecord:
        return self.record(
            "task_start",
            f"Task {task_id} started by {agent_id}",
            task_id=task_id,
            agent_id=agent_id,
        )

    def record_task_complete(self, task_id: str, agent_id: str,
                              output: str = "") -> ExecutionRecord:
        return self.record(
            "task_complete",
            f"Task {task_id} completed by {agent_id}",
            task_id=task_id,
            agent_id=agent_id,
            data={"output": output},
        )

    def record_task_failure(self, task_id: str, agent_id: str,
                             error: str = "") -> ExecutionRecord:
        return self.record(
            "task_failure",
            f"Task {task_id} failed by {agent_id}: {error}",
            task_id=task_id,
            agent_id=agent_id,
            data={"error": error},
        )

    def record_review(self, task_id: str, passed: bool,
                      issues: Optional[List[str]] = None) -> ExecutionRecord:
        return self.record(
            "review",
            f"Review {'passed' if passed else 'blocked'} for {task_id}",
            task_id=task_id,
            data={"passed": passed, "issues": issues or []},
        )

    def record_decision(self, decision: str, context: str = "",
                        task_id: str = "") -> ExecutionRecord:
        return self.record(
            "decision",
            decision,
            task_id=task_id,
            data={"context": context},
        )

    def get_timeline(self, limit: int = 0) -> List[ExecutionRecord]:
        if limit > 0:
            return self._records[-limit:]
        return list(self._records)

    def get_records_by_type(self, record_type: str) -> List[ExecutionRecord]:
        return [r for r in self._records if r.record_type == record_type]

    def get_records_by_task(self, task_id: str) -> List[ExecutionRecord]:
        return [r for r in self._records if r.task_id == task_id]

    def get_records_by_agent(self, agent_id: str) -> List[ExecutionRecord]:
        return [r for r in self._records if r.agent_id == agent_id]

    def get_last_record(self) -> Optional[ExecutionRecord]:
        return self._records[-1] if self._records else None

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution."""
        types = {}
        for r in self._records:
            types[r.record_type] = types.get(r.record_type, 0) + 1
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "total_records": len(self._records),
            "created_at": self._created_at,
            "last_record": self._records[-1].timestamp if self._records else None,
            "record_types": types,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "created_at": self._created_at,
            "records": [r.to_dict() for r in self._records],
            "summary": self.get_summary(),
        }

    def save_to_file(self, path: str) -> None:
        """Save execution memory to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                     encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: str) -> ExecutionMemory:
        """Load execution memory from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        mem = cls(plan_id=data.get("plan_id", ""),
                  project_id=data.get("project_id", ""))
        for r in data.get("records", []):
            mem._records.append(ExecutionRecord(**r))
        return mem
