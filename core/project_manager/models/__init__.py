"""
ProjectManager Data Models.

Only facts. No AI opinions. No speculative summaries.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
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


@dataclass
class SymbolEntry:
    """A single extracted symbol."""
    name: str
    type: str              # class, function, method, variable, interface, route
    file_path: str
    line: int
    signature: str = ""    # first 100 chars of definition line


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
