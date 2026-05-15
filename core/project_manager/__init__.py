"""
ProjectManager — passive observation kernel for the project.

NOT an AI agent. NOT an orchestrator. NOT a decision maker.
Stores facts about the project. Provides context on demand.

Usage:
    pm = ProjectManager(Path("/path/to/project"))
    pm.index_project()

    context = pm.query(agent="backend", question="What endpoints exist?")
    pm.update(agent="backend", action="task_completed", result={...})
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from core.project_manager.models import FileEntry, Snapshot
from core.project_manager.indexers import FileIndexer
from core.project_manager.indexers.dependency_graph import DependencyGraph
from core.project_manager.extractors import SymbolExtractor
from core.project_manager.storage import Storage
from core.project_manager.events import EventBus, FILE_INDEXED, INDEX_UPDATED, CONTEXT_REQUESTED, AGENT_TASK_COMPLETED, SNAPSHOT_CREATED
from core.project_manager.query import QueryEngine


class ProjectManager:
    """
    Passive project observation kernel.

    Responsibilities:
    - Index files (path, size, hash, language)
    - Extract symbols (classes, functions, imports)
    - Build dependency graph
    - Answer context queries with budget enforcement
    - Track task history

    NOT responsible for:
    - Making decisions
    - Writing code
    - Managing agents
    - Self-improvement
    """

    def __init__(self, project_path: Path, max_context_chars: int = 12000):
        self.project_path = Path(project_path).resolve()
        self._indexer = FileIndexer(self.project_path)
        self._extractor = SymbolExtractor()
        self._dep_graph = DependencyGraph(self.project_path)
        self._storage = Storage(self.project_path)
        self._events = EventBus()
        self._query_engine = QueryEngine(max_context_chars=max_context_chars)

        # State
        self.files: Dict[str, FileEntry] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self._indexed = False
        self._index_time: Optional[str] = None

        logger.info(f"ProjectManager initialized: {self.project_path}")

    @property
    def is_indexed(self) -> bool:
        return self._indexed

    # ── INDEXING ──────────────────────────────────────────────

    def index_project(self) -> Dict[str, Any]:
        """
        Full project scan and index.
        Returns stats dict.
        """
        logger.info(f"Indexing project: {self.project_path}")
        start = time.time()

        # 1. Scan files
        self.files = self._indexer.scan()
        self._events.emit(FILE_INDEXED, {'count': len(self.files)})

        # 2. Extract symbols and imports for each file
        total_symbols = 0
        for rel_path, entry in self.files.items():
            try:
                full_path = self.project_path / rel_path
                content = full_path.read_text(encoding='utf-8', errors='ignore')

                # Symbols
                symbols = self._extractor.extract_symbols(content, entry.language)
                for sym in symbols:
                    sym.file_path = rel_path
                entry.symbols = [{'name': s.name, 'type': s.type, 'line': s.line, 'signature': s.signature} for s in symbols]
                total_symbols += len(symbols)

                # Imports
                entry.imports = self._extractor.extract_imports(content, entry.language)

                # Exports
                entry.exports = self._extractor.extract_exports(content, entry.language)

                # Classify
                entry.is_entry_point = self._is_entry_point(rel_path, content)
                entry.is_test = 'test' in rel_path.lower() or rel_path.startswith('tests/')
                entry.is_config = self._is_config(rel_path)

            except Exception as e:
                logger.warning(f"Failed to process {rel_path}: {e}")
                continue

        # 3. Build dependency graph
        self.dependencies = self._dep_graph.build(self.files)

        # 4. Mark as indexed
        self._indexed = True
        self._index_time = datetime.now().isoformat()

        # 5. Persist
        self._storage.save_file_index(self.files)
        self._storage.save_dependency_graph(self.dependencies)

        # 6. Create initial snapshot
        snap = self._create_snapshot()
        self._events.emit(SNAPSHOT_CREATED, {'id': snap})

        elapsed = time.time() - start
        stats = {
            'total_files': len(self.files),
            'total_symbols': total_symbols,
            'total_dependencies': sum(len(v) for v in self.dependencies.values()),
            'elapsed_seconds': round(elapsed, 2),
        }
        self._events.emit(INDEX_UPDATED, stats)
        logger.info(f"Indexing complete: {stats}")
        return stats

    def reindex_file(self, rel_path: str) -> bool:
        """Reindex a single file after change."""
        if rel_path not in self.files:
            return False

        full_path = self.project_path / rel_path
        if not full_path.exists():
            del self.files[rel_path]
            self.dependencies = self._dep_graph.build(self.files)
            return True

        try:
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            entry = self.files[rel_path]

            entry.symbols = [{'name': s.name, 'type': s.type, 'line': s.line, 'signature': s.signature}
                           for s in self._extractor.extract_symbols(content, entry.language)]
            entry.imports = self._extractor.extract_imports(content, entry.language)
            entry.exports = self._extractor.extract_exports(content, entry.language)
            entry.hash = __import__('hashlib').sha256(content.encode()).hexdigest()[:16]
            entry.size = full_path.stat().st_size
            entry.modified = full_path.stat().st_mtime

            # Rebuild dependencies incrementally
            self.dependencies = self._dep_graph.build(self.files)
            self._storage.save_file_index(self.files)
            self._storage.save_dependency_graph(self.dependencies)
            return True

        except Exception as e:
            logger.error(f"Reindex failed for {rel_path}: {e}")
            return False

    # ── QUERY ─────────────────────────────────────────────────

    def query(self, agent: str, question: str, max_tokens: int = 3000) -> str:
        """
        Answer a context query. Enforces context budget.

        Args:
            agent: Which agent is asking
            question: What they want to know
            max_tokens: Token budget (x4 = char budget)

        Returns:
            Filtered context string
        """
        if not self._indexed:
            return "Project not indexed yet."

        max_chars = max_tokens * 4
        self._events.emit(CONTEXT_REQUESTED, {'agent': agent, 'question': question[:100]})

        return self._query_engine.query(self.files, question, max_chars=max_chars)

    # ── UPDATE ────────────────────────────────────────────────

    def update(self, agent: str, action: str, result: Dict[str, Any]) -> None:
        """
        Record an agent action result.

        Args:
            agent: Which agent
            action: What they did (task_completed, file_created, error)
            result: Action details
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent,
            'action': action,
            'result': result,
        }
        self._storage.append_task_record(record)
        self._events.emit(AGENT_TASK_COMPLETED, record)

        # Reindex if files were created/modified
        if action in ('file_created', 'file_modified'):
            files = result.get('files', [])
            for f in files:
                rel = str(Path(f).relative_to(self.project_path)) if str(self.project_path) in f else f
                if rel in self.files or (self.project_path / rel).exists():
                    self.reindex_file(rel)

    # ── SNAPSHOTS ─────────────────────────────────────────────

    def create_snapshot(self) -> str:
        """Create a snapshot. Returns snapshot ID."""
        snap_id = self._create_snapshot()
        self._events.emit(SNAPSHOT_CREATED, {'id': snap_id})
        return snap_id

    def _create_snapshot(self) -> str:
        """Internal snapshot creation."""
        snap_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_hashes = {p: e.hash for p, e in self.files.items()}
        total_symbols = sum(len(e.symbols) for e in self.files.values())

        snapshot = Snapshot(
            timestamp=snap_id,
            file_hashes=file_hashes,
            total_files=len(self.files),
            total_symbols=total_symbols,
        )
        self._storage.save_snapshot(snapshot)
        return snap_id

    def list_snapshots(self) -> List[str]:
        """List available snapshot IDs."""
        return self._storage.list_snapshots()

    # ── STATS ─────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get current project stats."""
        return {
            'total_files': len(self.files),
            'total_symbols': sum(len(e.symbols) for e in self.files.values()),
            'total_dependencies': sum(len(v) for v in self.dependencies.values()),
            'indexed': self._indexed,
            'index_time': self._index_time,
            'snapshots': len(self.list_snapshots()),
        }

    def get_file_tree(self, max_depth: int = 3) -> List[str]:
        """Get file tree for display."""
        tree_lines = [f"{self.project_path.name}/"]
        tree: Dict = {}
        for rel_path in self.files:
            parts = rel_path.split('/')
            current = tree
            for i, part in enumerate(parts[:max_depth]):
                if part not in current:
                    current[part] = {}
                current = current[part]

        def render(node, prefix="", is_last=True):
            items = sorted(node.items())
            for i, (name, children) in enumerate(items):
                is_last_item = (i == len(items) - 1)
                connector = "└── " if is_last_item else "├── "
                tree_lines.append(f"{prefix}{connector}{name}")
                if children:
                    ext = "    " if is_last_item else "│   "
                    render(children, prefix + ext, is_last_item)

        render(tree)
        return tree_lines

    def get_file_content(self, rel_path: str) -> Optional[str]:
        """Get file content by relative path."""
        full_path = self.project_path / rel_path
        if full_path.exists():
            try:
                return full_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                return None
        return None

    def search_symbols(self, name: str) -> List[Dict]:
        """Search for symbols by name across all files."""
        results = []
        for rel_path, entry in self.files.items():
            for sym in entry.symbols:
                if name.lower() in sym.get('name', '').lower():
                    results.append({
                        'file': rel_path,
                        'symbol': sym['name'],
                        'type': sym.get('type', ''),
                        'line': sym.get('line', 0),
                    })
        return results

    # ── CLASSIFICATION HELPERS ────────────────────────────────

    def _is_entry_point(self, rel_path: str, content: str) -> bool:
        """Check if file is an entry point."""
        name = Path(rel_path).name
        if name in ('app.py', 'main.py', 'manage.py', 'server.py', 'index.js', 'index.ts'):
            return True
        if 'if __name__' in content and '__main__' in content:
            return True
        return False

    def _is_config(self, rel_path: str) -> bool:
        """Check if file is a config file."""
        name = Path(rel_path).name
        configs = {
            'requirements.txt', 'package.json', 'pyproject.toml', 'setup.py',
            'setup.cfg', 'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
            'Makefile', 'Cargo.toml', 'go.mod', '.env.example',
        }
        if name in configs:
            return True
        ext = Path(rel_path).suffix.lower()
        return ext in ('.yaml', '.yml', '.toml', '.ini', '.cfg', '.config')
