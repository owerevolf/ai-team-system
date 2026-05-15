"""
ContextCompressor — Compresses project context to fit token limits.

Strategies:
1. Remove redundant whitespace
2. Truncate long lines
3. Summarize large files (keep first/last N lines)
4. Remove comments (optional)
5. Priority-based: important files first
"""

import re
from typing import Optional
from loguru import logger


class ContextCompressor:
    """
    Compresses text to fit within token limits.

    Approximation: 1 token ~ 4 characters for English/code.
    """

    def __init__(self, chars_per_token: int = 4):
        self.chars_per_token = chars_per_token

    def compress(self, text: str, max_chars: int) -> str:
        """
        Compress text to fit within max_chars.

        Args:
            text: Full context text
            max_chars: Maximum characters allowed

        Returns:
            Compressed text
        """
        if len(text) <= max_chars:
            return text

        # Strategy 1: Remove excessive whitespace
        compressed = self._remove_excess_whitespace(text)
        if len(compressed) <= max_chars:
            return compressed

        # Strategy 2: Truncate long lines
        compressed = self._truncate_long_lines(compressed, max_line_length=120)
        if len(compressed) <= max_chars:
            return compressed

        # Strategy 3: Remove comments
        compressed = self._remove_comments(compressed)
        if len(compressed) <= max_chars:
            return compressed

        # Strategy 4: Progressive truncation
        compressed = self._progressive_truncate(compressed, max_chars)

        logger.info(f"Compressed context: {len(text)} -> {len(compressed)} chars")
        return compressed

    def _remove_excess_whitespace(self, text: str) -> str:
        """Remove excessive blank lines and trailing whitespace."""
        lines = text.split('\n')
        cleaned = []
        prev_blank = False

        for line in lines:
            stripped = line.rstrip()
            if stripped == '':
                if not prev_blank:
                    cleaned.append('')
                    prev_blank = True
            else:
                cleaned.append(stripped)
                prev_blank = False

        return '\n'.join(cleaned)

    def _truncate_long_lines(self, text: str, max_line_length: int = 120) -> str:
        """Truncate very long lines."""
        lines = text.split('\n')
        truncated = []

        for line in lines:
            if len(line) > max_line_length:
                truncated.append(line[:max_line_length] + ' ...')
            else:
                truncated.append(line)

        return '\n'.join(truncated)

    def _remove_comments(self, text: str) -> str:
        """Remove code comments (basic regex)."""
        # Remove // comments
        text = re.sub(r'\s*//.*$', '', text, flags=re.MULTILINE)
        # Remove # comments (but not shebang)
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            if line.startswith('#!'):
                cleaned.append(line)
            else:
                cleaned.append(re.sub(r'\s*#.*$', '', line))
        text = '\n'.join(cleaned)
        # Remove /* */ comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        # Remove docstrings (simplified) - use chr() to avoid quote issues
        dq = chr(34)*3
        sq = chr(39)*3
        text = re.sub(dq + r'.*?' + dq, dq + '...' + dq, text, flags=re.DOTALL)
        text = re.sub(sq + r'.*?' + sq, sq + '...' + sq, text, flags=re.DOTALL)

        return self._remove_excess_whitespace(text)

    def _progressive_truncate(self, text: str, max_chars: int) -> str:
        """
        Progressive truncation: keep structure, reduce content.

        Priority:
        1. Keep headers and structure
        2. Keep first 30 lines of each file section
        3. Keep last 10 lines of each file section
        4. Replace middle with "... (N lines omitted) ..."
        """
        lines = text.split('\n')

        if len(''.join(lines)) <= max_chars:
            return text

        # Identify file sections (marked by ## FILE: or similar)
        sections = []
        current = []

        for line in lines:
            if line.startswith('## FILE:') or line.startswith('## ') and 'FILE' in line:
                if current:
                    sections.append(current)
                current = [line]
            else:
                current.append(line)

        if current:
            sections.append(current)

        if not sections:
            # No file sections, just truncate from end
            result = []
            current_len = 0
            for line in lines:
                if current_len + len(line) + 1 > max_chars:
                    result.append(f"... ({len(lines) - len(result)} lines omitted) ...")
                    break
                result.append(line)
                current_len += len(line) + 1
            return '\n'.join(result)

        # Compress each section
        compressed_sections = []
        for section in sections:
            compressed = self._compress_section(section, max_chars // len(sections))
            compressed_sections.append(compressed)

        result = '\n'.join('\n'.join(s) for s in compressed_sections)

        # If still too long, keep only headers
        if len(result) > max_chars:
            headers = []
            for section in sections:
                # Keep only first 5 lines (header) of each section
                headers.extend(section[:5])
                headers.append('...')
            result = '\n'.join(headers)

        return result

    def _compress_section(self, section: list, max_section_chars: int) -> list:
        """Compress a single file section."""
        section_text = '\n'.join(section)

        if len(section_text) <= max_section_chars:
            return section

        # Keep first 20 lines + last 5 lines
        first_n = 20
        last_n = 5

        if len(section) <= first_n + last_n + 1:
            return section

        compressed = section[:first_n]
        omitted = len(section) - first_n - last_n
        compressed.append(f"\n... ({omitted} lines omitted) ...\n")
        compressed.extend(section[-last_n:])

        return compressed

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // self.chars_per_token
