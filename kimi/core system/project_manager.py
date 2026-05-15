"""
ProjectManager — Single Source of Truth for the entire project.

All agents query PM for context instead of remembering themselves.
PM stores, indexes, validates. Does NOT generate code.

Usage:
    pm = ProjectManager(Path("/path/to/project"))
    pm.index_project()  # Full scan and indexing

    # Agent queries PM
    context = pm.query(agent="backend", question="What endpoints exist?", max_tokens=4000)

    # Agent reports result
    pm.update(agent="backend", action="created_file", result={"file": "auth.py", ...})

    # Validate proposed change
    is_valid, reason = pm.validate(agent="backend", proposal="Add middleware to app.py")
"""

import os
import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger

from .repo_explorer import RepoExplorer
from .symbol_extractor import SymbolExtractor
from .knowledge_base import KnowledgeBase
from .context_compressor import ContextCompressor
from .repo_validator import RepoValidator


@dataclass
class FileEntry:
    """Entry for a single file in the index."""
    path: str  # relative path from project root
    size: int
    modified: float
    hash: str  # content hash for change detection
    language: str  # python, javascript, etc.
    summary: str = ""  # AI-generated summary (short)
    symbols: List[Dict] = field(default_factory=list)  # classes, functions
    imports: List[str] = field(default_factory=list)  # what this file imports
    exported: List[str] = field(default_factory=list)  # what this file exports
    is_entry_point: bool = False
    is_test: bool = False
    is_config: bool = False


@dataclass
class ProjectSnapshot:
    """Snapshot of project state at a point in time."""
    timestamp: str
    files: Dict[str, FileEntry]
    tech_stack: List[str]
    entry_points: List[str]
    total_symbols: int
    dependencies: Dict[str, List[str]]  # file -> [files it depends on]


class ProjectManager:
    """
    Project Manager — the brain of the system.

    Responsibilities:
    1. Index all files in the project
    2. Extract symbols (classes, functions, variables)
    3. Build dependency graph
    4. Answer agent queries with relevant context
    5. Validate proposed changes
    6. Maintain decision log
    7. Track errors and fixes
    """

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.explorer = RepoExplorer(self.project_path)
        self.symbol_extractor = SymbolExtractor()
        self.kb = KnowledgeBase(self.project_path)
        self.compressor = ContextCompressor()
        self.validator = RepoValidator(self.project_path)

        # Current state
        self.files: Dict[str, FileEntry] = {}
        self.tech_stack: List[str] = []
        self.entry_points: List[str] = []
        self.dependencies: Dict[str, List[str]] = {}
        self.decisions: List[Dict] = []
        self.errors: List[Dict] = []

        # Snapshots for rollback
        self.snapshots: List[ProjectSnapshot] = []

        # Cache for frequent queries
        self._query_cache: Dict[str, Tuple[str, float]] = {}  # query -> (answer, timestamp)
        self._cache_ttl = 300  # 5 minutes

        logger.info(f"ProjectManager initialized for: {self.project_path}")

    # ============================================================
    # INDEXING
    # ============================================================

    def index_project(self, force: bool = False) -> Dict[str, Any]:
        """
        Full scan and index of the project.

        Returns stats dict with counts.
        """
        logger.info(f"Indexing project: {self.project_path}")

        # 1. Discover all files
        file_paths = self.explorer.discover_files()
        logger.info(f"Found {len(file_paths)} files")

        # 2. Process each file
        self.files = {}
        total_symbols = 0

        for rel_path in file_paths:
            full_path = self.project_path / rel_path

            try:
                stat = full_path.stat()
                content = full_path.read_text(encoding="utf-8", errors="ignore")

                # Detect language
                language = self._detect_language(rel_path)

                # Extract symbols
                symbols = self.symbol_extractor.extract(content, language)
                total_symbols += len(symbols)

                # Detect imports/exports
                imports, exported = self._extract_imports_exports(content, language)

                # Generate summary (first 200 chars + structure)
                summary = self._generate_summary(content, symbols)

                # Classify file
                is_entry = self._is_entry_point(rel_path, content, symbols)
                is_test = "test" in rel_path.lower() or rel_path.startswith("tests/")
                is_config = rel_path in [
                    "package.json", "requirements.txt", "pyproject.toml",
                    "setup.py", "Dockerfile", "docker-compose.yml", ".env.example"
                ] or any(rel_path.endswith(ext) for ext in [".config.js", ".config.ts", ".ini", ".cfg", ".yaml", ".yml", ".toml"])

                entry = FileEntry(
                    path=rel_path,
                    size=stat.st_size,
                    modified=stat.st_mtime,
                    hash=hashlib.sha256(content.encode()).hexdigest()[:16],
                    language=language,
                    summary=summary,
                    symbols=symbols,
                    imports=imports,
                    exported=exported,
                    is_entry_point=is_entry,
                    is_test=is_test,
                    is_config=is_config
                )

                self.files[rel_path] = entry

            except Exception as e:
                logger.warning(f"Failed to index {rel_path}: {e}")
                continue

        # 3. Detect tech stack
        self.tech_stack = self._detect_tech_stack()

        # 4. Find entry points
        self.entry_points = [f.path for f in self.files.values() if f.is_entry_point]

        # 5. Build dependency graph
        self.dependencies = self._build_dependency_graph()

        # 6. Save snapshot
        self._save_snapshot()

        # 7. Save to knowledge base
        self.kb.save_index(self.files, self.tech_stack, self.entry_points)

        stats = {
            "total_files": len(self.files),
            "total_symbols": total_symbols,
            "total_dependencies": sum(len(v) for v in self.dependencies.values()),
            "tech_stack": self.tech_stack,
            "entry_points": self.entry_points,
            "languages": self._get_language_stats()
        }

        logger.info(f"Indexing complete: {stats['total_files']} files, {stats['total_symbols']} symbols")
        return stats

    def reindex_file(self, rel_path: str) -> bool:
        """Reindex a single file after change."""
        if rel_path not in self.files:
            return False

        full_path = self.project_path / rel_path
        if not full_path.exists():
            del self.files[rel_path]
            return True

        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            entry = self.files[rel_path]

            entry.size = full_path.stat().st_size
            entry.modified = full_path.stat().st_mtime
            entry.hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            entry.symbols = self.symbol_extractor.extract(content, entry.language)
            entry.imports, entry.exported = self._extract_imports_exports(content, entry.language)
            entry.summary = self._generate_summary(content, entry.symbols)

            # Rebuild dependencies for this file
            self.dependencies = self._build_dependency_graph()

            # Clear query cache
            self._query_cache.clear()

            return True
        except Exception as e:
            logger.error(f"Reindex failed for {rel_path}: {e}")
            return False

    # ============================================================
    # QUERY — Agents ask PM for context
    # ============================================================

    def query(self, agent: str, question: str, max_tokens: int = 8000) -> str:
        """
        Answer agent query with relevant project context.

        This is the HEART of PM. It must:
        1. Understand what agent needs
        2. Find relevant files/symbols
        3. Compress to fit max_tokens
        4. Return structured, useful context

        Args:
            agent: Which agent is asking (teamlead, backend, etc.)
            question: What they want to know
            max_tokens: How much context they can handle (~4 chars per token)

        Returns:
            Compressed context string
        """
        # Check cache
        cache_key = f"{agent}:{question}"
        if cache_key in self._query_cache:
            answer, ts = self._query_cache[cache_key]
            if datetime.now().timestamp() - ts < self._cache_ttl:
                logger.debug(f"PM cache hit: {cache_key[:50]}...")
                return answer

        # Parse question to understand intent
        intent = self._parse_query_intent(question)
        logger.info(f"PM query from {agent}: {intent['type']} | {question[:80]}...")

        # Build context based on intent
        context_parts = []

        # Always include: project overview (compressed)
        overview = self._get_project_overview()
        context_parts.append(f"## PROJECT OVERVIEW\n{overview}\n")

        # Intent-specific context
        if intent["type"] == "architecture":
            context_parts.append(self._get_architecture_context())
        elif intent["type"] == "file_content":
            context_parts.append(self._get_file_context(intent.get("target_file", "")))
        elif intent["type"] == "api_endpoints":
            context_parts.append(self._get_api_context())
        elif intent["type"] == "dependencies":
            context_parts.append(self._get_dependency_context(intent.get("target_file", "")))
        elif intent["type"] == "testing":
            context_parts.append(self._get_testing_context())
        elif intent["type"] == "general":
            context_parts.append(self._get_general_context())

        # Add relevant files based on keywords in question
        relevant_files = self._find_relevant_files(question, max_files=5)
        if relevant_files:
            context_parts.append("## RELEVANT FILES\n")
            for f in relevant_files:
                entry = self.files.get(f)
                if entry:
                    context_parts.append(f"### {f}\n")
                    context_parts.append(f"Language: {entry.language}\n")
                    context_parts.append(f"Summary: {entry.summary}\n")
                    if entry.symbols:
                        context_parts.append(f"Symbols: {', '.join(s['name'] for s in entry.symbols[:10])}\n")
                    context_parts.append(f"Size: {entry.size} bytes\n\n")

        # Add decision log (recent decisions)
        if self.decisions:
            recent = self.decisions[-5:]
            context_parts.append("## RECENT DECISIONS\n")
            for d in recent:
                context_parts.append(f"- [{d['timestamp']}] {d['agent']}: {d['decision']}\n")

        # Combine and compress
        full_context = "\n".join(context_parts)
        compressed = self.compressor.compress(full_context, max_chars=max_tokens * 4)

        # Cache result
        self._query_cache[cache_key] = (compressed, datetime.now().timestamp())

        logger.info(f"PM answered {agent} with {len(compressed)} chars")
        return compressed

    # ============================================================
    # UPDATE — Agents report results to PM
    # ============================================================

    def update(self, agent: str, action: str, result: Dict[str, Any]) -> bool:
        """
        Update PM knowledge with agent action result.

        Args:
            agent: Which agent acted
            action: What they did (created_file, modified_file, error, decision)
            result: Details of the action
        """
        timestamp = datetime.now().isoformat()

        if action == "created_file" or action == "modified_file":
            files = result.get("files_created", []) or result.get("files", [])
            for f in files:
                # Reindex changed files
                rel_path = str(Path(f).relative_to(self.project_path)) if self.project_path in Path(f).parents else f
                if rel_path in self.files or (self.project_path / rel_path).exists():
                    self.reindex_file(rel_path)
                    logger.info(f"PM reindexed: {rel_path}")

        elif action == "decision":
            self.decisions.append({
                "timestamp": timestamp,
                "agent": agent,
                "decision": result.get("decision", ""),
                "reason": result.get("reason", ""),
                "context": result.get("context", "")
            })
            logger.info(f"PM logged decision from {agent}")

        elif action == "error":
            self.errors.append({
                "timestamp": timestamp,
                "agent": agent,
                "error": result.get("error", ""),
                "file": result.get("file", ""),
                "fix": result.get("fix", "")
            })
            logger.warning(f"PM logged error from {agent}: {result.get('error', '')[:100]}")

        elif action == "agent_completed":
            # Log completion for tracking
            self.decisions.append({
                "timestamp": timestamp,
                "agent": agent,
                "decision": f"Completed task: {result.get('summary', 'unknown')}",
                "reason": "Agent finished successfully",
                "files": result.get("files_created", [])
            })

        # Clear cache since state changed
        self._query_cache.clear()

        return True

    # ============================================================
    # VALIDATE — Check if proposed change is safe
    # ============================================================

    def validate(self, agent: str, proposal: str) -> Tuple[bool, str]:
        """
        Validate if a proposed change is safe.

        Returns:
            (is_valid, reason)
        """
        return self.validator.validate(proposal, self.files, self.dependencies)

    # ============================================================
    # SNAPSHOTS & ROLLBACK
    # ============================================================

    def create_snapshot(self) -> str:
        """Create manual snapshot. Returns snapshot ID."""
        return self._save_snapshot()

    def rollback(self, snapshot_id: Optional[str] = None) -> bool:
        """Rollback to previous snapshot."""
        if not self.snapshots:
            return False

        if snapshot_id:
            for snap in self.snapshots:
                if snap.timestamp == snapshot_id:
                    self._restore_snapshot(snap)
                    return True
            return False
        else:
            # Rollback to latest
            self._restore_snapshot(self.snapshots[-1])
            return True

    # ============================================================
    # GETTERS
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get current project stats."""
        return {
            "total_files": len(self.files),
            "total_symbols": sum(len(f.symbols) for f in self.files.values()),
            "tech_stack": self.tech_stack,
            "entry_points": self.entry_points,
            "languages": self._get_language_stats(),
            "decisions": len(self.decisions),
            "errors": len(self.errors),
            "snapshots": len(self.snapshots)
        }

    def get_file_tree(self, max_depth: int = 3) -> List[str]:
        """Get file tree for display."""
        return self.explorer.get_tree_display(self.files, max_depth)

    def get_file_content(self, rel_path: str) -> Optional[str]:
        """Get file content."""
        full_path = self.project_path / rel_path
        if full_path.exists():
            try:
                return full_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return None
        return None

    def search_symbols(self, name: str) -> List[Dict]:
        """Search for symbol by name across all files."""
        results = []
        for rel_path, entry in self.files.items():
            for sym in entry.symbols:
                if name.lower() in sym["name"].lower():
                    results.append({
                        "file": rel_path,
                        "symbol": sym["name"],
                        "type": sym["type"],
                        "line": sym.get("line", 0)
                    })
        return results

    # ============================================================
    # PRIVATE HELPERS
    # ============================================================

    def _detect_language(self, rel_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(rel_path).suffix.lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".md": "markdown",
            ".sql": "sql",
            ".sh": "bash",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".php": "php",
            ".rb": "ruby",
            ".vue": "vue",
            ".svelte": "svelte",
            ".dockerfile": "dockerfile",
        }
        return mapping.get(ext, "unknown")

    def _extract_imports_exports(self, content: str, language: str) -> Tuple[List[str], List[str]]:
        """Extract imports and exports from file content."""
        imports = []
        exported = []

        if language == "python":
            # import x, from x import y
            for match in re.finditer(r"^(?:from\s+(\S+)\s+import|import\s+(\S+))", content, re.MULTILINE):
                imports.append(match.group(1) or match.group(2))
            # def / class at top level
            for match in re.finditer(r"^(?:def|class)\s+(\w+)", content, re.MULTILINE):
                exported.append(match.group(1))

        elif language in ("javascript", "typescript"):
            # import x from 'y', require('y')
            for match in re.finditer(r"import\s+.*?\s+from\s+['\"](.+?)['\"]|require\(['\"](.+?)['\"]\)", content):
                imports.append(match.group(1) or match.group(2))
            # export
            for match in re.finditer(r"export\s+(?:default\s+)?(?:class|function|const|let|var)?\s*(\w+)", content):
                exported.append(match.group(1))

        return imports, exported

    def _generate_summary(self, content: str, symbols: List[Dict]) -> str:
        """Generate short summary of file."""
        lines = content.splitlines()
        first_line = lines[0] if lines else ""

        # Get docstring if present
        docstring = ""
        if len(lines) > 1:
            second = lines[1].strip()
            if second.startswith(chr(34)*3) or second.startswith(chr(39)*3):
                docstring = second[:100]

        # List main symbols
        main_symbols = [s["name"] for s in symbols if s["type"] in ("class", "function")][:5]

        summary = f"{first_line[:80]}"
        if main_symbols:
            summary += f" | Main: {', '.join(main_symbols)}"
        if docstring:
            summary += f" | {docstring}"

        return summary[:200]

    def _is_entry_point(self, rel_path: str, content: str, symbols: List[Dict]) -> bool:
        """Detect if file is an entry point."""
        name = Path(rel_path).name.lower()

        # Common entry point names
        if name in ("main.py", "app.py", "index.js", "index.ts", "server.py", "manage.py", "run.py", "__main__.py"):
            return True

        # Has if __name__ == "__main__"
        if 'if __name__ == "__main__"' in content or "if __name__ == '__main__'" in content:
            return True

        # Has app = Flask() or app = FastAPI()
        if re.search(r"(Flask|FastAPI|Express|createApp)\s*\(", content):
            return True

        return False

    def _detect_tech_stack(self) -> List[str]:
        """Detect tech stack from files."""
        stack = set()

        for entry in self.files.values():
            name = Path(entry.path).name.lower()

            if name == "package.json":
                stack.add("Node.js")
            elif name == "requirements.txt" or name == "pyproject.toml":
                stack.add("Python")
            elif name == "cargo.toml":
                stack.add("Rust")
            elif name == "go.mod":
                stack.add("Go")
            elif name == "pom.xml" or name == "build.gradle":
                stack.add("Java")
            elif name == "gemfile":
                stack.add("Ruby")
            elif name == "composer.json":
                stack.add("PHP")
            elif name == "dockerfile" or name == "docker-compose.yml":
                stack.add("Docker")

            # Framework detection from content
            if entry.path.endswith(".py"):
                content = self.get_file_content(entry.path) or ""
                if "flask" in content.lower():
                    stack.add("Flask")
                if "fastapi" in content.lower():
                    stack.add("FastAPI")
                if "django" in content.lower():
                    stack.add("Django")

            if entry.path.endswith(".js") or entry.path.endswith(".ts"):
                content = self.get_file_content(entry.path) or ""
                if "react" in content.lower():
                    stack.add("React")
                if "vue" in content.lower():
                    stack.add("Vue")
                if "angular" in content.lower():
                    stack.add("Angular")
                if "express" in content.lower():
                    stack.add("Express")
                if "next" in content.lower():
                    stack.add("Next.js")

        # Database detection
        for entry in self.files.values():
            content = self.get_file_content(entry.path) or ""
            if "sqlalchemy" in content.lower() or "sqlite" in content.lower():
                stack.add("SQLAlchemy")
            if "mongodb" in content.lower() or "mongoose" in content.lower():
                stack.add("MongoDB")
            if "postgresql" in content.lower() or "psycopg" in content.lower():
                stack.add("PostgreSQL")
            if "mysql" in content.lower():
                stack.add("MySQL")

        return sorted(list(stack))

    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build file dependency graph."""
        graph = {}

        for rel_path, entry in self.files.items():
            deps = []

            # Check imports against other files
            for imp in entry.imports:
                # Simple matching: import name -> file name
                for other_path, other_entry in self.files.items():
                    if other_path == rel_path:
                        continue
                    # Check if import matches exported symbols
                    if any(imp.lower() in exp.lower() for exp in other_entry.exported):
                        deps.append(other_path)
                    # Check if import matches file name
                    other_name = Path(other_path).stem
                    if imp.lower() == other_name.lower():
                        deps.append(other_path)

            graph[rel_path] = list(set(deps))

        return graph

    def _get_language_stats(self) -> Dict[str, int]:
        """Get file count per language."""
        stats = {}
        for entry in self.files.values():
            stats[entry.language] = stats.get(entry.language, 0) + 1
        return stats

    def _save_snapshot(self) -> str:
        """Save current state as snapshot."""
        snap = ProjectSnapshot(
            timestamp=datetime.now().isoformat(),
            files=self.files.copy(),
            tech_stack=self.tech_stack.copy(),
            entry_points=self.entry_points.copy(),
            total_symbols=sum(len(f.symbols) for f in self.files.values()),
            dependencies=self.dependencies.copy()
        )
        self.snapshots.append(snap)

        # Keep only last 10 snapshots
        if len(self.snapshots) > 10:
            self.snapshots = self.snapshots[-10:]

        return snap.timestamp

    def _restore_snapshot(self, snapshot: ProjectSnapshot):
        """Restore state from snapshot."""
        self.files = snapshot.files
        self.tech_stack = snapshot.tech_stack
        self.entry_points = snapshot.entry_points
        self.dependencies = snapshot.dependencies
        self._query_cache.clear()
        logger.info(f"Restored snapshot: {snapshot.timestamp}")

    def _parse_query_intent(self, question: str) -> Dict[str, str]:
        """Parse agent query to understand intent."""
        q = question.lower()

        if any(w in q for w in ["architect", "structure", "overview", "how organized"]):
            return {"type": "architecture"}
        elif any(w in q for w in ["endpoint", "api", "route", "url", "path"]):
            return {"type": "api_endpoints"}
        elif any(w in q for w in ["file", "content", "code in", "show me", "what does"]):
            # Try to extract file name
            words = question.split()
            for w in words:
                if "." in w and any(w.endswith(ext) for ext in [".py", ".js", ".ts", ".html", ".css"]):
                    return {"type": "file_content", "target_file": w.strip("'\"`")}
            return {"type": "file_content"}
        elif any(w in q for w in ["depend", "import", "use", "call", "reference"]):
            return {"type": "dependencies"}
        elif any(w in q for w in ["test", "testing", "pytest", "unittest"]):
            return {"type": "testing"}
        else:
            return {"type": "general"}

    def _get_project_overview(self) -> str:
        """Get compressed project overview."""
        parts = [
            f"Project: {self.project_path.name}",
            f"Files: {len(self.files)}",
            f"Tech: {', '.join(self.tech_stack) if self.tech_stack else 'Unknown'}",
            f"Entry points: {', '.join(self.entry_points) if self.entry_points else 'None detected'}"
        ]
        return " | ".join(parts)

    def _get_architecture_context(self) -> str:
        """Get architecture-related context."""
        parts = ["## ARCHITECTURE\n"]

        # Entry points and their roles
        if self.entry_points:
            parts.append("Entry Points:\n")
            for ep in self.entry_points[:5]:
                entry = self.files.get(ep)
                if entry:
                    parts.append(f"  - {ep}: {entry.summary[:100]}\n")

        # Key modules (non-test, non-config files with many symbols)
        key_files = sorted(
            [f for f in self.files.values() if not f.is_test and not f.is_config],
            key=lambda x: len(x.symbols),
            reverse=True
        )[:10]

        if key_files:
            parts.append("\nKey Modules:\n")
            for f in key_files:
                parts.append(f"  - {f.path} ({len(f.symbols)} symbols)\n")

        return "".join(parts)

    def _get_file_context(self, target_file: str) -> str:
        """Get context for a specific file."""
        if target_file in self.files:
            entry = self.files[target_file]
            content = self.get_file_content(target_file)

            parts = [f"## FILE: {target_file}\n"]
            parts.append(f"Language: {entry.language}\n")
            parts.append(f"Size: {entry.size} bytes\n")
            parts.append(f"Summary: {entry.summary}\n\n")

            if entry.symbols:
                parts.append("Symbols:\n")
                for s in entry.symbols[:20]:
                    parts.append(f"  - {s['type']} {s['name']} (line {s.get('line', '?')})\n")

            # Show first 50 lines of content if available
            if content:
                lines = content.splitlines()[:50]
                parts.append(f"\nFirst {len(lines)} lines:\n```\n")
                parts.append("\n".join(lines))
                parts.append("\n```\n")

            return "".join(parts)

        return f"## FILE: {target_file}\nFile not found in index.\n"

    def _get_api_context(self) -> str:
        """Get API endpoints context."""
        parts = ["## API ENDPOINTS\n"]

        # Search for route definitions
        endpoints = []
        for rel_path, entry in self.files.items():
            if entry.language not in ("python", "javascript", "typescript"):
                continue

            content = self.get_file_content(rel_path) or ""

            # Flask/FastAPI routes
            for match in re.finditer(r"@(?:app|router)\.route\(['\"](.+?)['\"]\)", content):
                endpoints.append({"path": match.group(1), "file": rel_path, "framework": "Flask/FastAPI"})

            # Express routes
            for match in re.finditer(r"\.(get|post|put|delete|patch)\(['\"](.+?)['\"]", content):
                endpoints.append({"path": match.group(2), "file": rel_path, "method": match.group(1).upper(), "framework": "Express"})

        if endpoints:
            for ep in endpoints[:20]:
                parts.append(f"  - {ep.get('method', 'GET')} {ep['path']} ({ep['framework']}) in {ep['file']}\n")
        else:
            parts.append("No API endpoints detected.\n")

        return "".join(parts)

    def _get_dependency_context(self, target_file: str) -> str:
        """Get dependency context for a file."""
        if target_file not in self.files:
            return f"## DEPENDENCIES: {target_file}\nFile not found.\n"

        deps = self.dependencies.get(target_file, [])
        reverse_deps = [f for f, d in self.dependencies.items() if target_file in d]

        parts = [f"## DEPENDENCIES: {target_file}\n"]

        if deps:
            parts.append(f"This file imports/uses: {', '.join(deps[:10])}\n")
        if reverse_deps:
            parts.append(f"Files that use this: {', '.join(reverse_deps[:10])}\n")

        entry = self.files[target_file]
        if entry.imports:
            parts.append(f"\nImports: {', '.join(entry.imports[:15])}\n")
        if entry.exported:
            parts.append(f"Exports: {', '.join(entry.exported[:15])}\n")

        return "".join(parts)

    def _get_testing_context(self) -> str:
        """Get testing-related context."""
        parts = ["## TESTING\n"]

        test_files = [f for f in self.files.values() if f.is_test]
        if test_files:
            parts.append(f"Test files: {len(test_files)}\n")
            for tf in test_files[:10]:
                parts.append(f"  - {tf.path}\n")
        else:
            parts.append("No test files detected.\n")

        # Test framework detection
        frameworks = set()
        for tf in test_files:
            content = self.get_file_content(tf.path) or ""
            if "pytest" in content or "import pytest" in content:
                frameworks.add("pytest")
            if "unittest" in content:
                frameworks.add("unittest")
            if "jest" in content or "describe(" in content:
                frameworks.add("jest")

        if frameworks:
            parts.append(f"\nFrameworks: {', '.join(frameworks)}\n")

        return "".join(parts)

    def _get_general_context(self) -> str:
        """Get general project context."""
        parts = ["## PROJECT STRUCTURE\n"]

        # Top-level directories
        dirs = set()
        for f in self.files:
            parts_path = Path(f).parts
            if len(parts_path) > 1:
                dirs.add(parts_path[0])

        if dirs:
            parts.append(f"Directories: {', '.join(sorted(dirs))}\n")

        # File count by type
        lang_stats = self._get_language_stats()
        if lang_stats:
            parts.append("\nFiles by language:\n")
            for lang, count in sorted(lang_stats.items(), key=lambda x: -x[1]):
                parts.append(f"  - {lang}: {count}\n")

        # Config files
        configs = [f.path for f in self.files.values() if f.is_config]
        if configs:
            parts.append(f"\nConfig files: {', '.join(configs[:10])}\n")

        return "".join(parts)

    def _find_relevant_files(self, question: str, max_files: int = 5) -> List[str]:
        """Find files relevant to the question."""
        q = question.lower()
        scores = {}

        for rel_path, entry in self.files.items():
            score = 0

            # Name match
            name = Path(rel_path).name.lower()
            if any(word in name for word in q.split() if len(word) > 3):
                score += 10

            # Symbol match
            for sym in entry.symbols:
                sym_name = sym["name"].lower()
                if any(word in sym_name for word in q.split() if len(word) > 3):
                    score += 5

            # Summary match
            if any(word in entry.summary.lower() for word in q.split() if len(word) > 3):
                score += 3

            # Language-specific keywords
            if "test" in q and entry.is_test:
                score += 15
            if "config" in q and entry.is_config:
                score += 15
            if "entry" in q and entry.is_entry_point:
                score += 15

            if score > 0:
                scores[rel_path] = score

        # Return top files
        sorted_files = sorted(scores.items(), key=lambda x: -x[1])
        return [f[0] for f in sorted_files[:max_files]]
