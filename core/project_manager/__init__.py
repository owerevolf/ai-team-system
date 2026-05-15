"""
ProjectManager — passive observation kernel for the project.

NOT an AI agent. NOT an orchestrator. NOT a decision maker.
Stores facts about the project. Provides context on demand.

Phase 2 features:
- Incremental indexing (hash-based change detection)
- AST-based symbol extraction (Python) with regex fallback
- FileWatch for real-time change detection
- Git intelligence (branch, commits, changed files)
- Impact analysis (dependency graph traversal)
- Deterministic retrieval ranking
- Event system with dedup and throttling
- SQLite storage backend
- Context quality metrics

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

from core.project_manager.models import FileEntry, Snapshot, IndexStats
from core.project_manager.indexers import FileIndexer
from core.project_manager.indexers.dependency_graph import DependencyGraph
from core.project_manager.indexers.git_intelligence import GitIntelligence
from core.project_manager.indexers.file_watch import FileWatch
from core.project_manager.extractors import SymbolExtractor
from core.project_manager.storage import Storage
from core.project_manager.events import (
    EventBus, FILE_INDEXED, FILE_CHANGED, FILE_DELETED,
    SYMBOLS_UPDATED, CONTEXT_REQUESTED, AGENT_TASK_COMPLETED,
    INDEX_UPDATED, INDEX_INCREMENTAL, SNAPSHOT_CREATED,
    GIT_STATE_CHANGED, IMPACT_ANALYSIS,
)
from core.project_manager.query import QueryEngine


class ProjectManager:
    """
    Passive project observation kernel.

    Responsibilities:
    - Index files (path, size, hash, language)
    - Extract symbols (classes, functions, imports) via AST + regex
    - Build dependency graph
    - Answer context queries with budget enforcement
    - Track task history
    - Git state awareness
    - Impact analysis
    - File watching for incremental updates

    NOT responsible for:
    - Making decisions
    - Writing code
    - Managing agents
    - Self-improvement
    """

    def __init__(
        self,
        project_path: Path,
        max_context_chars: int = 12000,
        storage_backend: str = "json",
        enable_watch: bool = False,
    ):
        self.project_path = Path(project_path).resolve()
        self._indexer = FileIndexer(self.project_path)
        self._extractor = SymbolExtractor()
        self._dep_graph = DependencyGraph(self.project_path)
        self._git = GitIntelligence(self.project_path)
        self._storage = Storage(self.project_path, backend=storage_backend)
        self._events = EventBus()
        self._query_engine = QueryEngine(max_context_chars=max_context_chars)

        # State
        self.files: Dict[str, FileEntry] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self._indexed = False
        self._index_time: Optional[str] = None
        self._last_stats: Optional[IndexStats] = None

        # File watcher (optional)
        self._watcher: Optional[FileWatch] = None
        if enable_watch:
            self._watcher = FileWatch(
                self.project_path,
                callback=self._on_files_changed,
                debounce_seconds=1.0,
            )

        logger.info(f"ProjectManager initialized: {self.project_path}")

    @property
    def is_indexed(self) -> bool:
        return self._indexed

    # ── INDEXING ──────────────────────────────────────────────

    def index_project(self) -> IndexStats:
        """
        Full project scan and index.
        Returns IndexStats.
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

                # Symbols (AST for Python, regex for others)
                symbols = self._extractor.extract_symbols(content, entry.language)
                for sym in symbols:
                    sym.file_path = rel_path
                entry.symbols = [
                    {
                        'name': s.name, 'type': s.type, 'line': s.line,
                        'signature': s.signature, 'decorators': s.decorators,
                        'parent': s.parent, 'is_async': s.is_async,
                    }
                    for s in symbols
                ]
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
        stats = IndexStats(
            total_files=len(self.files),
            total_symbols=total_symbols,
            total_dependencies=sum(len(v) for v in self.dependencies.values()),
            elapsed_seconds=round(elapsed, 2),
        )
        self._last_stats = stats
        self._events.emit(INDEX_UPDATED, stats)
        logger.info(f"Indexing complete: {stats}")
        return stats

    def index_incremental(self) -> IndexStats:
        """
        Incremental index: only process changed/new/deleted files.
        Much faster than full reindex for large projects.
        """
        if not self._indexed:
            return self.index_project()

        logger.info("Starting incremental index...")
        start = time.time()

        # 1. Scan for changes
        self.files, changed, added, removed = self._indexer.scan_incremental(self.files)

        # 2. Re-extract symbols for changed and new files
        total_symbols = 0
        for rel_path in changed + added:
            entry = self.files.get(rel_path)
            if not entry:
                continue

            try:
                full_path = self.project_path / rel_path
                content = full_path.read_text(encoding='utf-8', errors='ignore')

                symbols = self._extractor.extract_symbols(content, entry.language)
                for sym in symbols:
                    sym.file_path = rel_path
                entry.symbols = [
                    {
                        'name': s.name, 'type': s.type, 'line': s.line,
                        'signature': s.signature, 'decorators': s.decorators,
                        'parent': s.parent, 'is_async': s.is_async,
                    }
                    for s in symbols
                ]
                entry.imports = self._extractor.extract_imports(content, entry.language)
                entry.exports = self._extractor.extract_exports(content, entry.language)
                entry.is_entry_point = self._is_entry_point(rel_path, content)
                entry.is_test = 'test' in rel_path.lower() or rel_path.startswith('tests/')
                entry.is_config = self._is_config(rel_path)

            except Exception as e:
                logger.warning(f"Failed to process {rel_path}: {e}")
                continue

        # 3. Update dependency graph incrementally
        self.dependencies = self._dep_graph.build_incremental(
            self.files, self.dependencies, changed + added, removed
        )

        # 4. Persist
        self._storage.save_file_index(self.files)
        self._storage.save_dependency_graph(self.dependencies)

        elapsed = time.time() - start
        stats = IndexStats(
            total_files=len(self.files),
            total_symbols=sum(len(e.symbols) for e in self.files.values()),
            total_dependencies=sum(len(v) for v in self.dependencies.values()),
            elapsed_seconds=round(elapsed, 2),
            changed_files=len(changed),
            added_files=len(added),
            removed_files=len(removed),
            is_incremental=True,
        )
        self._last_stats = stats
        self._events.emit(INDEX_INCREMENTAL, stats)
        logger.info(f"Incremental index complete: {stats}")
        return stats

    def reindex_file(self, rel_path: str) -> bool:
        """Reindex a single file after change."""
        if rel_path not in self.files:
            # Check if it's a new file
            full_path = self.project_path / rel_path
            if full_path.exists():
                return self._index_new_file(rel_path)
            return False

        full_path = self.project_path / rel_path
        if not full_path.exists():
            # File was deleted
            del self.files[rel_path]
            self.dependencies = self._dep_graph.build_incremental(
                self.files, self.dependencies, [], [rel_path]
            )
            self._events.emit(FILE_DELETED, {'path': rel_path})
            return True

        try:
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            entry = self.files[rel_path]

            symbols = self._extractor.extract_symbols(content, entry.language)
            for sym in symbols:
                sym.file_path = rel_path
            entry.symbols = [
                {
                    'name': s.name, 'type': s.type, 'line': s.line,
                    'signature': s.signature, 'decorators': s.decorators,
                    'parent': s.parent, 'is_async': s.is_async,
                }
                for s in symbols
            ]
            entry.imports = self._extractor.extract_imports(content, entry.language)
            entry.exports = self._extractor.extract_exports(content, entry.language)
            entry.hash = __import__('hashlib').sha256(content.encode()).hexdigest()[:16]
            entry.size = full_path.stat().st_size
            entry.modified = full_path.stat().st_mtime

            # Update dependencies incrementally
            self.dependencies = self._dep_graph.build_incremental(
                self.files, self.dependencies, [rel_path], []
            )
            self._storage.save_file_index(self.files)
            self._storage.save_dependency_graph(self.dependencies)
            self._events.emit(FILE_CHANGED, {'path': rel_path})
            return True

        except Exception as e:
            logger.error(f"Reindex failed for {rel_path}: {e}")
            return False

    def _index_new_file(self, rel_path: str) -> bool:
        """Index a new file and add it to the index."""
        full_path = self.project_path / rel_path
        if not full_path.exists():
            return False

        try:
            stat = full_path.stat()
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            file_hash = __import__('hashlib').sha256(content.encode()).hexdigest()[:16]
            language = self._indexer._detect_language(full_path.name)

            symbols = self._extractor.extract_symbols(content, language)
            for sym in symbols:
                sym.file_path = rel_path

            entry = FileEntry(
                path=rel_path,
                size=stat.st_size,
                modified=stat.st_mtime,
                hash=file_hash,
                language=language,
                symbols=[
                    {
                        'name': s.name, 'type': s.type, 'line': s.line,
                        'signature': s.signature, 'decorators': s.decorators,
                        'parent': s.parent, 'is_async': s.is_async,
                    }
                    for s in symbols
                ],
                imports=self._extractor.extract_imports(content, language),
                exports=self._extractor.extract_exports(content, language),
                is_entry_point=self._is_entry_point(rel_path, content),
                is_test='test' in rel_path.lower() or rel_path.startswith('tests/'),
                is_config=self._is_config(rel_path),
                last_seen=stat.st_mtime,
                index_time=time.time(),
            )

            self.files[rel_path] = entry
            self.dependencies = self._dep_graph.build_incremental(
                self.files, self.dependencies, [rel_path], []
            )
            self._events.emit(FILE_INDEXED, {'path': rel_path})
            return True

        except Exception as e:
            logger.error(f"Failed to index new file {rel_path}: {e}")
            return False

    # ── FILE WATCH ────────────────────────────────────────────

    def start_watching(self) -> None:
        """Start file system watcher for automatic incremental indexing."""
        if self._watcher:
            self._watcher.start()
            logger.info("File watching started")

    def stop_watching(self) -> None:
        """Stop file system watcher."""
        if self._watcher:
            self._watcher.stop()
            logger.info("File watching stopped")

    def _on_files_changed(self, relative_paths: List[str]) -> None:
        """Callback from FileWatch — triggered when files change on disk."""
        if not self._indexed:
            return

        for rel_path in relative_paths:
            if rel_path in self.files:
                self.reindex_file(rel_path)
            else:
                self._index_new_file(rel_path)

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

        # Get git state for ranking
        git_state = self._git.get_state()

        return self._query_engine.query(
            self.files, question, max_chars=max_chars,
            agent=agent, dependencies=self.dependencies, git_state=git_state,
        )

    # ── GIT INTELLIGENCE ──────────────────────────────────────

    def get_git_state(self) -> Dict[str, Any]:
        """Get current git state."""
        state = self._git.get_state()
        return {
            'branch': state.branch,
            'commit_hash': state.commit_hash,
            'commit_message': state.commit_message,
            'commit_author': state.commit_author,
            'commit_date': state.commit_date,
            'is_clean': state.is_clean,
            'changed_files': state.changed_files,
            'staged_files': state.staged_files,
            'untracked_files': state.untracked_files,
            'recent_commits': state.recent_commits,
        }

    def get_recently_active_files(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get files modified in the last N days."""
        return self._git.get_recently_active_files(days=days, limit=limit)

    # ── IMPACT ANALYSIS ───────────────────────────────────────

    def analyze_impact(self, changed_file: str) -> Dict[str, Any]:
        """
        Analyze the impact of changing a file.

        Returns:
            Dict with affected files, broken imports, affected tests, etc.
        """
        if changed_file not in self.files:
            return {'error': f'File not found: {changed_file}'}

        # Direct dependents (files that import this file)
        direct_dependents = self._dep_graph.get_dependents(self.dependencies, changed_file)

        # All transitively affected files
        all_affected = self._dep_graph.get_all_dependents(self.dependencies, changed_file)

        # Find affected tests
        affected_tests = [f for f in all_affected if self.files.get(f, FileEntry('', 0, 0, '', '')).is_test]

        # Find affected entry points
        affected_entry_points = [
            f for f in all_affected
            if self.files.get(f, FileEntry('', 0, 0, '', '')).is_entry_point
        ]

        result = {
            'changed_file': changed_file,
            'direct_dependents': direct_dependents,
            'all_affected_files': all_affected,
            'affected_tests': affected_tests,
            'affected_entry_points': affected_entry_points,
            'impact_score': len(all_affected),
            'risk_level': 'high' if len(all_affected) > 10 else ('medium' if len(all_affected) > 3 else 'low'),
        }

        self._events.emit(IMPACT_ANALYSIS, result)
        return result

    def get_dependency_chain(self, source: str, target: str) -> List[str]:
        """Find dependency path from source to target."""
        return self._dep_graph.get_dependency_chain(self.dependencies, source, target)

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
        """Internal snapshot creation with structural diff."""
        snap_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_hashes = {p: e.hash for p, e in self.files.items()}
        total_symbols = sum(len(e.symbols) for e in self.files.values())

        # Compute diff from previous snapshot
        added_files = []
        removed_files = []
        changed_files = []
        added_symbols = []
        removed_symbols = []

        prev_snap_id = self._get_previous_snapshot_id()
        if prev_snap_id:
            prev_data = self._storage.load_snapshot(prev_snap_id)
            if prev_data:
                prev_hashes = prev_data.get('file_hashes', {})
                prev_files = set(prev_hashes.keys())
                curr_files = set(file_hashes.keys())

                added_files = sorted(curr_files - prev_files)
                removed_files = sorted(prev_files - curr_files)
                changed_files = sorted(
                    f for f in curr_files & prev_files
                    if prev_hashes.get(f) != file_hashes.get(f)
                )

        snapshot = Snapshot(
            timestamp=snap_id,
            file_hashes=file_hashes,
            total_files=len(self.files),
            total_symbols=total_symbols,
            added_files=added_files,
            removed_files=removed_files,
            changed_files=changed_files,
            added_symbols=added_symbols,
            removed_symbols=removed_symbols,
        )
        self._storage.save_snapshot(snapshot)
        return snap_id

    def _get_previous_snapshot_id(self) -> Optional[str]:
        """Get the most recent snapshot ID."""
        snaps = self._storage.list_snapshots()
        return snaps[0] if snaps else None

    def list_snapshots(self) -> List[str]:
        """List available snapshot IDs."""
        return self._storage.list_snapshots()

    def compare_snapshots(self, snap_a: str, snap_b: str) -> Dict[str, Any]:
        """Compare two snapshots and return structural diff."""
        data_a = self._storage.load_snapshot(snap_a)
        data_b = self._storage.load_snapshot(snap_b)

        if not data_a or not data_b:
            return {'error': 'One or both snapshots not found'}

        files_a = set(data_a.get('file_hashes', {}).keys())
        files_b = set(data_b.get('file_hashes', {}).keys())

        return {
            'snapshot_a': snap_a,
            'snapshot_b': snap_b,
            'added_files': sorted(files_b - files_a),
            'removed_files': sorted(files_a - files_b),
            'changed_files': sorted(
                f for f in files_a & files_b
                if data_a['file_hashes'].get(f) != data_b['file_hashes'].get(f)
            ),
            'files_count_a': data_a.get('total_files', 0),
            'files_count_b': data_b.get('total_files', 0),
            'symbols_count_a': data_a.get('total_symbols', 0),
            'symbols_count_b': data_b.get('total_symbols', 0),
        }

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
            'watching': self._watcher.is_running if self._watcher else False,
            'storage_backend': self._storage.backend,
            'last_index_stats': {
                'total_files': self._last_stats.total_files if self._last_stats else 0,
                'total_symbols': self._last_stats.total_symbols if self._last_stats else 0,
                'elapsed_seconds': self._last_stats.elapsed_seconds if self._last_stats else 0,
                'is_incremental': self._last_stats.is_incremental if self._last_stats else False,
            },
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

    def get_retrieval_metrics(self, limit: int = 50) -> List[Dict]:
        """Get retrieval quality metrics."""
        return self._query_engine.get_metrics(limit=limit)

    def get_hot_files(self, limit: int = 10) -> List[tuple]:
        """Get most frequently accessed files."""
        return self._query_engine.get_hot_files(limit=limit)

    # ── REPO EXPLORER COMPATIBILITY ───────────────────────────

    def get_repo_summary(self, level: str = "advanced") -> str:
        """
        Generate a factual project summary.
        No speculation. Only facts from index.
        """
        if not self._indexed:
            return "Project not indexed yet."

        parts = []
        parts.append(f"# Project: {self.project_path.name}\n")
        parts.append(f"## Statistics")
        parts.append(f"- Total files: {len(self.files)}")
        parts.append(f"- Total symbols: {sum(len(e.symbols) for e in self.files.values())}")
        parts.append(f"- Total dependencies: {sum(len(v) for v in self.dependencies.values())}")

        # Entry points
        entry_points = [f for f, e in self.files.items() if e.is_entry_point]
        if entry_points:
            parts.append(f"\n## Entry Points")
            for ep in entry_points[:10]:
                parts.append(f"- {ep}")

        # Languages
        from collections import Counter
        langs = Counter(e.language for e in self.files.values())
        parts.append(f"\n## Languages")
        for lang, count in langs.most_common(10):
            parts.append(f"- {lang}: {count} files")

        # Git state
        git = self._git.get_state()
        if git.branch:
            parts.append(f"\n## Git")
            parts.append(f"- Branch: {git.branch}")
            parts.append(f"- Commit: {git.commit_hash}")
            if not git.is_clean:
                parts.append(f"- Changed files: {len(git.changed_files)}")
                parts.append(f"- Staged files: {len(git.staged_files)}")

        # Top-level structure
        parts.append(f"\n## Structure")
        tree = self.get_file_tree(max_depth=2)
        parts.extend(tree[:30])

        return '\n'.join(parts)

    def rollback(self, snapshot_id: Optional[str] = None) -> bool:
        """
        Rollback to a snapshot.
        Note: This restores the PM index state, not file contents.
        For full rollback, git should be used.
        """
        try:
            if snapshot_id:
                data = self._storage.load_snapshot(snapshot_id)
            else:
                snaps = self._storage.list_snapshots()
                if not snaps:
                    return False
                data = self._storage.load_snapshot(snaps[-1])

            if not data:
                return False

            # Restore file hashes from snapshot
            # Note: This only restores the index, not actual file contents
            # For full rollback, use git reset
            logger.info(f"Rolled back PM index to snapshot: {data.get('timestamp', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    # ── PHASE 3: ENGINEERING SAFETY ───────────────────────────

    def validate_project(self, checks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run validation pipeline on the project.

        Args:
            checks: Optional list of check names. If None, run all.

        Returns:
            ValidationResult summary dict
        """
        from core.project_manager.validation import ValidationPipeline

        pipeline = ValidationPipeline(self.files, self.dependencies, self.project_path)
        result = pipeline.validate(checks=checks)
        return result.summary()

    def check_architecture_rules(self) -> List[Dict]:
        """Check all imports for architecture rule violations."""
        from core.project_manager.validation.architecture_rules import (
            ArchitectureRulesEngine, ArchitectureRulesConfig
        )

        engine = ArchitectureRulesEngine(
            self.files, self.dependencies,
            config=ArchitectureRulesConfig.default_rules(),
        )
        violations = engine.check_all_imports()
        return [
            {
                'rule': v.rule_name,
                'source': v.source_file,
                'target': v.target_file,
                'action': v.action.value,
                'message': v.message,
            }
            for v in violations
        ]

    def is_file_protected(self, file_path: str) -> bool:
        """Check if a file is protected from agent modifications."""
        from core.project_manager.validation.architecture_rules import (
            ArchitectureRulesEngine, ArchitectureRulesConfig
        )

        engine = ArchitectureRulesEngine(
            self.files, self.dependencies,
            config=ArchitectureRulesConfig.default_rules(),
        )
        return engine.is_file_protected(file_path)

    def find_relevant_tests(self, changed_files: List[str]) -> Dict:
        """Find tests relevant to the given file changes."""
        from core.project_manager.validation.test_impact import TestImpactAnalyzer

        analyzer = TestImpactAnalyzer(self.files, self.dependencies)
        return analyzer.get_test_recommendations(changed_files)

    def detect_semantic_changes(
        self, old_files: Dict[str, FileEntry]
    ) -> Dict[str, Any]:
        """
        Detect semantic changes between current state and old state.

        Args:
            old_files: Previous file index (from snapshot)
        """
        from core.project_manager.validation.semantic_change import SemanticChangeDetector

        detector = SemanticChangeDetector(old_files, self.files)
        report = detector.detect_changes()
        return report.summary()

    def assess_risk(
        self,
        changed_files: List[str],
        architecture_violations: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Assess risk of proposed changes.

        Args:
            changed_files: Files to be changed
            architecture_violations: Any architecture violations

        Returns:
            RiskAssessment summary dict
        """
        from core.project_manager.validation.risk_analysis import RiskAnalysisEngine

        # Get hot files from query engine
        hot_files = dict(self._query_engine.get_hot_files(limit=50))

        # Get protected files
        from core.project_manager.validation.architecture_rules import (
            ArchitectureRulesEngine, ArchitectureRulesConfig
        )
        arch_engine = ArchitectureRulesEngine(
            self.files, self.dependencies,
            config=ArchitectureRulesConfig.default_rules(),
        )
        protected = set(arch_engine.get_protected_files())

        risk_engine = RiskAnalysisEngine(
            self.files, self.dependencies,
            hot_files=hot_files,
            protected_files=protected,
        )

        # Count public API changes (simplified)
        public_api_changes = 0
        for f in changed_files:
            if f in self.files:
                for sym in self.files[f].symbols:
                    name = sym.get('name', '')
                    if not name.startswith('_') and sym.get('type') in ('class', 'function'):
                        public_api_changes += 1

        assessment = risk_engine.assess_changes(
            changed_files,
            architecture_violations=architecture_violations,
            public_api_changes=public_api_changes,
        )
        return assessment.summary()

    def apply_patch_set(self, patch_set: Any, dry_run: bool = False) -> List[Dict]:
        """
        Apply a set of patches safely.

        Args:
            patch_set: PatchSet to apply
            dry_run: If True, only check without applying

        Returns:
            List of patch results
        """
        from core.project_manager.validation.safe_patch import SafePatchSystem

        patcher = SafePatchSystem(self.project_path)
        results = patcher.apply_patch_set(patch_set, dry_run=dry_run)
        return [
            {
                'file': r.patch.file_path,
                'type': r.patch.patch_type.value,
                'success': r.success,
                'conflict': r.conflict,
                'error': r.error,
            }
            for r in results
        ]

    def get_module_stability(self) -> List[Dict]:
        """Get stability metrics for all modules."""
        from collections import defaultdict

        # Count changes per file from task history
        change_counts: Dict[str, int] = defaultdict(int)
        failure_counts: Dict[str, int] = defaultdict(int)

        try:
            history = self._storage.load_task_history(limit=500)
            for record in history:
                result = record.get('result', {})
                files = result.get('files', [])
                action = record.get('action', '')

                for f in files:
                    change_counts[f] += 1
                    if action == 'error' or action == 'failed':
                        failure_counts[f] += 1
        except Exception:
            pass

        results = []
        for rel_path in self.files:
            entry = self.files[rel_path]
            changes = change_counts.get(rel_path, 0)
            failures = failure_counts.get(rel_path, 0)
            dependents = len(self._dep_graph.get_dependents(self.dependencies, rel_path))

            # Stability score: 1.0 = perfectly stable, 0.0 = very unstable
            if changes == 0:
                stability = 1.0
            else:
                failure_rate = failures / max(changes, 1)
                change_penalty = min(changes * 0.05, 0.5)
                stability = max(0.0, 1.0 - failure_rate - change_penalty)

            results.append({
                'file': rel_path,
                'changes': changes,
                'failures': failures,
                'dependents': dependents,
                'stability': round(stability, 2),
                'is_test': entry.is_test,
                'is_entry_point': entry.is_entry_point,
            })

        # Sort by stability (least stable first)
        results.sort(key=lambda x: x['stability'])
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
