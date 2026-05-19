"""
Brain Store — JSON persistence layer for ProjectBrain.

Simple. Stable. No database. No Redis. Just files.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .project_brain import ProjectBrain, brain_to_dict, brain_from_dict


class BrainStore:
    """
    Persistence layer for ProjectBrain.

    Storage layout:
        {storage_dir}/
            {project_id}/
                brain.json          — current brain state
                snapshots/
                    {timestamp}.json  — point-in-time snapshots
    """

    def __init__(self, storage_dir: str = ".ai-team/brains"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _brain_path(self, project_id: str) -> Path:
        return self._storage_dir / project_id / "brain.json"

    def _snapshots_dir(self, project_id: str) -> Path:
        return self._storage_dir / project_id / "snapshots"

    def create_brain(self, project_id: str, project_name: str = "") -> ProjectBrain:
        """Create a new empty brain for a project."""
        now = datetime.utcnow().isoformat() + "Z"
        brain = ProjectBrain(
            project_id=project_id,
            project_name=project_name or project_id,
            created_at=now,
            updated_at=now,
        )
        self.save_brain(brain)
        logger.info(f"Brain created for project: {project_id}")
        return brain

    def load_brain(self, project_id: str) -> Optional[ProjectBrain]:
        """Load a brain from disk. Returns None if not found."""
        path = self._brain_path(project_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            brain = brain_from_dict(data)
            logger.debug(f"Brain loaded: {project_id}")
            return brain
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load brain {project_id}: {e}")
            return None

    def save_brain(self, brain: ProjectBrain) -> None:
        """Save a brain to disk."""
        brain.touch()
        path = self._brain_path(brain.project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = brain_to_dict(brain)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug(f"Brain saved: {brain.project_id}")

    def update_brain(self, project_id: str, **kwargs) -> Optional[ProjectBrain]:
        """Update specific fields of a brain and save."""
        brain = self.load_brain(project_id)
        if not brain:
            return None
        for key, value in kwargs.items():
            if hasattr(brain, key):
                setattr(brain, key, value)
        self.save_brain(brain)
        return brain

    def snapshot_brain(self, project_id: str) -> Optional[str]:
        """Create a point-in-time snapshot. Returns snapshot path."""
        brain = self.load_brain(project_id)
        if not brain:
            return None
        snapshots_dir = self._snapshots_dir(project_id)
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snap_path = snapshots_dir / f"{timestamp}.json"
        data = brain_to_dict(brain)
        snap_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"Brain snapshot: {project_id} @ {timestamp}")
        return str(snap_path)

    def list_brains(self) -> List[Dict[str, str]]:
        """List all saved brains."""
        results = []
        if not self._storage_dir.exists():
            return results
        for d in sorted(self._storage_dir.iterdir()):
            if d.is_dir() and (d / "brain.json").exists():
                brain = self.load_brain(d.name)
                if brain:
                    results.append({
                        "project_id": brain.project_id,
                        "project_name": brain.project_name,
                        "updated_at": brain.updated_at,
                    })
        return results

    def delete_brain(self, project_id: str) -> bool:
        """Delete a brain and all its snapshots."""
        import shutil
        path = self._brain_path(project_id).parent
        if path.exists():
            shutil.rmtree(path)
            logger.info(f"Brain deleted: {project_id}")
            return True
        return False

    def brain_exists(self, project_id: str) -> bool:
        return self._brain_path(project_id).exists()
