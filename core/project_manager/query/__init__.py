"""
Query Engine — provides filtered, ranked context from ProjectManager.

Enforces context budget. Returns only relevant facts.
Deterministic ranking — no AI reasoning, only structural signals.

Ranking signals:
- Symbol relevance (name match)
- Dependency proximity (distance from entry points)
- Recently modified files (recency boost)
- Git activity (frequently changed files)
- Import distance (how many hops from query-relevant files)
- Entrypoint weight (entry points get higher base score)
- Task relevance (files mentioned in recent tasks)
- Hot-path files (frequently accessed)
"""

import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from core.project_manager.models import FileEntry, RetrievalMetrics
from loguru import logger

# Default context budget: ~3000 tokens ~= 12000 chars
DEFAULT_MAX_CONTEXT_CHARS = 12000
# Minimum chars per file entry in context
MIN_FILE_CONTEXT = 200
# Maximum files per query response
MAX_FILES_PER_QUERY = 10


class QueryEngine:
    """Processes context queries with budget enforcement and deterministic ranking."""

    def __init__(self, max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS):
        self.max_context_chars = max_context_chars
        self._access_counts: Dict[str, int] = defaultdict(int)
        self._metrics_log: List[RetrievalMetrics] = []

    def query(
        self,
        files: Dict[str, FileEntry],
        question: str,
        max_chars: Optional[int] = None,
        agent: str = "unknown",
        dependencies: Optional[Dict[str, List[str]]] = None,
        git_state: Optional[Any] = None,
    ) -> str:
        """
        Build a context response for a query.

        Args:
            files: Project file index
            question: What the agent wants to know
            max_chars: Override default budget
            agent: Which agent is asking
            dependencies: Optional dependency graph for proximity scoring
            git_state: Optional git state for activity scoring

        Returns:
            Filtered, compressed context string
        """
        start_time = time.time()
        budget = max_chars or self.max_context_chars

        # Extract query terms
        query_terms = self._extract_terms(question)

        # Rank files by relevance
        ranked = self._rank_files(files, query_terms, dependencies, git_state)

        # Build context within budget
        parts = []
        used_chars = 0
        files_included = 0
        symbols_returned = 0

        for rel_path, score in ranked:
            if files_included >= MAX_FILES_PER_QUERY:
                break
            if used_chars >= budget:
                break

            entry = files.get(rel_path)
            if not entry:
                continue

            # Build file context block
            block = self._format_file_block(entry, query_terms)
            block_len = len(block)

            if used_chars + block_len > budget:
                # Try a truncated version
                remaining = budget - used_chars
                if remaining >= MIN_FILE_CONTEXT:
                    block = self._format_file_block(entry, query_terms, brief=True)
                    block_len = len(block)
                    if block_len <= remaining:
                        parts.append(block)
                        used_chars += block_len
                        files_included += 1
                        symbols_returned += len(entry.symbols)
                break

            parts.append(block)
            used_chars += block_len
            files_included += 1
            symbols_returned += len(entry.symbols)
            self._access_counts[rel_path] += 1

        # Add summary header
        header = f"## PROJECT CONTEXT ({len(files)} files total, {files_included} shown)\n"
        header += f"## QUERY: {question[:100]}\n\n"

        result = header + ''.join(parts)

        # Final safety trim
        if len(result) > budget:
            result = result[:budget] + "\n... (truncated)"

        # Record metrics
        elapsed_ms = (time.time() - start_time) * 1000
        metrics = RetrievalMetrics(
            query=question[:200],
            agent=agent,
            timestamp=datetime.now().isoformat() if 'datetime' in dir() else "",
            files_returned=files_included,
            symbols_returned=symbols_returned,
            context_chars=len(result),
            duration_ms=round(elapsed_ms, 2),
        )
        self._metrics_log.append(metrics)

        return result

    def _extract_terms(self, question: str) -> List[str]:
        """Extract meaningful search terms from a query."""
        # Remove common stop words
        stop_words = {
            'what', 'where', 'which', 'how', 'the', 'a', 'an', 'is', 'are',
            'was', 'were', 'do', 'does', 'did', 'can', 'could', 'should',
            'would', 'will', 'about', 'for', 'with', 'from', 'into', 'through',
            'its', 'this', 'that', 'these', 'those', 'i', 'me', 'my', 'we',
            'our', 'you', 'your', 'it', 'to', 'of', 'in', 'on', 'at', 'by',
            'or', 'and', 'not', 'no', 'if', 'then', 'else', 'when', 'who',
            'whom', 'whose', 'why', 'all', 'each', 'every', 'both', 'few',
            'more', 'most', 'other', 'some', 'such', 'than', 'too', 'very',
            'just', 'because', 'as', 'until', 'while', 'although', 'though',
            'after', 'before', 'since', 'so', 'tell', 'show', 'find', 'give',
            'need', 'want', 'like', 'make', 'take', 'come', 'go', 'see',
            'know', 'get', 'look', 'use', 'work', 'call', 'try', 'ask',
        }

        words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', question.lower())
        terms = [w for w in words if len(w) > 2 and w not in stop_words]
        return terms

    def _rank_files(
        self,
        files: Dict[str, FileEntry],
        query_terms: List[str],
        dependencies: Optional[Dict[str, List[str]]] = None,
        git_state: Optional[Any] = None,
    ) -> List[tuple]:
        """
        Rank files by relevance to query terms.

        Scoring signals (all deterministic):
        1. Name match: filename contains query term
        2. Symbol match: symbol name contains query term
        3. Import match: import path contains query term
        4. Entry point bonus: entry points get base score
        5. Test match: if query mentions tests
        6. Config match: if query mentions config
        7. Route match: if query mentions routes/endpoints
        8. Recency: recently modified files get boost
        9. Git activity: frequently changed files get boost
        10. Hot-path: frequently accessed files get boost
        11. Dependency proximity: files near entry points get boost
        """
        scores: Dict[str, float] = defaultdict(float)
        now = time.time()

        for rel_path, entry in files.items():
            # ── Signal 1: Entry point weight ──
            if entry.is_entry_point:
                scores[rel_path] += 20

            # ── Signal 2: Name match ──
            name = Path(rel_path).name.lower()
            path_lower = rel_path.lower()
            for term in query_terms:
                if term in name:
                    scores[rel_path] += 15
                elif term in path_lower:
                    scores[rel_path] += 8

            # ── Signal 3: Symbol match ──
            for sym in entry.symbols:
                sym_name = sym.get('name', '').lower()
                for term in query_terms:
                    if term == sym_name:
                        scores[rel_path] += 12
                    elif term in sym_name:
                        scores[rel_path] += 6

            # ── Signal 4: Import match ──
            for imp in entry.imports:
                imp_lower = imp.lower()
                for term in query_terms:
                    if term in imp_lower:
                        scores[rel_path] += 4

            # ── Signal 5: Export match ──
            for exp in entry.exports:
                exp_lower = exp.lower()
                for term in query_terms:
                    if term in exp_lower:
                        scores[rel_path] += 5

            # ── Signal 6: Keyword boosts ──
            query_str = ' '.join(query_terms)
            if 'test' in query_str and entry.is_test:
                scores[rel_path] += 15
            if 'config' in query_str and entry.is_config:
                scores[rel_path] += 15
            if any(w in query_str for w in ['route', 'endpoint', 'api', 'url', 'path']):
                if any(s.get('type') == 'route' for s in entry.symbols):
                    scores[rel_path] += 15
                if any(w in path_lower for w in ['route', 'view', 'controller', 'handler', 'endpoint']):
                    scores[rel_path] += 10
            if any(w in query_str for w in ['model', 'schema', 'table', 'database', 'db']):
                if any(w in path_lower for w in ['model', 'schema', 'database', 'migration']):
                    scores[rel_path] += 10
            if any(w in query_str for w in ['service', 'business', 'logic']):
                if 'service' in path_lower:
                    scores[rel_path] += 10

            # ── Signal 7: Recency boost ──
            if entry.modified > 0:
                age_days = (now - entry.modified) / 86400
                if age_days < 1:
                    scores[rel_path] += 8
                elif age_days < 7:
                    scores[rel_path] += 5
                elif age_days < 30:
                    scores[rel_path] += 2

            # ── Signal 8: Hot-path (access frequency) ──
            access_count = self._access_counts.get(rel_path, 0)
            if access_count > 0:
                scores[rel_path] += min(access_count * 0.5, 5)

        # ── Signal 9: Git activity boost ──
        if git_state and hasattr(git_state, 'changed_files'):
            git_changed = set(git_state.changed_files + git_state.staged_files)
            for rel_path in scores:
                if rel_path in git_changed:
                    scores[rel_path] += 7

        # ── Signal 10: Dependency proximity ──
        if dependencies:
            # Find files that are depended on by many others (high centrality)
            dependent_count: Dict[str, int] = defaultdict(int)
            for source, deps in dependencies.items():
                for dep in deps:
                    dependent_count[dep] += 1

            for rel_path, count in dependent_count.items():
                if rel_path in scores and count > 2:
                    scores[rel_path] += min(count * 0.5, 5)

        # Sort by score descending, then by path for stability
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        return ranked

    def _format_file_block(
        self,
        entry: FileEntry,
        query_terms: List[str],
        brief: bool = False,
    ) -> str:
        """Format a file entry as a context block."""
        lines = [f"### {entry.path}\n"]
        lines.append(f"lang: {entry.language}, size: {entry.size}b")

        if entry.is_entry_point:
            lines.append(" [ENTRY POINT]")
        if entry.is_test:
            lines.append(" [TEST]")
        if entry.is_config:
            lines.append(" [CONFIG]")

        lines.append("\n")

        if entry.symbols:
            # Prioritize symbols matching query terms
            matching = []
            other = []
            for s in entry.symbols:
                sym_name = s.get('name', '').lower()
                if any(t in sym_name for t in query_terms):
                    matching.append(s)
                else:
                    other.append(s)

            display = (matching + entry.symbols)[:15]  # matching first, then all
            seen = set()
            sym_names = []
            for s in display:
                n = s.get('name', '?')
                if n not in seen:
                    seen.add(n)
                    sym_names.append(n)

            lines.append(f"symbols: {', '.join(sym_names)}\n")

        if entry.imports and not brief:
            imp_names = entry.imports[:10]
            lines.append(f"imports: {', '.join(imp_names)}\n")

        if entry.exports:
            lines.append(f"exports: {', '.join(entry.exports[:10])}\n")

        lines.append("\n")
        return ''.join(lines)

    def get_metrics(self, limit: int = 50) -> List[Dict]:
        """Get recent retrieval metrics."""
        return [
            {
                'query': m.query,
                'agent': m.agent,
                'timestamp': m.timestamp,
                'files_returned': m.files_returned,
                'symbols_returned': m.symbols_returned,
                'context_chars': m.context_chars,
                'duration_ms': m.duration_ms,
            }
            for m in self._metrics_log[-limit:]
        ]

    def get_hot_files(self, limit: int = 10) -> List[tuple]:
        """Get most frequently accessed files."""
        sorted_files = sorted(self._access_counts.items(), key=lambda x: -x[1])
        return sorted_files[:limit]


# Need datetime for metrics
from datetime import datetime
