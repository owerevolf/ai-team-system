"""
ProjectManager Data Models.

Only facts. No AI opinions. No speculative summaries.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime


@dataclass
class FileEntry:
    """Immutable fact about a file."""
    path: str              # relative path from project root
    size: int              # bytes
    modified: float        # mtime timestamp
    hash: str              # sha256[:16] for change detection
    language: str          # python, javascript, etc.

    # Optional facts (empty if unknown)
    symbols: List[Dict] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)

    # Classification flags
    is_entry_point: bool = False
    is_test: bool = False
    is_config: bool = False

    # Incremental indexing metadata
    index_time: float = 0.0       # when this file was last indexed
    last_seen: float = 0.0        # mtime when hash was computed


@dataclass
class SymbolEntry:
    """A single extracted symbol."""
    name: str
    type: str              # class, function, method, variable, interface, route
    file_path: str
    line: int
    signature: str = ""    # first 100 chars of definition line
    decorators: List[str] = field(default_factory=list)  # @app.route, @staticmethod, etc.
    parent: str = ""       # parent class/method name
    is_async: bool = False


@dataclass
class DependencyEdge:
    """A -> B means A imports/depends on B."""
    source: str            # file path
    target: str            # file path
    symbols: List[str] = field(default_factory=list)  # what is imported


@dataclass
class Snapshot:
    """Point-in-time snapshot of project state."""
    timestamp: str
    file_hashes: Dict[str, str]     # path -> hash
    total_files: int
    total_symbols: int
    # Phase 2: structural diff
    added_files: List[str] = field(default_factory=list)
    removed_files: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    added_symbols: List[Dict] = field(default_factory=list)
    removed_symbols: List[Dict] = field(default_factory=list)


@dataclass
class GitState:
    """Current git state of the project."""
    branch: str = ""
    commit_hash: str = ""
    commit_message: str = ""
    commit_author: str = ""
    commit_date: str = ""
    changed_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    staged_files: List[str] = field(default_factory=list)
    recent_commits: List[Dict] = field(default_factory=list)
    is_clean: bool = True


@dataclass
class RetrievalMetrics:
    """Metrics for a single retrieval operation."""
    query: str
    agent: str
    timestamp: str
    files_returned: int
    symbols_returned: int
    context_chars: int
    duration_ms: float
    cache_hit: bool = False


@dataclass
class IndexStats:
    """Statistics about an indexing operation."""
    total_files: int = 0
    total_symbols: int = 0
    total_dependencies: int = 0
    elapsed_seconds: float = 0.0
    changed_files: int = 0
    added_files: int = 0
    removed_files: int = 0
    is_incremental: bool = False
