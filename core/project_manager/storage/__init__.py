"""
Storage Layer — persistent fact storage for ProjectManager.

Two backends:
- JSON (default, for compatibility)
- SQLite (Phase 2, for performance at scale)

Stores ONLY facts: file metadata, symbols, dependencies, timestamps.
Never stores AI opinions or speculative summaries.
"""

import json
import sqlite3
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.project_manager.models import FileEntry, Snapshot, RetrievalMetrics
from loguru import logger


class Storage:
    """
    Persistent storage for ProjectManager facts.

    Supports JSON (default) and SQLite backends.
    SQLite is recommended for large repositories (>1000 files).
    """

    def __init__(self, project_path: Path, backend: str = "json"):
        self.project_path = Path(project_path)
        self.backend = backend
        self.pm_dir = self.project_path / '.agents' / 'pm'
        self.pm_dir.mkdir(parents=True, exist_ok=True)

        if backend == "sqlite":
            self._db_path = self.pm_dir / 'pm.db'
            self._init_sqlite()

    # ── BACKEND: JSON (default) ──

    def _init_sqlite(self) -> None:
        """Initialize SQLite database."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    size INTEGER,
                    modified REAL,
                    hash TEXT,
                    language TEXT,
                    symbols TEXT,
                    imports TEXT,
                    exports TEXT,
                    is_entry_point INTEGER DEFAULT 0,
                    is_test INTEGER DEFAULT 0,
                    is_config INTEGER DEFAULT 0,
                    index_time REAL DEFAULT 0,
                    last_seen REAL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS dependencies (
                    source TEXT,
                    target TEXT,
                    PRIMARY KEY (source, target)
                );

                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    file_hashes TEXT,
                    total_files INTEGER,
                    total_symbols INTEGER,
                    added_files TEXT DEFAULT '[]',
                    removed_files TEXT DEFAULT '[]',
                    changed_files TEXT DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS task_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    agent TEXT,
                    action TEXT,
                    result TEXT
                );

                CREATE TABLE IF NOT EXISTS retrieval_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    agent TEXT,
                    timestamp TEXT,
                    files_returned INTEGER,
                    symbols_returned INTEGER,
                    context_chars INTEGER,
                    duration_ms REAL
                );

                CREATE INDEX IF NOT EXISTS idx_files_language ON files(language);
                CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash);
                CREATE INDEX IF NOT EXISTS idx_deps_source ON dependencies(source);
                CREATE INDEX IF NOT EXISTS idx_deps_target ON dependencies(target);
            """)

    # ── FILE INDEX ──

    def save_file_index(self, files: Dict[str, FileEntry]) -> None:
        """Save file index."""
        if self.backend == "sqlite":
            self._save_file_index_sqlite(files)
        else:
            self._save_file_index_json(files)

    def load_file_index(self) -> Optional[Dict[str, Any]]:
        """Load file index."""
        if self.backend == "sqlite":
            return self._load_file_index_sqlite()
        return self._load_file_index_json()

    def _save_file_index_json(self, files: Dict[str, FileEntry]) -> None:
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

    def _load_file_index_json(self) -> Optional[Dict[str, Any]]:
        return self._read_json('index.json')

    def _save_file_index_sqlite(self, files: Dict[str, FileEntry]) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM files")
            for path, entry in files.items():
                conn.execute(
                    """INSERT OR REPLACE INTO files
                    (path, size, modified, hash, language, symbols, imports, exports,
                     is_entry_point, is_test, is_config, index_time, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        entry.path, entry.size, entry.modified, entry.hash,
                        entry.language,
                        json.dumps(entry.symbols),
                        json.dumps(entry.imports),
                        json.dumps(entry.exports),
                        int(entry.is_entry_point), int(entry.is_test), int(entry.is_config),
                        entry.index_time, entry.last_seen,
                    ),
                )
            conn.commit()

    def _load_file_index_sqlite(self) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM files").fetchall()
            if not rows:
                return None
            result = {}
            for row in rows:
                result[row['path']] = {
                    'path': row['path'],
                    'size': row['size'],
                    'modified': row['modified'],
                    'hash': row['hash'],
                    'language': row['language'],
                    'symbols': json.loads(row['symbols'] or '[]'),
                    'imports': json.loads(row['imports'] or '[]'),
                    'exports': json.loads(row['exports'] or '[]'),
                    'is_entry_point': bool(row['is_entry_point']),
                    'is_test': bool(row['is_test']),
                    'is_config': bool(row['is_config']),
                    'index_time': row['index_time'],
                    'last_seen': row['last_seen'],
                }
            return result

    # ── DEPENDENCY GRAPH ──

    def save_dependency_graph(self, graph: Dict[str, List[str]]) -> None:
        """Save dependency graph."""
        if self.backend == "sqlite":
            self._save_dep_graph_sqlite(graph)
        else:
            self._save_dep_graph_json(graph)

    def load_dependency_graph(self) -> Optional[Dict[str, List[str]]]:
        """Load dependency graph."""
        if self.backend == "sqlite":
            return self._load_dep_graph_sqlite()
        return self._load_dep_graph_json()

    def _save_dep_graph_json(self, graph: Dict[str, List[str]]) -> None:
        self._write_json('dependencies.json', graph)

    def _load_dep_graph_json(self) -> Optional[Dict[str, List[str]]]:
        return self._read_json('dependencies.json')

    def _save_dep_graph_sqlite(self, graph: Dict[str, List[str]]) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM dependencies")
            for source, targets in graph.items():
                for target in targets:
                    conn.execute(
                        "INSERT OR REPLACE INTO dependencies (source, target) VALUES (?, ?)",
                        (source, target),
                    )
            conn.commit()

    def _load_dep_graph_sqlite(self) -> Optional[Dict[str, List[str]]]:
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute("SELECT source, target FROM dependencies").fetchall()
            graph: Dict[str, List[str]] = {}
            for source, target in rows:
                if source not in graph:
                    graph[source] = []
                graph[source].append(target)
            return graph if graph else None

    # ── SNAPSHOTS ──

    def save_snapshot(self, snapshot: Snapshot) -> str:
        """Save snapshot. Returns snapshot ID."""
        snap_id = snapshot.timestamp

        if self.backend == "sqlite":
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO snapshots
                    (id, timestamp, file_hashes, total_files, total_symbols,
                     added_files, removed_files, changed_files)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        snap_id, snap_id,
                        json.dumps(snapshot.file_hashes),
                        snapshot.total_files, snapshot.total_symbols,
                        json.dumps(snapshot.added_files),
                        json.dumps(snapshot.removed_files),
                        json.dumps(snapshot.changed_files),
                    ),
                )
                conn.commit()
        else:
            snap_dir = self.pm_dir / 'snapshots'
            snap_dir.mkdir(exist_ok=True)
            data = {
                'timestamp': snapshot.timestamp,
                'file_hashes': snapshot.file_hashes,
                'total_files': snapshot.total_files,
                'total_symbols': snapshot.total_symbols,
                'added_files': snapshot.added_files,
                'removed_files': snapshot.removed_files,
                'changed_files': snapshot.changed_files,
            }
            self._write_json(f'snapshots/{snap_id}.json', data)

        return snap_id

    def load_snapshot(self, snap_id: str) -> Optional[Dict[str, Any]]:
        """Load snapshot by ID."""
        if self.backend == "sqlite":
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snap_id,)).fetchone()
                if not row:
                    return None
                return {
                    'timestamp': row['timestamp'],
                    'file_hashes': json.loads(row['file_hashes'] or '{}'),
                    'total_files': row['total_files'],
                    'total_symbols': row['total_symbols'],
                    'added_files': json.loads(row['added_files'] or '[]'),
                    'removed_files': json.loads(row['removed_files'] or '[]'),
                    'changed_files': json.loads(row['changed_files'] or '[]'),
                }
        return self._read_json(f'snapshots/{snap_id}.json')

    def list_snapshots(self) -> List[str]:
        """List all snapshot IDs."""
        if self.backend == "sqlite":
            with sqlite3.connect(str(self._db_path)) as conn:
                rows = conn.execute(
                    "SELECT id FROM snapshots ORDER BY id DESC"
                ).fetchall()
                return [row[0] for row in rows]

        snap_dir = self.pm_dir / 'snapshots'
        if not snap_dir.exists():
            return []
        return sorted([f.stem for f in snap_dir.glob('*.json')], reverse=True)

    # ── TASK LOG ──

    def append_task_record(self, record: Dict[str, Any]) -> None:
        """Append task completion record."""
        if self.backend == "sqlite":
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    "INSERT INTO task_log (timestamp, agent, action, result) VALUES (?, ?, ?, ?)",
                    (
                        record.get('timestamp', ''),
                        record.get('agent', ''),
                        record.get('action', ''),
                        json.dumps(record.get('result', {})),
                    ),
                )
                conn.commit()
        else:
            log_file = self.pm_dir / 'tasks.jsonl'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def load_task_history(self, limit: int = 100) -> List[Dict]:
        """Load recent task records."""
        if self.backend == "sqlite":
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM task_log ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
                return [
                    {
                        'timestamp': row['timestamp'],
                        'agent': row['agent'],
                        'action': row['action'],
                        'result': json.loads(row['result'] or '{}'),
                    }
                    for row in rows
                ]

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

    # ── RETRIEVAL METRICS ──

    def save_retrieval_metrics(self, metrics: RetrievalMetrics) -> None:
        """Save retrieval metrics."""
        if self.backend == "sqlite":
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    """INSERT INTO retrieval_metrics
                    (query, agent, timestamp, files_returned, symbols_returned,
                     context_chars, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        metrics.query, metrics.agent, metrics.timestamp,
                        metrics.files_returned, metrics.symbols_returned,
                        metrics.context_chars, metrics.duration_ms,
                    ),
                )
                conn.commit()

    def load_retrieval_metrics(self, limit: int = 100) -> List[Dict]:
        """Load recent retrieval metrics."""
        if self.backend == "sqlite":
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM retrieval_metrics ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [dict(row) for row in rows]
        return []

    # ── MAINTENANCE ──

    def clear_all(self) -> None:
        """Clear all PM data. Use with caution."""
        if self.backend == "sqlite" and self._db_path.exists():
            self._db_path.unlink()
            self._init_sqlite()
        elif self.pm_dir.exists():
            shutil.rmtree(self.pm_dir)
            self.pm_dir.mkdir(parents=True, exist_ok=True)

    def migrate_to_sqlite(self) -> None:
        """Migrate existing JSON data to SQLite."""
        if self.backend == "sqlite":
            return

        logger.info("Migrating PM storage to SQLite...")
        self.backend = "sqlite"
        self._init_sqlite()

        # Migrate file index
        files_data = self._load_file_index_json()
        if files_data:
            files = {}
            for path, data in files_data.items():
                entry = FileEntry(
                    path=data['path'], size=data['size'],
                    modified=data['modified'], hash=data['hash'],
                    language=data['language'], symbols=data.get('symbols', []),
                    imports=data.get('imports', []), exports=data.get('exports', []),
                    is_entry_point=data.get('is_entry_point', False),
                    is_test=data.get('is_test', False),
                    is_config=data.get('is_config', False),
                )
                files[path] = entry
            self._save_file_index_sqlite(files)

        # Migrate dependencies
        deps = self._load_dep_graph_json()
        if deps:
            self._save_dep_graph_sqlite(deps)

        logger.info("Migration to SQLite complete")

    # ── JSON HELPERS ──

    def _write_json(self, filename: str, data: Any) -> None:
        filepath = self.pm_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def _read_json(self, filename: str) -> Optional[Any]:
        filepath = self.pm_dir / filename
        if not filepath.exists():
            return None
        try:
            return json.loads(filepath.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return None
