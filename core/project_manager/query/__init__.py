"""
Query API — provides filtered, ranked context from ProjectManager.

Enforces context budget. Returns only relevant facts.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

from core.project_manager.models import FileEntry

# Default context budget: ~3000 tokens ~= 12000 chars
DEFAULT_MAX_CONTEXT_CHARS = 12000
# Minimum chars per file entry in context
MIN_FILE_CONTEXT = 200
# Maximum files per query response
MAX_FILES_PER_QUERY = 8


class QueryEngine:
    """Processes context queries with budget enforcement."""

    def __init__(self, max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS):
        self.max_context_chars = max_context_chars

    def query(
        self,
        files: Dict[str, FileEntry],
        question: str,
        max_chars: Optional[int] = None,
    ) -> str:
        """
        Build a context response for a query.

        Args:
            files: Project file index
            question: What the agent wants to know
            max_chars: Override default budget

        Returns:
            Filtered, compressed context string
        """
        budget = max_chars or self.max_context_chars

        # Rank files by relevance
        ranked = self._rank_files(files, question)

        # Build context within budget
        parts = []
        used_chars = 0
        files_included = 0

        # Always include the most relevant files first
        for rel_path, score in ranked:
            if files_included >= MAX_FILES_PER_QUERY:
                break
            if used_chars >= budget:
                break

            entry = files.get(rel_path)
            if not entry:
                continue

            # Build file context block
            block = self._format_file_block(entry)
            block_len = len(block)

            if used_chars + block_len > budget:
                # Try a truncated version
                remaining = budget - used_chars
                if remaining >= MIN_FILE_CONTEXT:
                    block = self._format_file_block(entry, brief=True)
                    block_len = len(block)
                    if block_len <= remaining:
                        parts.append(block)
                        used_chars += block_len
                        files_included += 1
                break

            parts.append(block)
            used_chars += block_len
            files_included += 1

        # Add summary header
        header = f"## PROJECT CONTEXT ({len(files)} files total, {files_included} shown)\n"
        header += f"## QUERY: {question[:100]}\n\n"

        result = header + ''.join(parts)

        # Final safety trim
        if len(result) > budget:
            result = result[:budget] + "\n... (truncated)"

        return result

    def _rank_files(self, files: Dict[str, FileEntry], question: str) -> List[tuple]:
        """Rank files by relevance to question. Returns [(path, score), ...]."""
        q = question.lower()
        scores: Dict[str, int] = defaultdict(int)

        for rel_path, entry in files.items():
            # Entry points get high priority
            if entry.is_entry_point:
                scores[rel_path] += 20

            # Name match
            name = Path(rel_path).name.lower()
            for word in q.split():
                if len(word) > 2 and word in name:
                    scores[rel_path] += 10

            # Symbol match
            for sym in entry.symbols:
                sym_name = sym.get('name', '').lower()
                for word in q.split():
                    if len(word) > 2 and word in sym_name:
                        scores[rel_path] += 5

            # Import match
            for imp in entry.imports:
                for word in q.split():
                    if len(word) > 2 and word in imp.lower():
                        scores[rel_path] += 3

            # Keyword boosts
            if 'test' in q and entry.is_test:
                scores[rel_path] += 15
            if 'config' in q and entry.is_config:
                scores[rel_path] += 15
            if 'route' in q or 'endpoint' in q or 'api' in q:
                if any(s.get('type') == 'route' for s in entry.symbols):
                    scores[rel_path] += 15
                if 'route' in rel_path.lower() or 'view' in rel_path.lower():
                    scores[rel_path] += 10

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return ranked

    def _format_file_block(self, entry: FileEntry, brief: bool = False) -> str:
        """Format a file entry as a context block."""
        lines = [f"### {entry.path}\n"]
        lines.append(f"lang: {entry.language}, size: {entry.size}b\n")

        if entry.symbols:
            sym_names = [s.get('name', '?') for s in entry.symbols[:15]]
            lines.append(f"symbols: {', '.join(sym_names)}\n")

        if entry.imports and not brief:
            imp_names = entry.imports[:10]
            lines.append(f"imports: {', '.join(imp_names)}\n")

        if entry.exports:
            lines.append(f"exports: {', '.join(entry.exports[:10])}\n")

        lines.append("\n")
        return ''.join(lines)
