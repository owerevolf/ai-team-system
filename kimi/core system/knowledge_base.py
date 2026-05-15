"""
KnowledgeBase — Persistent storage for Project Manager data.

Uses JSON files in .agents/pm/ directory.
No external DB needed.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger


class KnowledgeBase:
    """
    Persistent knowledge storage.

    Stores:
    - File index
    - Symbol index
    - Decision log
    - Error log
    - Snapshots
    """

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.pm_dir = self.project_path / ".agents" / "pm"
        self.pm_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"KnowledgeBase initialized: {self.pm_dir}")

    def save_index(self, files: Dict, tech_stack: List[str], entry_points: List[str]) -> Path:
        """Save file index to disk."""
        index_file = self.pm_dir / "index.json"

        # Convert FileEntry objects to dicts
        serializable_files = {}
        for path, entry in files.items():
            serializable_files[path] = {
                "path": entry.path,
                "size": entry.size,
                "modified": entry.modified,
                "hash": entry.hash,
                "language": entry.language,
                "summary": entry.summary,
                "symbols": entry.symbols,
                "imports": entry.imports,
                "exported": entry.exported,
                "is_entry_point": entry.is_entry_point,
                "is_test": entry.is_test,
                "is_config": entry.is_config,
            }

        data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "tech_stack": tech_stack,
            "entry_points": entry_points,
            "files": serializable_files,
        }

        index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Index saved: {index_file}")
        return index_file

    def load_index(self) -> Optional[Dict]:
        """Load file index from disk."""
        index_file = self.pm_dir / "index.json"
        if not index_file.exists():
            return None

        try:
            data = json.loads(index_file.read_text(encoding="utf-8"))
            logger.info(f"Index loaded: {index_file}")
            return data
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return None

    def append_decision(self, decision: Dict) -> Path:
        """Append decision to log."""
        log_file = self.pm_dir / "decisions.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision, ensure_ascii=False) + "\n")

        return log_file

    def load_decisions(self, limit: int = 100) -> List[Dict]:
        """Load recent decisions."""
        log_file = self.pm_dir / "decisions.jsonl"
        if not log_file.exists():
            return []

        decisions = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        decisions.append(json.loads(line))
                    except Exception:
                        continue

        return decisions[-limit:]

    def append_error(self, error: Dict) -> Path:
        """Append error to log."""
        log_file = self.pm_dir / "errors.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(error, ensure_ascii=False) + "\n")

        return log_file

    def load_errors(self, limit: int = 100) -> List[Dict]:
        """Load recent errors."""
        log_file = self.pm_dir / "errors.jsonl"
        if not log_file.exists():
            return []

        errors = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        errors.append(json.loads(line))
                    except Exception:
                        continue

        return errors[-limit:]

    def save_snapshot(self, snapshot_id: str, snapshot_data: Dict) -> Path:
        """Save snapshot."""
        snap_dir = self.pm_dir / "snapshots"
        snap_dir.mkdir(exist_ok=True)

        snap_file = snap_dir / f"{snapshot_id}.json"
        snap_file.write_text(json.dumps(snapshot_data, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info(f"Snapshot saved: {snap_file}")
        return snap_file

    def list_snapshots(self) -> List[str]:
        """List available snapshot IDs."""
        snap_dir = self.pm_dir / "snapshots"
        if not snap_dir.exists():
            return []

        return sorted([f.stem for f in snap_dir.glob("*.json")])

    def load_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Load snapshot by ID."""
        snap_file = self.pm_dir / "snapshots" / f"{snapshot_id}.json"
        if not snap_file.exists():
            return None

        try:
            return json.loads(snap_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load snapshot {snapshot_id}: {e}")
            return None

    def clear_all(self) -> None:
        """Clear all PM data. Use with caution."""
        import shutil
        if self.pm_dir.exists():
            shutil.rmtree(self.pm_dir)
            self.pm_dir.mkdir(parents=True, exist_ok=True)
            logger.warning("KnowledgeBase cleared")
