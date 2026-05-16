"""
Lightweight Session Memory (P11) — Phase 8

Simple engineering continuity tracker. Stores current work state in
.ai-team/session.json within the project directory.

Not a giant AI memory system — just enough context to resume work:
active tasks, pending workflows, approvals, file changes, and branch state.
"""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionMemory:
    """Tracks current work state for engineering continuity."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.session_dir = os.path.join(project_path, ".ai-team")
        self.session_file = os.path.join(self.session_dir, "session.json")
        os.makedirs(self.session_dir, exist_ok=True)
        if not os.path.exists(self.session_file):
            self._write({
                "session": None,
                "tasks": [],
                "workflows": [],
                "approvals": [],
                "changes": [],
                "branch": {"branch": "", "commit_hash": ""},
            })

    # -- internal helpers ---------------------------------------------------

    def _read(self) -> dict:
        try:
            with open(self.session_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {
                "session": None,
                "tasks": [],
                "workflows": [],
                "approvals": [],
                "changes": [],
                "branch": {"branch": "", "commit_hash": ""},
            }

    def _write(self, data: dict) -> None:
        """Atomic write: dump to temp file, then rename into place."""
        fd, tmp_path = tempfile.mkstemp(
            dir=self.session_dir, suffix=".tmp", prefix="session_"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.session_file)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _save(self, data: dict) -> None:
        self._write(data)

    # -- session lifecycle --------------------------------------------------

    def start_session(self, user: str = "default") -> dict:
        data = self._read()
        session = {
            "id": str(uuid.uuid4()),
            "user": user,
            "start_time": _now(),
            "end_time": None,
            "status": "active",
        }
        data["session"] = session
        self._save(data)
        return session

    def get_session(self) -> dict | None:
        data = self._read()
        return data.get("session")

    def end_session(self) -> dict | None:
        data = self._read()
        session = data.get("session")
        if session:
            session["end_time"] = _now()
            session["status"] = "ended"
            data["session"] = session
            self._save(data)
        return session

    # -- tasks --------------------------------------------------------------

    def add_task(self, task: dict) -> dict:
        data = self._read()
        data["tasks"].append(task)
        self._save(data)
        return task

    def update_task(self, task_id: str, **kwargs) -> dict | None:
        data = self._read()
        for task in data["tasks"]:
            if task.get("id") == task_id:
                task.update(kwargs)
                self._save(data)
                return task
        return None

    def get_tasks(self, status: str | None = None) -> list:
        data = self._read()
        tasks = data.get("tasks", [])
        if status:
            return [t for t in tasks if t.get("status") == status]
        return list(tasks)

    # -- workflows ----------------------------------------------------------

    def add_pending_workflow(self, workflow: dict) -> dict:
        data = self._read()
        data["workflows"].append(workflow)
        self._save(data)
        return workflow

    def update_workflow(self, workflow_id: str, **kwargs) -> dict | None:
        data = self._read()
        for wf in data["workflows"]:
            if wf.get("id") == workflow_id:
                wf.update(kwargs)
                self._save(data)
                return wf
        return None

    def get_pending_workflows(self) -> list:
        data = self._read()
        return [w for w in data.get("workflows", []) if w.get("status") == "pending"]

    # -- approvals ----------------------------------------------------------

    def add_approval(self, approval: dict) -> dict:
        data = self._read()
        data["approvals"].append(approval)
        self._save(data)
        return approval

    def resolve_approval(self, approval_id: str, decision: str, reason: str = "") -> dict | None:
        data = self._read()
        for ap in data["approvals"]:
            if ap.get("id") == approval_id:
                ap["status"] = decision
                ap["resolved_at"] = _now()
                if reason:
                    ap["reason"] = reason
                self._save(data)
                return ap
        return None

    def get_pending_approvals(self) -> list:
        data = self._read()
        return [a for a in data.get("approvals", []) if a.get("status") == "pending"]

    # -- file changes -------------------------------------------------------

    def record_change(self, file_path: str, change_type: str, task_id: str | None = None) -> dict:
        data = self._read()
        change = {
            "file_path": file_path,
            "change_type": change_type,
            "task_id": task_id,
            "timestamp": _now(),
        }
        data["changes"].append(change)
        self._save(data)
        return change

    def get_recent_changes(self, limit: int = 20) -> list:
        data = self._read()
        changes = data.get("changes", [])
        return changes[-limit:]

    # -- branch state -------------------------------------------------------

    def set_branch_state(self, branch: str, commit_hash: str = "") -> dict:
        data = self._read()
        state = {"branch": branch, "commit_hash": commit_hash}
        data["branch"] = state
        self._save(data)
        return state

    def get_branch_state(self) -> dict:
        data = self._read()
        return data.get("branch", {"branch": "", "commit_hash": ""})

    # -- summary -----------------------------------------------------------

    def get_summary(self) -> dict:
        data = self._read()
        return {
            "session": data.get("session"),
            "open_tasks": [
                t for t in data.get("tasks", [])
                if t.get("status") in ("pending", "running")
            ],
            "pending_workflows": [
                w for w in data.get("workflows", [])
                if w.get("status") == "pending"
            ],
            "pending_approvals": [
                a for a in data.get("approvals", [])
                if a.get("status") == "pending"
            ],
            "recent_changes": data.get("changes", [])[-20:],
            "branch_state": data.get("branch", {"branch": "", "commit_hash": ""}),
        }
