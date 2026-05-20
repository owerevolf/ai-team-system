"""
Workspace Runtime — isolated workspace system.

Every execution happens in an isolated workspace.
No agent writes directly to the main repo.
"""

from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class WorkspaceState(Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    CLEANED = "cleaned"


@dataclass
class WorkspaceSnapshot:
    """A point-in-time snapshot of the workspace."""
    snapshot_id: str = ""
    timestamp: str = ""
    description: str = ""
    files_hash: Dict[str, str] = field(default_factory=dict)  # file -> md5

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = str(uuid.uuid4())[:8]
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


@dataclass
class Workspace:
    """An isolated workspace for task execution."""
    workspace_id: str = ""
    project_id: str = ""
    task_id: str = ""
    branch_name: str = ""
    state: str = WorkspaceState.CREATED.value
    created_at: str = ""
    base_path: str = ""
    active_agents: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    snapshots: List[WorkspaceSnapshot] = field(default_factory=list)

    def __post_init__(self):
        if not self.workspace_id:
            self.workspace_id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
        if not self.branch_name:
            self.branch_name = f"ai-workspace-{self.workspace_id}"


class WorkspaceRuntime:
    """
    Manages isolated workspaces for controlled execution.

    Each task gets its own workspace with:
    - isolated file operations
    - git branch (optional)
    - snapshots for rollback
    - cleanup after completion
    """

    def __init__(self, base_dir: str = ".ai-team/workspaces"):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._workspaces: Dict[str, Workspace] = {}

    def create_workspace(self, project_id: str, task_id: str,
                         project_root: str = ".") -> Workspace:
        """Create a new isolated workspace."""
        ws = Workspace(
            project_id=project_id,
            task_id=task_id,
        )
        ws.base_path = str(self._base_dir / f"{project_id}-{ws.workspace_id}")

        # Create workspace directory
        ws_path = Path(ws.base_path)
        ws_path.mkdir(parents=True, exist_ok=True)

        # Copy project files to workspace
        self._copy_project(project_root, ws.base_path)

        ws.state = WorkspaceState.ACTIVE.value
        self._workspaces[ws.workspace_id] = ws

        return ws

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        return self._workspaces.get(workspace_id)

    def create_snapshot(self, workspace_id: str,
                        description: str = "") -> Optional[WorkspaceSnapshot]:
        """Create a snapshot of the current workspace state."""
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return None

        snapshot = WorkspaceSnapshot(description=description)
        ws_path = Path(ws.base_path)

        for f in ws_path.rglob("*"):
            if f.is_file() and not f.name.startswith('.'):
                rel = str(f.relative_to(ws_path))
                content = f.read_bytes()
                import hashlib
                snapshot.files_hash[rel] = hashlib.md5(content).hexdigest()

        ws.snapshots.append(snapshot)
        return snapshot

    def restore_snapshot(self, workspace_id: str,
                         snapshot_id: str) -> bool:
        """Restore workspace to a previous snapshot."""
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return False

        snapshot = None
        for s in ws.snapshots:
            if s.snapshot_id == snapshot_id:
                snapshot = s
                break

        if not snapshot:
            return False

        # In a real implementation, this would restore file contents
        # For now, we mark the state
        ws.state = WorkspaceState.ROLLED_BACK.value
        return True

    def list_modified_files(self, workspace_id: str) -> List[str]:
        """List files modified in the workspace."""
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return []
        return list(ws.modified_files)

    def cleanup_workspace(self, workspace_id: str) -> bool:
        """Clean up a workspace after completion."""
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return False

        ws_path = Path(ws.base_path)
        if ws_path.exists():
            shutil.rmtree(ws_path)

        ws.state = WorkspaceState.CLEANED.value
        return True

    def list_workspaces(self, project_id: str = "") -> List[Workspace]:
        workspaces = list(self._workspaces.values())
        if project_id:
            workspaces = [w for w in workspaces if w.project_id == project_id]
        return workspaces

    def _copy_project(self, source: str, dest: str) -> None:
        """Copy project files to workspace, ignoring certain dirs."""
        ignore = {'.git', '__pycache__', 'node_modules', '.ai-team',
                  '.venv', 'venv', '.env'}
        src = Path(source)
        dst = Path(dest)

        if not src.exists():
            return

        for item in src.iterdir():
            if item.name in ignore:
                continue
            if item.is_file():
                shutil.copy2(item, dst / item.name)
            elif item.is_dir():
                shutil.copytree(item, dst / item.name,
                               dirs_exist_ok=True,
                               ignore=shutil.ignore_patterns(*ignore))
