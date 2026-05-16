"""
Workspace UX Module (P6) — Phase 8

Clean, simple workspace state management for the browser UI.
NO enterprise overload. Just the essentials:
  - Workspace state (current project, open files, active views)
  - Task panel state
  - Project map (simple tree)
  - Workflow timeline
  - Approval queue
  - Diff preview data
  - Rollback state
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceView:
    """Represents a UI view/panel in the workspace."""
    view_id: str
    name: str
    view_type: str           # project_map | task_panel | timeline | approval_queue | diff_preview | health_dashboard
    visible: bool = True
    position: str = "main"   # sidebar | main | overlay
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "view_id": self.view_id,
            "name": self.name,
            "view_type": self.view_type,
            "visible": self.visible,
            "position": self.position,
            "data": self.data,
        }


@dataclass
class FileTreeNode:
    """A node in the project file tree."""
    name: str
    path: str
    is_dir: bool = False
    children: list[dict] = field(default_factory=list)
    health_indicator: str = "none"  # none | healthy | warning | error

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "is_dir": self.is_dir,
            "children": self.children,
            "health_indicator": self.health_indicator,
        }


@dataclass
class TimelineEvent:
    """An event in the workflow timeline."""
    event_id: str
    timestamp: str
    event_type: str          # import | analysis | workflow_start | workflow_end | approval | rollback | error
    title: str
    description: str = ""
    status: str = "completed"  # completed | in_progress | failed | pending

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Workspace UX Manager
# ---------------------------------------------------------------------------

class WorkspaceUX:
    """
    Manages the clean workspace state for the browser UI.

    Usage:
        ws = WorkspaceUx("/path/to/project")
        ws.set_current_view("project_map")
        project_map = ws.build_project_map()
    """

    def __init__(self, project_path: Optional[str] = None) -> None:
        self.project_path = project_path
        self._current_view: str = "project_map"
        self._open_files: list[str] = []
        self._timeline: list[TimelineEvent] = []
        self._views: dict[str, WorkspaceView] = {}
        self._setup_default_views()

    def _setup_default_views(self) -> None:
        """Create the default set of workspace views."""
        defaults = [
            WorkspaceView("v-project-map", "Project Map", "project_map", position="sidebar"),
            WorkspaceView("v-task-panel", "Tasks", "task_panel", position="sidebar"),
            WorkspaceView("v-health", "Health Dashboard", "health_dashboard", position="main"),
            WorkspaceView("v-timeline", "Timeline", "timeline", position="main"),
            WorkspaceView("v-approvals", "Approvals", "approval_queue", position="overlay", visible=False),
            WorkspaceView("v-diff", "Diff Preview", "diff_preview", position="overlay", visible=False),
        ]
        for v in defaults:
            self._views[v.view_id] = v

    # -- View management -----------------------------------------------------

    def set_current_view(self, view_id: str) -> bool:
        """Set the currently active view."""
        if view_id in self._views:
            self._current_view = view_id
            return True
        # Also allow setting by view_type
        for vid, v in self._views.items():
            if v.view_type == view_id:
                self._current_view = vid
                return True
        return False

    def get_current_view(self) -> Optional[dict[str, Any]]:
        """Get the current view state."""
        for vid, v in self._views.items():
            if vid == self._current_view or v.view_type == self._current_view:
                return v.to_dict()
        return None

    def toggle_view(self, view_id: str) -> bool:
        """Toggle visibility of a view."""
        if view_id in self._views:
            self._views[view_id].visible = not self._views[view_id].visible
            return True
        return False

    def get_sidebar_views(self) -> list[dict[str, Any]]:
        """Get all sidebar views."""
        return [v.to_dict() for v in self._views.values() if v.position == "sidebar" and v.visible]

    def get_main_views(self) -> list[dict[str, Any]]:
        """Get all main area views."""
        return [v.to_dict() for v in self._views.values() if v.position == "main" and v.visible]

    def get_overlay_views(self) -> list[dict[str, Any]]:
        """Get all visible overlay views."""
        return [v.to_dict() for v in self._views.values() if v.position == "overlay" and v.visible]

    # -- Project map ---------------------------------------------------------

    def build_project_map(self, max_depth: int = 3) -> dict[str, Any]:
        """
        Build a simple project file tree for the sidebar.

        Args:
            max_depth: Maximum directory depth to scan.

        Returns:
            Dict with tree structure: {name, path, is_dir, children}
        """
        if not self.project_path or not os.path.isdir(self.project_path):
            return {"name": "No project", "path": "", "is_dir": True, "children": []}

        exclude = {".git", "__pycache__", "node_modules", "venv", ".venv", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", ".next", ".nuxt", "target"}

        def _scan(path: str, depth: int) -> list[dict]:
            if depth > max_depth:
                return []
            items = []
            try:
                entries = sorted(os.listdir(path))
            except PermissionError:
                return []
            for entry in entries:
                if entry in exclude:
                    continue
                full = os.path.join(path, entry)
                rel = os.path.relpath(full, self.project_path)
                if os.path.isdir(full):
                    children = _scan(full, depth + 1)
                    items.append({
                        "name": entry,
                        "path": rel,
                        "is_dir": True,
                        "children": children,
                    })
                else:
                    items.append({
                        "name": entry,
                        "path": rel,
                        "is_dir": False,
                        "children": [],
                    })
            return items

        return {
            "name": os.path.basename(self.project_path) or self.project_path,
            "path": self.project_path,
            "is_dir": True,
            "children": _scan(self.project_path, 0),
        }

    # -- Timeline -----------------------------------------------------------

    def add_timeline_event(
        self,
        event_type: str,
        title: str,
        description: str = "",
        status: str = "completed",
    ) -> TimelineEvent:
        """Add an event to the workflow timeline."""
        import uuid
        event = TimelineEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            title=title,
            description=description,
            status=status,
        )
        self._timeline.append(event)
        # Keep timeline manageable: max 100 events
        if len(self._timeline) > 100:
            self._timeline = self._timeline[-100:]
        return event

    def get_timeline(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent timeline events."""
        return [e.to_dict() for e in self._timeline[-limit:]]

    # -- Open files ---------------------------------------------------------

    def open_file(self, file_path: str) -> list[str]:
        """Add a file to the open files list."""
        if file_path not in self._open_files:
            self._open_files.append(file_path)
            # Max 10 open files
            if len(self._open_files) > 10:
                self._open_files = self._open_files[-10:]
        return list(self._open_files)

    def close_file(self, file_path: str) -> list[str]:
        """Remove a file from the open files list."""
        if file_path in self._open_files:
            self._open_files.remove(file_path)
        return list(self._open_files)

    def get_open_files(self) -> list[str]:
        """Get currently open files."""
        return list(self._open_files)

    # -- Rollback state -----------------------------------------------------

    def set_rollback_point(self, checkpoint_hash: str, label: str = "") -> dict[str, Any]:
        """Set a rollback point for the UI."""
        return {
            "checkpoint_hash": checkpoint_hash,
            "label": label,
            "available": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def clear_rollback_point(self) -> None:
        """Clear the current rollback point."""
        pass  # UI state only; actual rollback handled by sandbox

    # -- Full workspace state -----------------------------------------------

    def get_workspace_state(self) -> dict[str, Any]:
        """Get the complete workspace state for the browser."""
        return {
            "project_path": self.project_path,
            "current_view": self._current_view,
            "sidebar_views": self.get_sidebar_views(),
            "main_views": self.get_main_views(),
            "overlay_views": self.get_overlay_views(),
            "open_files": self._open_files,
            "timeline": self.get_timeline(limit=10),
        }
