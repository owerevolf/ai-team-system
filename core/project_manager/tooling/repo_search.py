"""
repo_search.py — Intelligent Repo Search.

NOT just grep. Provides:
- symbol search (functions, classes, variables)
- import tracing (who imports what)
- usage lookup (where is this used)
- route detection (API routes, URL patterns)
- component discovery (React components, etc.)

This is the foundation for understanding large projects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger


@dataclass
class SearchMatch:
    """A single search match."""
    file_path: str = ""
    line_number: int = 0
    line_content: str = ""
    match_type: str = ""  # symbol, import, usage, route, component
    symbol_name: str = ""
    context: str = ""  # surrounding lines


@dataclass
class SearchResult:
    """Result of a repo search."""
    query: str = ""
    search_type: str = ""  # symbol, import, usage, route, component, text
    matches: List[SearchMatch] = field(default_factory=list)
    total_matches: int = 0
    files_searched: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "search_type": self.search_type,
            "total_matches": self.total_matches,
            "files_searched": self.files_searched,
            "duration_ms": round(self.duration_ms, 2),
            "matches": [
                {
                    "file_path": m.file_path,
                    "line_number": m.line_number,
                    "line_content": m.line_content.strip()[:200],
                    "match_type": m.match_type,
                    "symbol_name": m.symbol_name,
                }
                for m in self.matches[:100]
            ],
        }


class RepoSearch:
    """
    Intelligent repository search.
    Understands code structure, not just text.
    """

    # File extensions to search
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
        ".json", ".yaml", ".yml", ".toml", ".sh", ".bash",
        ".rs", ".go", ".java", ".rb", ".php",
    }

    # Directories to skip
    SKIP_DIRS = {
        "node_modules", "__pycache__", ".git", "venv", ".venv",
        "dist", "build", ".next", "coverage", ".cache",
        "site-packages", ".tox", ".mypy_cache", ".ruff_cache",
    }

    # Language-specific patterns
    PATTERNS = {
        "python": {
            "function": re.compile(r'^\s*def\s+(\w+)\s*\('),
            "class": re.compile(r'^\s*class\s+(\w+)'),
            "import": re.compile(r'^\s*(?:from\s+(\S+)\s+)?import\s+(.+)'),
            "route": re.compile(r'@(?:app|router|blueprint)\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)'),
            "variable": re.compile(r'^(\w+)\s*=\s*'),
        },
        "javascript": {
            "function": re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\('),
            "arrow_function": re.compile(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\('),
            "class": re.compile(r'(?:export\s+)?class\s+(\w+)'),
            "import": re.compile(r'import\s+.*?\s+from\s+["\']([^"\']+)["\']'),
            "route": re.compile(r'(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)'),
            "component": re.compile(r'(?:export\s+)?(?:default\s+)?function\s+(\w+)\s*\('),
        },
        "typescript": {
            "function": re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*[<\(]'),
            "class": re.compile(r'(?:export\s+)?class\s+(\w+)'),
            "interface": re.compile(r'(?:export\s+)?interface\s+(\w+)'),
            "type": re.compile(r'(?:export\s+)?type\s+(\w+)'),
            "import": re.compile(r'import\s+.*?\s+from\s+["\']([^"\']+)["\']'),
            "route": re.compile(r'(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)'),
        },
    }

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()

    def search(
        self,
        query: str,
        search_type: str = "text",
        file_pattern: str = "",
        max_results: int = 100,
    ) -> SearchResult:
        """
        Search the repository.

        Args:
            query: search query
            search_type: text, symbol, import, usage, route, component
            file_pattern: glob pattern to filter files
            max_results: maximum number of results
        """
        import time
        t0 = time.monotonic()

        result = SearchResult(query=query, search_type=search_type)

        if search_type == "symbol":
            result = self._search_symbols(query, max_results)
        elif search_type == "import":
            result = self._search_imports(query, max_results)
        elif search_type == "usage":
            result = self._search_usage(query, max_results)
        elif search_type == "route":
            result = self._search_routes(query, max_results)
        elif search_type == "component":
            result = self._search_components(query, max_results)
        else:
            result = self._search_text(query, file_pattern, max_results)

        result.duration_ms = (time.monotonic() - t0) * 1000
        return result

    def find_symbol(self, symbol_name: str) -> SearchResult:
        """Find where a symbol is defined."""
        return self.search(symbol_name, search_type="symbol")

    def find_usages(self, symbol_name: str) -> SearchResult:
        """Find all usages of a symbol."""
        return self.search(symbol_name, search_type="usage")

    def find_imports(self, module_name: str) -> SearchResult:
        """Find all imports of a module."""
        return self.search(module_name, search_type="import")

    def find_routes(self, path_pattern: str = "") -> SearchResult:
        """Find API routes."""
        return self.search(path_pattern, search_type="route")

    def find_components(self, name_pattern: str = "") -> SearchResult:
        """Find UI components."""
        return self.search(name_pattern, search_type="component")

    def _get_files(self, file_pattern: str = "") -> List[Path]:
        """Get list of files to search."""
        files = []
        for path in self._project_root.rglob(file_pattern or "*"):
            if path.is_file():
                # Skip unwanted directories
                parts = path.relative_to(self._project_root).parts
                if any(part in self.SKIP_DIRS for part in parts):
                    continue
                # Check extension
                if path.suffix in self.CODE_EXTENSIONS:
                    files.append(path)
        return files

    def _detect_language(self, file_path: Path) -> str:
        """Detect the language of a file."""
        ext = file_path.suffix
        if ext == ".py":
            return "python"
        elif ext in (".js", ".jsx", ".mjs"):
            return "javascript"
        elif ext in (".ts", ".tsx"):
            return "typescript"
        return "unknown"

    def _search_text(self, query: str, file_pattern: str,
                     max_results: int) -> SearchResult:
        """Plain text search."""
        result = SearchResult(query=query, search_type="text")
        files = self._get_files(file_pattern)
        result.files_searched = len(files)

        pattern = re.compile(re.escape(query), re.IGNORECASE)

        for file_path in files:
            if result.total_matches >= max_results:
                break
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.split("\n"), 1):
                    if result.total_matches >= max_results:
                        break
                    if pattern.search(line):
                        rel_path = str(file_path.relative_to(self._project_root))
                        result.matches.append(SearchMatch(
                            file_path=rel_path,
                            line_number=i,
                            line_content=line,
                            match_type="text",
                        ))
                        result.total_matches += 1
            except IOError:
                continue

        return result

    def _search_symbols(self, symbol_name: str, max_results: int) -> SearchResult:
        """Search for symbol definitions."""
        result = SearchResult(query=symbol_name, search_type="symbol")
        files = self._get_files()
        result.files_searched = len(files)

        for file_path in files:
            if result.total_matches >= max_results:
                break
            lang = self._detect_language(file_path)
            patterns = self.PATTERNS.get(lang, {})

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.split("\n"), 1):
                    if result.total_matches >= max_results:
                        break

                    for symbol_type, pattern in patterns.items():
                        if symbol_type in ("import", "route"):
                            continue
                        match = pattern.match(line)
                        if match:
                            name = match.group(1)
                            if symbol_name.lower() in name.lower():
                                rel_path = str(file_path.relative_to(self._project_root))
                                result.matches.append(SearchMatch(
                                    file_path=rel_path,
                                    line_number=i,
                                    line_content=line,
                                    match_type=f"symbol:{symbol_type}",
                                    symbol_name=name,
                                ))
                                result.total_matches += 1
            except IOError:
                continue

        return result

    def _search_imports(self, module_name: str, max_results: int) -> SearchResult:
        """Search for imports of a module."""
        result = SearchResult(query=module_name, search_type="import")
        files = self._get_files()
        result.files_searched = len(files)

        for file_path in files:
            if result.total_matches >= max_results:
                break
            lang = self._detect_language(file_path)
            patterns = self.PATTERNS.get(lang, {})
            import_pattern = patterns.get("import")

            if not import_pattern:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.split("\n"), 1):
                    if result.total_matches >= max_results:
                        break
                    match = import_pattern.match(line)
                    if match:
                        imported = match.group(1) or ""
                        if module_name.lower() in imported.lower():
                            rel_path = str(file_path.relative_to(self._project_root))
                            result.matches.append(SearchMatch(
                                file_path=rel_path,
                                line_number=i,
                                line_content=line,
                                match_type="import",
                                symbol_name=imported,
                            ))
                            result.total_matches += 1
            except IOError:
                continue

        return result

    def _search_usage(self, symbol_name: str, max_results: int) -> SearchResult:
        """Search for usages of a symbol."""
        result = SearchResult(query=symbol_name, search_type="usage")
        files = self._get_files()
        result.files_searched = len(files)

        pattern = re.compile(r'\b' + re.escape(symbol_name) + r'\b')

        for file_path in files:
            if result.total_matches >= max_results:
                break
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.split("\n"), 1):
                    if result.total_matches >= max_results:
                        break
                    if pattern.search(line):
                        rel_path = str(file_path.relative_to(self._project_root))
                        result.matches.append(SearchMatch(
                            file_path=rel_path,
                            line_number=i,
                            line_content=line,
                            match_type="usage",
                            symbol_name=symbol_name,
                        ))
                        result.total_matches += 1
            except IOError:
                continue

        return result

    def _search_routes(self, path_pattern: str, max_results: int) -> SearchResult:
        """Search for API routes."""
        result = SearchResult(query=path_pattern, search_type="route")
        files = self._get_files()
        result.files_searched = len(files)

        for file_path in files:
            if result.total_matches >= max_results:
                break
            lang = self._detect_language(file_path)
            patterns = self.PATTERNS.get(lang, {})
            route_pattern = patterns.get("route")

            if not route_pattern:
                # Also check for generic route patterns
                route_pattern = re.compile(r'["\'](\/api\/[^"\']+)["\']')

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.split("\n"), 1):
                    if result.total_matches >= max_results:
                        break
                    match = route_pattern.search(line)
                    if match:
                        route_path = match.group(1)
                        if not path_pattern or path_pattern in route_path:
                            rel_path = str(file_path.relative_to(self._project_root))
                            result.matches.append(SearchMatch(
                                file_path=rel_path,
                                line_number=i,
                                line_content=line,
                                match_type="route",
                                symbol_name=route_path,
                            ))
                            result.total_matches += 1
            except IOError:
                continue

        return result

    def _search_components(self, name_pattern: str, max_results: int) -> SearchResult:
        """Search for UI components."""
        result = SearchResult(query=name_pattern, search_type="component")
        files = self._get_files()
        result.files_searched = len(files)

        for file_path in files:
            if result.total_matches >= max_results:
                break
            lang = self._detect_language(file_path)
            if lang not in ("javascript", "typescript"):
                continue

            patterns = self.PATTERNS.get(lang, {})
            component_pattern = patterns.get("component") or patterns.get("function")

            if not component_pattern:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.split("\n"), 1):
                    if result.total_matches >= max_results:
                        break
                    match = component_pattern.match(line)
                    if match:
                        name = match.group(1)
                        if not name_pattern or name_pattern.lower() in name.lower():
                            # Check if it looks like a component (returns JSX)
                            rel_path = str(file_path.relative_to(self._project_root))
                            result.matches.append(SearchMatch(
                                file_path=rel_path,
                                line_number=i,
                                line_content=line,
                                match_type="component",
                                symbol_name=name,
                            ))
                            result.total_matches += 1
            except IOError:
                continue

        return result
