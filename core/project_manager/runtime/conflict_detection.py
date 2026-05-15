"""
Conflict Detection Engine — detects conflicts between concurrent tasks.

Conflict types:
- file_overlap: both tasks modify same file
- symbol_overlap: both tasks modify same symbol
- dependency_collision: tasks modify dependent files
- api_contract_collision: tasks modify same API endpoint
- architecture_conflict: changes violate architecture rules
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


class ConflictSeverity(Enum):
    LOW = "low"           # Can auto-resolve
    MEDIUM = "medium"     # Needs review
    HIGH = "high"         # Must resolve before proceeding
    BLOCKING = "blocking" # Cannot proceed


class ConflictType(Enum):
    FILE_OVERLAP = "file_overlap"
    SYMBOL_OVERLAP = "symbol_overlap"
    DEPENDENCY_COLLISION = "dependency_collision"
    API_CONTRACT = "api_contract"
    ARCHITECTURE = "architecture"
    ROUTE_CONFLICT = "route_conflict"


@dataclass
class TaskConflict:
    """A detected conflict between tasks."""
    conflict_type: ConflictType
    severity: ConflictSeverity
    task_a: str
    task_b: str
    description: str
    files_involved: List[str] = field(default_factory=list)
    symbols_involved: List[str] = field(default_factory=list)
    resolution: str = ""  # suggested resolution
    auto_resolvable: bool = False


class ConflictDetectionEngine:
    """
    Detects conflicts between concurrent tasks.

    Analyzes:
    - File overlap (same files modified)
    - Symbol overlap (same symbols modified)
    - Dependency collision (dependent files modified)
    - API contract collision (same routes/endpoints)
    - Architecture rule conflicts
    """

    def __init__(
        self,
        files: Dict[str, Any],
        dependencies: Dict[str, List[str]],
        reverse_dependencies: Optional[Dict[str, List[str]]] = None,
    ):
        self.files = files
        self.dependencies = dependencies
        self._reverse_deps = reverse_dependencies or self._build_reverse_deps()

    def _build_reverse_deps(self) -> Dict[str, List[str]]:
        reverse: Dict[str, List[str]] = {}
        for source, targets in self.dependencies.items():
            for target in targets:
                if target not in reverse:
                    reverse[target] = []
                reverse[target].append(source)
        return reverse

    def detect_all_conflicts(
        self,
        tasks: Dict[str, Any],  # task_id -> task with files_locked
    ) -> List[TaskConflict]:
        """Detect all conflicts between active tasks."""
        conflicts = []
        task_ids = list(tasks.keys())

        for i in range(len(task_ids)):
            for j in range(i + 1, len(task_ids)):
                task_a = tasks[task_ids[i]]
                task_b = tasks[task_ids[j]]

                pair_conflicts = self._detect_pair_conflicts(task_a, task_b)
                conflicts.extend(pair_conflicts)

        return conflicts

    def _detect_pair_conflicts(self, task_a: Any, task_b: Any) -> List[TaskConflict]:
        """Detect conflicts between two tasks."""
        conflicts = []

        files_a = set(getattr(task_a, 'files_locked', []))
        files_b = set(getattr(task_b, 'files_locked', []))

        # File overlap
        overlap = files_a & files_b
        if overlap:
            for f in overlap:
                conflicts.append(TaskConflict(
                    conflict_type=ConflictType.FILE_OVERLAP,
                    severity=ConflictSeverity.HIGH,
                    task_a=task_a.id,
                    task_b=task_b.id,
                    description=f"Both tasks modify: {f}",
                    files_involved=[f],
                ))

        # Dependency collision
        for fa in files_a:
            for fb in files_b:
                if fa != fb and self._are_dependent(fa, fb):
                    conflicts.append(TaskConflict(
                        conflict_type=ConflictType.DEPENDENCY_COLLISION,
                        severity=ConflictSeverity.MEDIUM,
                        task_a=task_a.id,
                        task_b=task_b.id,
                        description=f"Tasks modify dependent files: {fa} ↔ {fb}",
                        files_involved=[fa, fb],
                    ))

        # Symbol overlap
        symbols_a = set(getattr(task_a, 'symbols_locked', []))
        symbols_b = set(getattr(task_b, 'symbols_locked', []))
        symbol_overlap = symbols_a & symbols_b
        if symbol_overlap:
            for sym in symbol_overlap:
                conflicts.append(TaskConflict(
                    conflict_type=ConflictType.SYMBOL_OVERLAP,
                    severity=ConflictSeverity.HIGH,
                    task_a=task_a.id,
                    task_b=task_b.id,
                    description=f"Both tasks modify symbol: {sym}",
                    symbols_involved=[sym],
                ))

        # API contract collision
        api_conflicts = self._detect_api_conflicts(task_a, task_b, files_a, files_b)
        conflicts.extend(api_conflicts)

        return conflicts

    def _are_dependent(self, file_a: str, file_b: str) -> bool:
        """Check if two files are in a dependency relationship."""
        # BFS from file_a to file_b
        visited: Set[str] = set()
        queue = [file_a]

        while queue:
            current = queue.pop(0)
            if current == file_b:
                return True
            if current in visited:
                continue
            visited.add(current)

            for dep in self.dependencies.get(current, []):
                if dep not in visited:
                    queue.append(dep)

        return False

    def _detect_api_conflicts(
        self, task_a: Any, task_b: Any, files_a: Set[str], files_b: Set[str]
    ) -> List[TaskConflict]:
        """Detect API/route conflicts."""
        conflicts = []

        # Collect routes from both tasks
        routes_a = self._collect_routes(files_a)
        routes_b = self._collect_routes(files_b)

        for route_a, file_a in routes_a:
            for route_b, file_b in routes_b:
                if route_a == route_b and file_a != file_b:
                    conflicts.append(TaskConflict(
                        conflict_type=ConflictType.API_CONTRACT,
                        severity=ConflictSeverity.HIGH,
                        task_a=task_a.id,
                        task_b=task_b.id,
                        description=f"Both tasks modify route: {route_a}",
                        files_involved=[file_a, file_b],
                    ))

        return conflicts

    def _collect_routes(self, files: Set[str]) -> List[tuple]:
        """Collect route definitions from files."""
        routes = []
        for f in files:
            if f in self.files:
                entry = self.files[f]
                for sym in entry.symbols:
                    if sym.get('type') == 'route':
                        sig = sym.get('signature', '')
                        if sig:
                            routes.append((sig, f))
        return routes

    def get_resolution_suggestion(self, conflict: TaskConflict) -> str:
        """Get a suggestion for resolving a conflict."""
        if conflict.conflict_type == ConflictType.FILE_OVERLAP:
            return "Sequential execution: complete one task before starting the other"
        elif conflict.conflict_type == ConflictType.SYMBOL_OVERLAP:
            return "Split the symbol changes or execute sequentially"
        elif conflict.conflict_type == ConflictType.DEPENDENCY_COLLISION:
            return "Execute tasks in dependency order (leaf first)"
        elif conflict.conflict_type == ConflictType.API_CONTRACT:
            return "Merge API changes manually or execute sequentially"
        elif conflict.conflict_type == ConflictType.ARCHITECTURE:
            return "Review architecture rules and adjust changes"
        return "Manual review required"
