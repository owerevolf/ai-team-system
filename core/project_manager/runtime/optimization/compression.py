"""
Context Compression Engine — deterministic context optimization.

Techniques:
- Duplicate elimination (identical file blocks)
- Symbol collapsing (group related symbols)
- Stale context removal (outdated information)
- Repetitive import compression (deduplicate imports)
- Dependency summarization (summarize deep dependency chains)

NO AI-generated compression summaries. Only deterministic compression.
"""

import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict


class ContextCompressionEngine:
    """
    Compresses context deterministically to reduce token usage.

    Techniques:
    1. Duplicate block elimination
    2. Symbol collapsing (group by type/prefix)
    3. Import deduplication
    4. Stale context detection
    5. Dependency chain summarization
    """

    def __init__(self):
        self._compression_stats = {
            'original_chars': 0,
            'compressed_chars': 0,
            'duplicates_removed': 0,
            'imports_deduped': 0,
            'symbols_collapsed': 0,
        }

    def compress(self, context: str) -> Tuple[str, Dict[str, Any]]:
        """
        Compress context using deterministic techniques.

        Returns:
            Tuple of (compressed_context, stats)
        """
        self._compression_stats = {
            'original_chars': len(context),
            'compressed_chars': 0,
            'duplicates_removed': 0,
            'imports_deduped': 0,
            'symbols_collapsed': 0,
        }

        # Split into blocks (file sections)
        blocks = self._split_into_blocks(context)

        # 1. Deduplicate blocks
        unique_blocks, dupes = self._deduplicate_blocks(blocks)
        self._compression_stats['duplicates_removed'] = dupes

        # 2. Compress imports within blocks
        compressed_blocks, imports_deduped = self._compress_imports(unique_blocks)
        self._compression_stats['imports_deduped'] = imports_deduped

        # 3. Collapse symbols
        final_blocks, syms_collapsed = self._collapse_symbols(compressed_blocks)
        self._compression_stats['symbols_collapsed'] = syms_collapsed

        result = ''.join(final_blocks)
        self._compression_stats['compressed_chars'] = len(result)

        stats = self._compression_stats.copy()
        stats['compression_ratio'] = (
            round(len(result) / max(stats['original_chars'], 1), 3)
        )
        stats['chars_saved'] = stats['original_chars'] - stats['compressed_chars']

        return result, stats

    def _split_into_blocks(self, context: str) -> List[str]:
        """Split context into file blocks (### file_path ... ### or end)."""
        blocks = []
        current_block = []

        for line in context.split('\n'):
            if line.startswith('### ') and current_block:
                blocks.append('\n'.join(current_block))
                current_block = [line]
            else:
                current_block.append(line)

        if current_block:
            blocks.append('\n'.join(current_block))

        return blocks

    def _deduplicate_blocks(self, blocks: List[str]) -> Tuple[List[str], int]:
        """Remove duplicate blocks based on content hash."""
        seen: Set[str] = set()
        unique: List[str] = []
        dupes = 0

        for block in blocks:
            # Hash the content (excluding the header)
            content = '\n'.join(block.split('\n')[1:])  # Skip ### header
            block_hash = hashlib.md5(content.encode()).hexdigest()[:16]

            if block_hash in seen:
                dupes += 1
            else:
                seen.add(block_hash)
                unique.append(block)

        return unique, dupes

    def _compress_imports(self, blocks: List[str]) -> Tuple[List[str], int]:
        """Deduplicate imports across blocks."""
        seen_imports: Set[str] = set()
        compressed: List[str] = []
        deduped = 0

        for block in blocks:
            lines = block.split('\n')
            new_lines = []

            for line in lines:
                if line.startswith('imports: '):
                    imports_str = line[len('imports: '):]
                    imports = [i.strip() for i in imports_str.split(',')]

                    new_imports = []
                    for imp in imports:
                        if imp not in seen_imports:
                            seen_imports.add(imp)
                            new_imports.append(imp)
                        else:
                            deduped += 1

                    if new_imports:
                        new_lines.append(f"imports: {', '.join(new_imports)}")
                    # Skip empty import lines
                else:
                    new_lines.append(line)

            compressed.append('\n'.join(new_lines))

        return compressed, deduped

    def _collapse_symbols(self, blocks: List[str]) -> Tuple[List[str], int]:
        """Collapse symbol lists by grouping related symbols."""
        collapsed: List[str] = []
        total_collapsed = 0

        for block in blocks:
            lines = block.split('\n')
            new_lines = []

            for line in lines:
                if line.startswith('symbols: ') and ',' in line:
                    symbols_str = line[len('symbols: '):]
                    symbols = [s.strip() for s in symbols_str.split(',')]

                    if len(symbols) > 8:
                        # Group by prefix (e.g., "get_", "set_", "handle_")
                        groups = self._group_symbols(symbols)
                        if len(groups) < len(symbols):
                            collapsed_syms = []
                            for prefix, members in groups.items():
                                if len(members) > 1:
                                    collapsed_syms.append(f"{prefix}[{len(members)}]")
                                    total_collapsed += len(members) - 1
                                else:
                                    collapsed_syms.append(members[0])

                            new_lines.append(f"symbols: {', '.join(collapsed_syms[:10])}")
                            continue

                    new_lines.append(line)
                else:
                    new_lines.append(line)

            collapsed.append('\n'.join(new_lines))

        return collapsed, total_collapsed

    def _group_symbols(self, symbols: List[str]) -> Dict[str, List[str]]:
        """Group symbols by common prefix."""
        groups: Dict[str, List[str]] = defaultdict(list)

        for sym in symbols:
            # Extract prefix (e.g., "get_" from "get_user")
            parts = sym.split('_')
            if len(parts) > 1:
                prefix = parts[0] + '_'
                groups[prefix].append(sym)
            else:
                groups['_other'].append(sym)

        return dict(groups)

    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        return self._compression_stats.copy()
