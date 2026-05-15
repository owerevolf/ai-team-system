"""
Storage Layer — persistent fact storage for ProjectManager.

Uses JSON files in .agents/pm/ directory.
Stores ONLY facts: file metadata, symbols, dependencies, timestamps.
Never stores AI opinions or speculative summaries.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.project_manager.models import FileEntry, Snapshot


class Storage:
    """Persistent storage for ProjectManager facts."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.pm_dir = self.project_path / '.agents' / 'pm'
        self.pm_dir.mkdir(parents=True, exist_ok=True)

    def save_file_index(self, files: Dict[str, FileEntry]) -> None:
        """Save file index as JSON."""
        data = {}
        for path, entry in files.items():
            data[path] = {
                'path': entry.path,
                'size': entry.size,
                'modified': entry.modified,
                'hash': entry.hash,
                'language': entry.language,
                'symbols': entry.symbols,
                'imports': entry.imports,
                'exports': entry.exports,
                'is_entry_point': entry.is_entry_point,
                'is_test': entry.is_test,
                'is_config': entry.is_config,
            }
        self._write_json('index.json', data)

    def load_file_index(self) -> Optional[Dict[str, Any]]:
        """Load file index from JSON."""
        return self._read_json('index.json')

    def save_dependency_graph(self, graph: Dict[str, List[str]]) -> None:
        """Save dependency graph."""
        self._write_json('dependencies.json', graph)

    def load_dependency_graph(self) -> Optional[Dict[str, List[str]]]:
        """Load dependency graph."""
        return self._read_json('dependencies.json')

    def save_snapshot(self, snapshot: Snapshot) -> str:
        """Save snapshot. Returns snapshot ID."""
        snap_id = snapshot.timestamp
        snap_dir = self.pm_dir / 'snapshots'
        snap_dir.mkdir(exist_ok=True)

        data = {
            'timestamp': snapshot.timestamp,
            'file_hashes': snapshot.file_hashes,
            'total_files': snapshot.total_files,
            'total_symbols': snapshot.total_symbols,
        }
        self._write_json(f'snapshots/{snap_id}.json', data)
        return snap_id

    def load_snapshot(self, snap_id: str) -> Optional[Dict[str, Any]]:
        """Load snapshot by ID."""
        return self._read_json(f'snapshots/{snap_id}.json')

    def list_snapshots(self) -> List[str]:
        """List all snapshot IDs."""
        snap_dir = self.pm_dir / 'snapshots'
        if not snap_dir.exists():
            return []
        return sorted([f.stem for f in snap_dir.glob('*.json')])

    def append_task_record(self, record: Dict[str, Any]) -> None:
        """Append task completion record to JSONL log."""
        log_file = self.pm_dir / 'tasks.jsonl'
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def load_task_history(self, limit: int = 100) -> List[Dict]:
        """Load recent task records."""
        log_file = self.pm_dir / 'tasks.jsonl'
        if not log_file.exists():
            return []
        records = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records[-limit:]

    def clear_all(self) -> None:
        """Clear all PM data. Use with caution."""
        if self.pm_dir.exists():
            shutil.rmtree(self.pm_dir)
            self.pm_dir.mkdir(parents=True, exist_ok=True)

    def _write_json(self, filename: str, data: Any) -> None:
        """Write data to JSON file."""
        filepath = self.pm_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def _read_json(self, filename: str) -> Optional[Any]:
        """Read data from JSON file."""
        filepath = self.pm_dir / filename
        if not filepath.exists():
            return None
        try:
            return json.loads(filepath.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return None
