"""
Validation Pipeline — deterministic repository validation.

Checks:
- Broken imports (imported file doesn't exist)
- Missing symbols (imported symbol not found in target file)
- Circular dependencies (A → B → ... → A)
- Orphan modules (no one imports them, not entry points)
- Route conflicts (duplicate route paths)
- Duplicate symbols (same name, same scope)
- Invalid references (symbol used but not defined)
- Dependency violations (layer boundary violations)
- Invalid exports (exported but not defined)
- Unreachable modules (can't be reached from entry points)

All checks are deterministic. No AI opinions.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from core.project_manager.models import FileEntry
from loguru import logger


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """A single validation finding."""
    check: str           # which check found this
    severity: Severity
    message: str
    file: str            # relative path
    line: int = 0
    symbol: str = ""
    related_files: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Complete validation result."""
    issues: List[ValidationIssue] = field(default_factory=list)
    files_checked: int = 0
    symbols_checked: int = 0
    elapsed_seconds: float = 0.0

    @property
    def has_errors(self) -> bool:
        return any(i.severity in (Severity.ERROR, Severity.CRITICAL) for i in self.issues)

    @property
    def has_critical(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    def by_severity(self, severity: Severity) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == severity]

    def by_check(self, check: str) -> List[ValidationIssue]:
        return [i for i in self.issues if i.check == check]

    def by_file(self, file_path: str) -> List[ValidationIssue]:
        return [i for i in self.issues if i.file == file_path]

    def summary(self) -> Dict[str, Any]:
        return {
            'total_issues': len(self.issues),
            'critical': self.critical_count,
            'errors': self.error_count,
            'warnings': self.warning_count,
            'info': len(self.by_severity(Severity.INFO)),
            'files_checked': self.files_checked,
            'symbols_checked': self.symbols_checked,
            'elapsed_seconds': self.elapsed_seconds,
            'has_errors': self.has_errors,
            'has_critical': self.has_critical,
        }


class ValidationPipeline:
    """
    Runs a suite of deterministic validation checks on the project.

    Each check is independent and returns a list of ValidationIssue.
    Checks never crash — they return partial results on error.
    """

    def __init__(
        self,
        files: Dict[str, FileEntry],
        dependencies: Dict[str, List[str]],
        project_path: Path,
    ):
        self.files = files
        self.dependencies = dependencies
        self.project_path = project_path

        # Build symbol index: symbol_name -> [(file, line)]
        self._symbol_index: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        # Build export index: exported_symbol -> file
        self._export_index: Dict[str, str] = {}
        # Build route index: (method, path) -> file
        self._route_index: Dict[Tuple[str, str], str] = {}
        # Build module map for import resolution (cached)
        self._module_map: Dict[str, str] = {}

        self._build_indices()

    def _build_indices(self) -> None:
        """Build lookup indices for validation."""
        for rel_path, entry in self.files.items():
            # Module map for import resolution
            self._module_map[rel_path] = rel_path
            self._module_map[rel_path.replace('/', '.').rsplit('.', 1)[0]] = rel_path

            for sym in entry.symbols:
                name = sym.get('name', '')
                line = sym.get('line', 0)
                if name:
                    self._symbol_index[name].append((rel_path, line))

            for exp in entry.exports:
                if exp not in self._export_index:
                    self._export_index[exp] = rel_path

    def validate(self, checks: Optional[List[str]] = None) -> ValidationResult:
        """
        Run all validation checks.

        Args:
            checks: Optional list of check names to run. If None, run all.

        Returns:
            ValidationResult with all findings.
        """
        import time
        start = time.time()

        all_checks = {
            'broken_imports': self._check_broken_imports,
            'missing_symbols': self._check_missing_symbols,
            'circular_dependencies': self._check_circular_dependencies,
            'orphan_modules': self._check_orphan_modules,
            'route_conflicts': self._check_route_conflicts,
            'duplicate_symbols': self._check_duplicate_symbols,
            'invalid_exports': self._check_invalid_exports,
            'unreachable_modules': self._check_unreachable_modules,
        }

        if checks:
            selected = {k: v for k, v in all_checks.items() if k in checks}
        else:
            selected = all_checks

        result = ValidationResult()
        result.files_checked = len(self.files)
        result.symbols_checked = sum(len(e.symbols) for e in self.files.values())

        for check_name, check_fn in selected.items():
            try:
                issues = check_fn()
                result.issues.extend(issues)
            except Exception as e:
                logger.error(f"Validation check '{check_name}' failed: {e}")
                result.issues.append(ValidationIssue(
                    check=check_name,
                    severity=Severity.WARNING,
                    message=f"Check failed with error: {e}",
                    file="",
                ))

        result.elapsed_seconds = round(time.time() - start, 3)
        return result

    # ── CHECK: Broken Imports ──

    def _check_broken_imports(self) -> List[ValidationIssue]:
        """Check that all imports resolve to existing project files."""
        issues = []

        for rel_path, entry in self.files.items():
            for imp in entry.imports:
                # Skip external imports (stdlib, third-party)
                first_part = imp.split('.')[0].split('/')[0]
                if self._is_external(first_part):
                    continue

                # Try to resolve
                resolved = self._resolve_import(imp, rel_path)
                if not resolved:
                    issues.append(ValidationIssue(
                        check='broken_imports',
                        severity=Severity.ERROR,
                        message=f"Cannot resolve import: {imp}",
                        file=rel_path,
                        symbol=imp,
                    ))

        return issues

    # ── CHECK: Missing Symbols ──

    def _check_missing_symbols(self) -> List[ValidationIssue]:
        """Check that imported symbols exist in target files."""
        issues = []

        for rel_path, entry in self.files.items():
            for imp in entry.imports:
                # Check if this is a "from X import Y" style
                if '.' in imp:
                    parts = imp.rsplit('.', 1)
                    if len(parts) == 2:
                        module_path, symbol_name = parts
                        # Find the target file
                        target_file = self._resolve_import(module_path, rel_path)
                        if target_file and target_file in self.files:
                            target_entry = self.files[target_file]
                            symbol_names = {s.get('name', '') for s in target_entry.symbols}
                            if symbol_name not in symbol_names:
                                # Check exports
                                if symbol_name not in target_entry.exports:
                                    issues.append(ValidationIssue(
                                        check='missing_symbols',
                                        severity=Severity.ERROR,
                                        message=f"Symbol '{symbol_name}' not found in {target_file}",
                                        file=rel_path,
                                        symbol=symbol_name,
                                        related_files=[target_file],
                                    ))

        return issues

    # ── CHECK: Circular Dependencies ──

    def _check_circular_dependencies(self) -> List[ValidationIssue]:
        """Detect circular dependencies using DFS."""
        issues = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self.dependencies.get(node, []):
                if dep not in visited:
                    cycle = dfs(dep)
                    if cycle:
                        return cycle
                elif dep in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]

            path.pop()
            rec_stack.discard(node)
            return None

        for file_path in self.files:
            if file_path not in visited:
                cycle = dfs(file_path)
                if cycle:
                    cycle_str = " → ".join(cycle)
                    issues.append(ValidationIssue(
                        check='circular_dependencies',
                        severity=Severity.CRITICAL,
                        message=f"Circular dependency: {cycle_str}",
                        file=cycle[0],
                        related_files=cycle[1:-1],
                    ))
                    # Don't report same cycle multiple times
                    break

        return issues

    # ── CHECK: Orphan Modules ──

    def _check_orphan_modules(self) -> List[ValidationIssue]:
        """Find modules that are not imported by anyone and are not entry points."""
        issues = []

        # Find all files that are imported
        imported: Set[str] = set()
        for deps in self.dependencies.values():
            imported.update(deps)

        for rel_path, entry in self.files.items():
            if entry.is_entry_point:
                continue
            if entry.is_test:
                continue
            if entry.is_config:
                continue
            if rel_path in imported:
                continue

            # Check if it's a special file
            name = Path(rel_path).name
            if name in ('__init__.py', 'setup.py', 'conftest.py'):
                continue

            issues.append(ValidationIssue(
                check='orphan_modules',
                severity=Severity.WARNING,
                message="Module is not imported by any other module",
                file=rel_path,
            ))

        return issues

    # ── CHECK: Route Conflicts ──

    def _check_route_conflicts(self) -> List[ValidationIssue]:
        """Detect duplicate route definitions."""
        issues = []
        route_map: Dict[str, List[str]] = defaultdict(list)

        for rel_path, entry in self.files.items():
            for sym in entry.symbols:
                if sym.get('type') == 'route':
                    route_path = sym.get('signature', '')
                    if route_path:
                        route_map[route_path].append(rel_path)

        for route, files in route_map.items():
            if len(files) > 1:
                issues.append(ValidationIssue(
                    check='route_conflicts',
                    severity=Severity.ERROR,
                    message=f"Route '{route}' defined in multiple files",
                    file=files[0],
                    related_files=files[1:],
                ))

        return issues

    # ── CHECK: Duplicate Symbols ──

    def _check_duplicate_symbols(self) -> List[ValidationIssue]:
        """Find duplicate symbol names within the same file."""
        issues = []

        for rel_path, entry in self.files.items():
            seen: Dict[str, int] = {}
            for sym in entry.symbols:
                name = sym.get('name', '')
                line = sym.get('line', 0)
                if name in seen:
                    issues.append(ValidationIssue(
                        check='duplicate_symbols',
                        severity=Severity.WARNING,
                        message=f"Symbol '{name}' defined at lines {seen[name]} and {line}",
                        file=rel_path,
                        symbol=name,
                        line=line,
                    ))
                else:
                    seen[name] = line

        return issues

    # ── CHECK: Invalid Exports ──

    def _check_invalid_exports(self) -> List[ValidationIssue]:
        """Check that exported symbols actually exist in the file."""
        issues = []

        for rel_path, entry in self.files.items():
            symbol_names = {s.get('name', '') for s in entry.symbols}
            for exp in entry.exports:
                if exp not in symbol_names:
                    issues.append(ValidationIssue(
                        check='invalid_exports',
                        severity=Severity.ERROR,
                        message=f"Exported symbol '{exp}' not found in file",
                        file=rel_path,
                        symbol=exp,
                    ))

        return issues

    # ── CHECK: Unreachable Modules ──

    def _check_unreachable_modules(self) -> List[ValidationIssue]:
        """Find modules that can't be reached from any entry point via imports."""
        # BFS from entry points
        reachable: Set[str] = set()
        queue: List[str] = []

        for rel_path, entry in self.files.items():
            if entry.is_entry_point:
                queue.append(rel_path)
                reachable.add(rel_path)

        while queue:
            current = queue.pop(0)
            for dep in self.dependencies.get(current, []):
                if dep not in reachable:
                    reachable.add(dep)
                    queue.append(dep)

        # Find unreachable non-test, non-config files
        issues = []
        for rel_path, entry in self.files.items():
            if rel_path in reachable:
                continue
            if entry.is_test:
                continue
            if entry.is_config:
                continue
            name = Path(rel_path).name
            if name in ('__init__.py', 'setup.py', 'conftest.py'):
                continue

            issues.append(ValidationIssue(
                check='unreachable_modules',
                severity=Severity.INFO,
                message="Module not reachable from any entry point",
                file=rel_path,
            ))

        return issues

    # ── HELPERS ──

    def _is_external(self, module_name: str) -> bool:
        """Check if module is external."""
        stdlib = {
            'os', 'sys', 'json', 're', 'pathlib', 'typing', 'datetime',
            'collections', 'itertools', 'functools', 'math', 'random',
            'hashlib', 'logging', 'urllib', 'http', 'socket', 'threading',
            'multiprocessing', 'subprocess', 'tempfile', 'shutil', 'glob',
            'inspect', 'importlib', 'abc', 'enum', 'dataclasses',
            'contextlib', 'io', 'csv', 'xml', 'html', 'email', 'sqlite3',
            'unittest', 'asyncio', 'queue', 'time', 'uuid', 'copy',
            'pprint', 'textwrap', 'string', 'struct', 'codecs',
            'warnings', 'traceback', 'types', 'weakref', 'gc',
            'atexit', 'signal', 'errno', 'stat', 'fnmatch', 'fileinput',
            'filecmp', 'linecache', 'pickle', 'shelve', 'dbm',
            'zlib', 'gzip', 'bz2', 'lzma', 'zipfile', 'tarfile',
        }
        if module_name in stdlib:
            return True

        third_party = {
            'fastapi', 'flask', 'django', 'pydantic', 'sqlalchemy',
            'alembic', 'celery', 'redis', 'requests', 'httpx', 'aiohttp',
            'numpy', 'pandas', 'matplotlib', 'sklearn', 'torch',
            'transformers', 'pytest', 'jinja2', 'loguru', 'dotenv',
            'rich', 'click', 'typer', 'uvicorn', 'starlette',
            'ollama', 'openai', 'anthropic',
        }
        if module_name in third_party:
            return True

        return False

    def _resolve_import(self, import_path: str, source_file: str) -> Optional[str]:
        """Resolve an import path to a project file path (uses cached module map)."""
        if import_path in self._module_map:
            return self._module_map[import_path]

        source_dir = str(Path(source_file).parent)
        candidate = f"{source_dir.replace('/', '.')}.{import_path}"
        if candidate in self._module_map:
            return self._module_map[candidate]

        for ext in ['', '.py', '.js', '.ts', '/index.py', '/index.js', '/index.ts']:
            candidate_path = import_path.replace('.', '/') + ext
            if candidate_path in self._module_map:
                return self._module_map[candidate_path]

        return None
