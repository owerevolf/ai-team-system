"""
unified_workspace.py — Unified Workspace Runtime.

Purpose: One workspace experience that grows with the user.
NOT separate applications — one system.

Connects:
- learning mode
- guided mode
- engineering mode
- developer mode

Into: ONE coherent workspace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class WorkspaceState:
    """Current workspace state."""
    current_view: str = "conversation"  # conversation, project, review, settings
    active_project: str = ""
    active_mode: str = "learning"  # learning, guided, engineering
    sidebar_collapsed: bool = False
    right_panel: str = "context"  # context, memory, orchestration, none
    recent_conversations: List[Dict[str, str]] = field(default_factory=list)
    pinned_items: List[str] = field(default_factory=list)


class UnifiedWorkspace:
    """
    Unified workspace runtime.
    One workspace that adapts to the user's level and intent.
    """

    # Available views per mode
    VIEWS = {
        "learning": ["conversation", "project", "help"],
        "guided": ["conversation", "project", "review", "help"],
        "engineering": ["conversation", "project", "review", "memory", "settings"],
    }

    # Available right panels per mode
    PANELS = {
        "learning": ["context", "help", "none"],
        "guided": ["context", "memory", "orchestration", "none"],
        "engineering": ["context", "memory", "orchestration", "git", "none"],
    }

    def __init__(self, mode: str = "learning"):
        self._state = WorkspaceState(active_mode=mode)
        self._view_history: List[str] = []

    @property
    def state(self) -> WorkspaceState:
        return self._state

    def switch_mode(self, new_mode: str) -> None:
        """Switch workspace mode."""
        if new_mode not in self.VIEWS:
            logger.warning(f"Unknown mode: {new_mode}")
            return

        old_mode = self._state.active_mode
        self._state.active_mode = new_mode

        # Reset view to first available
        available_views = self.VIEWS.get(new_mode, [])
        if available_views and self._state.current_view not in available_views:
            self._state.current_view = available_views[0]

        # Reset right panel
        available_panels = self.PANELS.get(new_mode, [])
        if available_panels and self._state.right_panel not in available_panels:
            self._state.right_panel = available_panels[0]

        logger.info(f"Workspace mode: {old_mode} -> {new_mode}")

    def switch_view(self, view: str) -> bool:
        """Switch to a different view."""
        available = self.VIEWS.get(self._state.active_mode, [])
        if view not in available:
            logger.warning(f"View '{view}' not available in {self._state.active_mode} mode")
            return False

        self._view_history.append(self._state.current_view)
        self._state.current_view = view
        return True

    def get_available_views(self) -> List[str]:
        """Get available views for current mode."""
        return self.VIEWS.get(self._state.active_mode, [])

    def get_available_panels(self) -> List[str]:
        """Get available right panels for current mode."""
        return self.PANELS.get(self._state.active_mode, [])

    def toggle_sidebar(self) -> None:
        self._state.sidebar_collapsed = not self._state.sidebar_collapsed

    def set_right_panel(self, panel: str) -> bool:
        available = self.get_available_panels()
        if panel not in available:
            return False
        self._state.right_panel = panel
        return True

    def add_recent_conversation(self, title: str, conversation_id: str) -> None:
        """Add a recent conversation."""
        self._state.recent_conversations.insert(0, {
            "title": title,
            "id": conversation_id,
        })
        # Keep last 10
        self._state.recent_conversations = self._state.recent_conversations[:10]

    def get_workspace_summary(self) -> str:
        """Get a summary of the current workspace state."""
        lines = [
            f"# Workspace",
            f"Mode: {self._state.active_mode}",
            f"View: {self._state.current_view}",
            f"Project: {self._state.active_project or 'None'}",
            f"Sidebar: {'collapsed' if self._state.sidebar_collapsed else 'expanded'}",
            f"Right panel: {self._state.right_panel}",
            "",
            f"## Available Views",
        ]
        for v in self.get_available_views():
            marker = "→" if v == self._state.current_view else " "
            lines.append(f"  {marker} {v}")

        lines.append("")
        lines.append("## Available Panels")
        for p in self.get_available_panels():
            marker = "→" if p == self._state.right_panel else " "
            lines.append(f"  {marker} {p}")

        return "\n".join(lines)
