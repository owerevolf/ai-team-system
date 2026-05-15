"""
Dependency Graph — builds file dependency graph from import statements.

Deterministic. No semantic analysis. Only real import relationships.
Incremental updates supported.
"""

from pathlib import Path
from typing import Dict, List, Set

from core.project_manager.models import FileEntry


class DependencyGraph:
    """Builds and maintains file dependency graph from imports."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()

    def build(self, files: Dict[str, FileEntry]) -> Dict[str, List[str]]:
        """
        Build full dependency graph from file index.

        Returns:
            Dict mapping file path -> list of file paths it depends on
        """
        graph: Dict[str, List[str]] = {}
        module_map = self._build_module_map(files)

        for rel_path, entry in files.items():
            deps: Set[str] = set()
            for imp in entry.imports:
                resolved = self._resolve_import(imp, rel_path, module_map)
                if resolved and resolved != rel_path:
                    deps.add(resolved)
            graph[rel_path] = sorted(deps)

        return graph

    def build_incremental(
        self,
        files: Dict[str, FileEntry],
        existing_graph: Dict[str, List[str]],
        changed_files: List[str],
    ) -> Dict[str, List[str]]:
        """
        Update dependency graph for changed files only.
        """
        graph = dict(existing_graph)
        module_map = self._build_module_map(files)

        for rel_path in changed_files:
            if rel_path in files:
                entry = files[rel_path]
                deps: Set[str] = set()
                for imp in entry.imports:
                    resolved = self._resolve_import(imp, rel_path, module_map)
                    if resolved and resolved != rel_path:
                        deps.add(resolved)
                graph[rel_path] = sorted(deps)
            else:
                graph.pop(rel_path, None)

        return graph

    def get_dependents(self, graph: Dict[str, List[str]], target: str) -> List[str]:
        """Find all files that depend on the target file."""
        result = []
        for source, deps in graph.items():
            if target in deps:
                result.append(source)
        return result

    def _build_module_map(self, files: Dict[str, FileEntry]) -> Dict[str, str]:
        """Map module-like paths to actual file paths."""
        module_map: Dict[str, str] = {}
        for rel_path in files:
            module_map[rel_path] = rel_path
            module_map[rel_path.replace('/', '.').rsplit('.', 1)[0]] = rel_path
            parts = rel_path.split('/')
            if len(parts) > 1:
                module_map['.'.join(parts[:-1])] = rel_path
        return module_map

    def _resolve_import(
        self,
        import_path: str,
        source_file: str,
        module_map: Dict[str, str],
    ) -> str:
        """Resolve an import path to a project file path. Returns '' if external."""
        first_part = import_path.split('.')[0].split('/')[0]
        if self._is_external(first_part):
            return ''

        if import_path in module_map:
            return module_map[import_path]

        source_dir = str(Path(source_file).parent)
        candidate = f"{source_dir.replace('/', '.')}.{import_path}"
        if candidate in module_map:
            return module_map[candidate]

        for ext in ['', '.py', '.js', '.ts', '/index.py', '/index.js', '/index.ts']:
            candidate_path = import_path.replace('.', '/') + ext
            if candidate_path in module_map:
                return module_map[candidate_path]

        return ''

    def _is_external(self, module_name: str) -> bool:
        """Check if module is external (stdlib or third-party)."""
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
