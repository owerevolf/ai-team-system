"""
Multi-Stage Retrieval Pipeline — hierarchical context retrieval.

Stages:
1. Cheap filtering: filenames, tags, modified files, module scopes
2. Dependency narrowing: import graph, impact graph, related symbols
3. Symbol prioritization: hot symbols, frequently modified, execution-relevant
4. Context assembly: deduplication, token budgeting, relevance scoring

Goal: NOT "dump entire repo into 1M context"
Goal: "deliver exactly what's needed, nothing more"
"""

import hashlib
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

from loguru import logger


class RetrievalStageResult:
    """Result from a single retrieval stage."""

    def __init__(self, stage_name: str, files: List[str], symbols: List[str], cost: float):
        self.stage_name = stage_name
        self.files = files
        self.symbols = symbols
        self.cost = cost  # processing time in ms


class MultiStageRetrievalPipeline:
    """
    Hierarchical retrieval that narrows context at each stage.

    Stage 1: Cheap filtering — fast heuristics to narrow candidate set
    Stage 2: Dependency narrowing — use graph to find related files
    Stage 3: Symbol prioritization — rank symbols by relevance
    Stage 4: Context assembly — build final context within budget
    """

    DEFAULT_MAX_FILES = 15
    DEFAULT_MAX_SYMBOLS = 50
    DEFAULT_TOKEN_BUDGET = 12000

    def __init__(
        self,
        files: Dict[str, Any],
        dependencies: Dict[str, List[str]],
        reverse_dependencies: Optional[Dict[str, List[str]]] = None,
        hot_files: Optional[Dict[str, int]] = None,
        max_files: int = DEFAULT_MAX_FILES,
        max_symbols: int = DEFAULT_MAX_SYMBOLS,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ):
        self.files = files
        self.dependencies = dependencies
        self._reverse_deps = reverse_dependencies or self._build_reverse_deps()
        self._hot_files = hot_files or {}
        self._max_files = max_files
        self._max_symbols = max_symbols
        self._token_budget = token_budget

        # Stage statistics
        self._stage_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            'calls': 0, 'total_ms': 0.0, 'avg_ms': 0.0,
        })

    def _build_reverse_deps(self) -> Dict[str, List[str]]:
        reverse: Dict[str, List[str]] = {}
        for source, targets in self.dependencies.items():
            for target in targets:
                if target not in reverse:
                    reverse[target] = []
                reverse[target].append(source)
        return reverse

    def retrieve(
        self,
        query: str,
        agent: str = "unknown",
        max_files: int = -1,
        max_symbols: int = -1,
        token_budget: int = -1,
    ) -> Tuple[str, List[RetrievalStageResult]]:
        """
        Execute multi-stage retrieval pipeline.

        Returns:
            Tuple of (context_string, stage_results)
        """
        if max_files < 0:
            max_files = self._max_files
        if max_symbols < 0:
            max_symbols = self._max_symbols
        if token_budget < 0:
            token_budget = self._token_budget

        stage_results: List[RetrievalStageResult] = []

        # ── Stage 1: Cheap Filtering ──
        start = time.time()
        candidate_files = self._stage1_cheap_filtering(query)
        stage_results.append(RetrievalStageResult(
            'cheap_filtering', candidate_files, [],
            (time.time() - start) * 1000,
        ))

        # ── Stage 2: Dependency Narrowing ──
        start = time.time()
        narrowed_files, related_symbols = self._stage2_dependency_narrowing(
            candidate_files, query
        )
        stage_results.append(RetrievalStageResult(
            'dependency_narrowing', narrowed_files, related_symbols,
            (time.time() - start) * 1000,
        ))

        # ── Stage 3: Symbol Prioritization ──
        start = time.time()
        prioritized_symbols = self._stage3_symbol_prioritization(
            narrowed_files, related_symbols, query, max_symbols
        )
        stage_results.append(RetrievalStageResult(
            'symbol_prioritization', narrowed_files, prioritized_symbols,
            (time.time() - start) * 1000,
        ))

        # ── Stage 4: Context Assembly ──
        start = time.time()
        context = self._stage4_context_assembly(
            narrowed_files, prioritized_symbols, query, token_budget
        )
        stage_results.append(RetrievalStageResult(
            'context_assembly', narrowed_files, prioritized_symbols,
            (time.time() - start) * 1000,
        ))

        return context, stage_results

    # ── STAGE 1: Cheap Filtering ──

    def _stage1_cheap_filtering(self, query: str) -> List[str]:
        """
        Fast heuristics to narrow candidate files.

        Signals:
        - Filename match
        - Path match
        - Recently modified
        - Hot files (frequently accessed)
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        candidates: Dict[str, float] = {}

        for file_path, entry in self.files.items():
            score = 0.0

            # Filename match
            filename = file_path.lower()
            for word in query_words:
                if len(word) > 2 and word in filename:
                    score += 5.0

            # Hot file bonus
            hot_score = self._hot_files.get(file_path, 0)
            if hot_score > 0:
                score += min(hot_score * 0.5, 5.0)

            # Recently modified bonus
            if entry.modified > 0:
                age_days = (time.time() - entry.modified) / 86400
                if age_days < 7:
                    score += 3.0
                elif age_days < 30:
                    score += 1.0

            # Entry point bonus
            if entry.is_entry_point:
                score += 2.0

            if score > 0:
                candidates[file_path] = score

        # Sort by score, take top candidates
        sorted_files = sorted(candidates.items(), key=lambda x: -x[1])
        return [f for f, _ in sorted_files[:self._max_files * 3]]

    # ── STAGE 2: Dependency Narrowing ──

    def _stage2_dependency_narrowing(
        self, candidate_files: List[str], query: str
    ) -> Tuple[List[str], List[str]]:
        """
        Use dependency graph to find related files and symbols.

        - Include direct dependencies of candidates
        - Include reverse dependencies (dependents)
        - Extract related symbols from dependency chain
        """
        narrowed: Set[str] = set(candidate_files)
        related_symbols: Set[str] = set()

        for file_path in candidate_files[:10]:  # Limit to top 10 for perf
            # Add direct dependencies
            for dep in self.dependencies.get(file_path, [])[:5]:
                narrowed.add(dep)

            # Add reverse dependencies
            for rev_dep in self._reverse_deps.get(file_path, [])[:5]:
                narrowed.add(rev_dep)

            # Extract symbols from candidates
            if file_path in self.files:
                entry = self.files[file_path]
                for sym in entry.symbols[:10]:
                    sym_name = sym.get('name', '')
                    if sym_name:
                        related_symbols.add(sym_name)

        return list(narrowed)[:self._max_files * 2], list(related_symbols)

    # ── STAGE 3: Symbol Prioritization ──

    def _stage3_symbol_prioritization(
        self,
        files: List[str],
        related_symbols: List[str],
        query: str,
        max_symbols: int,
    ) -> List[str]:
        """
        Rank symbols by relevance to query.

        Signals:
        - Name match with query
        - Symbol type (classes/functions > variables)
        - File importance (entry points > tests > config)
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        symbol_scores: Dict[str, float] = {}

        for file_path in files:
            if file_path not in self.files:
                continue

            entry = self.files[file_path]

            for sym in entry.symbols:
                sym_name = sym.get('name', '')
                if not sym_name or sym_name in symbol_scores:
                    continue

                score = 0.0

                # Name match with query
                for word in query_words:
                    if len(word) > 2 and word in sym_name.lower():
                        score += 10.0

                # Related symbol bonus
                if sym_name in related_symbols:
                    score += 5.0

                # Type bonus
                sym_type = sym.get('type', '')
                if sym_type in ('class', 'function', 'interface'):
                    score += 3.0
                elif sym_type in ('method', 'route'):
                    score += 2.0

                # File importance bonus
                if entry.is_entry_point:
                    score += 2.0

                if score > 0:
                    symbol_scores[sym_name] = score

        sorted_symbols = sorted(symbol_scores.items(), key=lambda x: -x[1])
        return [s for s, _ in sorted_symbols[:max_symbols]]

    # ── STAGE 4: Context Assembly ──

    def _stage4_context_assembly(
        self,
        files: List[str],
        prioritized_symbols: List[str],
        query: str,
        token_budget: int,
    ) -> str:
        """
        Build final context string within token budget.

        Strategy:
        - Deduplicate content
        - Prioritize high-value files
        - Compress symbol lists
        - Enforce token budget
        """
        parts = []
        used_chars = 0
        used_files = 0
        seen_content: Set[str] = set()  # Deduplication

        # Header
        header = f"## PROJECT CONTEXT\n## QUERY: {query[:100]}\n\n"
        parts.append(header)
        used_chars += len(header)

        # Build file blocks
        for file_path in files:
            if used_files >= self._max_files:
                break
            if used_chars >= token_budget:
                break

            if file_path not in self.files:
                continue

            entry = self.files[file_path]
            block = self._format_file_block_compact(
                entry, prioritized_symbols
            )

            # Deduplication
            block_hash = hashlib.md5(block.encode()).hexdigest()[:16]
            if block_hash in seen_content:
                continue
            seen_content.add(block_hash)

            block_len = len(block)
            if used_chars + block_len > token_budget:
                # Try truncated version
                remaining = token_budget - used_chars
                if remaining > 200:
                    block = block[:remaining] + "\n... (truncated)\n"
                    parts.append(block)
                    used_chars += len(block)
                    used_files += 1
                break

            parts.append(block)
            used_chars += block_len
            used_files += 1

        return ''.join(parts)

    def _format_file_block_compact(
        self, entry: Any, prioritized_symbols: List[str]
    ) -> str:
        """Format a file entry as a compact context block."""
        lines = [f"### {entry.path}\n"]

        # Only include prioritized symbols
        matching_syms = []
        other_syms = []

        for sym in entry.symbols:
            name = sym.get('name', '')
            if name in prioritized_symbols:
                matching_syms.append(name)
            elif not name.startswith('_'):
                other_syms.append(name)

        display = (matching_syms + other_syms)[:10]
        if display:
            lines.append(f"symbols: {', '.join(display)}\n")

        # Only include key imports
        if entry.imports:
            key_imports = [i for i in entry.imports if not self._is_external_import(i)][:5]
            if key_imports:
                lines.append(f"imports: {', '.join(key_imports)}\n")

        lines.append("\n")
        return ''.join(lines)

    @staticmethod
    def _is_external_import(import_path: str) -> bool:
        """Quick check if import is external."""
        first = import_path.split('.')[0].split('/')[0]
        stdlib = {
            'os', 'sys', 'json', 're', 'pathlib', 'typing', 'datetime',
            'collections', 'itertools', 'functools', 'math', 'hashlib',
            'logging', 'urllib', 'http', 'socket', 'threading', 'subprocess',
            'tempfile', 'shutil', 'glob', 'inspect', 'importlib', 'abc',
            'enum', 'dataclasses', 'contextlib', 'io', 'csv', 'xml', 'html',
            'unittest', 'asyncio', 'queue', 'time', 'uuid', 'copy', 'pickle',
        }
        third_party = {
            'fastapi', 'flask', 'django', 'pydantic', 'sqlalchemy', 'requests',
            'httpx', 'numpy', 'pandas', 'pytest', 'jinja2', 'loguru', 'dotenv',
            'rich', 'click', 'typer', 'uvicorn', 'starlette', 'ollama', 'openai',
            'anthropic',
        }
        return first in stdlib or first in third_party

    # ── STATS ──

    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval pipeline statistics."""
        return {
            'max_files': self._max_files,
            'max_symbols': self._max_symbols,
            'token_budget': self._token_budget,
        }
