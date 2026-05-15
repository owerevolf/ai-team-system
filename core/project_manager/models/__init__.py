"""
ProjectManager Data Models.

Only facts. No AI opinions. No speculative summaries.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
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


# ── Phase 3: Engineering Safety Models ──

@dataclass
class ValidationReport:
    """Result of running validation pipeline."""
    issues: List[Dict] = field(default_factory=list)
    files_checked: int = 0
    symbols_checked: int = 0
    elapsed_seconds: float = 0.0
    has_errors: bool = False
    has_critical: bool = False

    def summary(self) -> Dict[str, Any]:
        from collections import Counter
        severities = Counter(i.get('severity', 'unknown') for i in self.issues)
        return {
            'total_issues': len(self.issues),
            'critical': severities.get('critical', 0),
            'errors': severities.get('error', 0),
            'warnings': severities.get('warning', 0),
            'info': severities.get('info', 0),
            'files_checked': self.files_checked,
            'elapsed_seconds': self.elapsed_seconds,
        }


@dataclass
class ExecutionRecord:
    """Record of a task execution attempt."""
    task_id: str = ""
    agent: str = ""
    action: str = ""
    status: str = "pending"  # pending, running, completed, failed, rolled_back
    started_at: str = ""
    completed_at: str = ""
    files_changed: List[str] = field(default_factory=list)
    validation_result: Optional[Dict] = None
    risk_level: str = "low"
    risk_score: float = 0.0
    error: str = ""
    snapshot_before: str = ""
    snapshot_after: str = ""


@dataclass
class ModuleStability:
    """Stability metrics for a module."""
    file_path: str = ""
    change_count: int = 0       # how many times modified
    last_change: str = ""       # timestamp
    failure_count: int = 0      # how many times changes here caused failures
    dependent_count: int = 0    # how many files depend on this
    stability_score: float = 1.0  # 0.0 (unstable) to 1.0 (stable)


# ── Phase 4: Collaborative Runtime Models ──

@dataclass
class AgentMetrics:
    """Metrics for agent reliability tracking."""
    agent_name: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0
    patches_applied: int = 0
    patches_rolled_back: int = 0
    validation_failures: int = 0
    avg_risk_score: float = 0.0
    reliability_score: float = 1.0  # 0.0 to 1.0

    def update_reliability(self):
        total = self.tasks_completed + self.tasks_failed
        if total > 0:
            self.reliability_score = round(self.tasks_completed / total, 2)


@dataclass
class WorkflowMetrics:
    """Metrics for workflow execution."""
    workflow_name: str = ""
    executions: int = 0
    successes: int = 0
    failures: int = 0
    rollbacks: int = 0
    avg_duration_seconds: float = 0.0
    avg_risk_score: float = 0.0
