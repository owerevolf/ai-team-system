"""
SymbolExtractor — Extracts classes, functions, methods from code.

Uses regex (no AST parser needed). Fast and works for any language.
"""

import re
from typing import List, Dict, Any
from loguru import logger


class SymbolExtractor:
    """
    Extracts symbols from source code using regex patterns.

    Supports: Python, JavaScript, TypeScript, Go, Rust, Java, etc.
    """

    # Language-specific patterns
    PATTERNS = {
        "python": {
            "class": re.compile(r'^class\s+(\w+)\s*(?:\(([^)]*)\))?', re.MULTILINE),
            "function": re.compile(r'^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE),
            "variable": re.compile(r'^(\w+)\s*=\s*(?!\s*[=])', re.MULTILINE),
            "constant": re.compile(r'^([A-Z_][A-Z0-9_]*)\s*=', re.MULTILINE),
        },
        "javascript": {
            "class": re.compile(r'^class\s+(\w+)', re.MULTILINE),
            "function": re.compile(r'^(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function\s*\(|\([^)]*\)\s*=>))', re.MULTILINE),
            "method": re.compile(r'^(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE),
            "variable": re.compile(r'^(?:const|let|var)\s+(\w+)\s*=', re.MULTILINE),
        },
        "typescript": {
            "class": re.compile(r'^class\s+(\w+)', re.MULTILINE),
            "interface": re.compile(r'^interface\s+(\w+)', re.MULTILINE),
            "function": re.compile(r'^(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function\s*\(|\([^)]*\)\s*=>))', re.MULTILINE),
            "method": re.compile(r'^(\w+)\s*\([^)]*\)\s*[:\{]', re.MULTILINE),
            "variable": re.compile(r'^(?:const|let|var)\s+(\w+)\s*:', re.MULTILINE),
        },
        "go": {
            "function": re.compile(r'^func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', re.MULTILINE),
            "struct": re.compile(r'^type\s+(\w+)\s+struct', re.MULTILINE),
            "interface": re.compile(r'^type\s+(\w+)\s+interface', re.MULTILINE),
        },
        "rust": {
            "function": re.compile(r'^(?:pub\s+)?fn\s+(\w+)\s*\(', re.MULTILINE),
            "struct": re.compile(r'^(?:pub\s+)?struct\s+(\w+)', re.MULTILINE),
            "trait": re.compile(r'^(?:pub\s+)?trait\s+(\w+)', re.MULTILINE),
            "impl": re.compile(r'^impl\s+(?:<[^>]+>\s+)?(\w+)', re.MULTILINE),
        },
        "java": {
            "class": re.compile(r'^(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?class\s+(\w+)', re.MULTILINE),
            "interface": re.compile(r'^(?:public\s+|private\s+|protected\s+)?interface\s+(\w+)', re.MULTILINE),
            "method": re.compile(r'^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:\w+<[^>]+>|\w+)\s+(\w+)\s*\(', re.MULTILINE),
        },
        "php": {
            "class": re.compile(r'^class\s+(\w+)', re.MULTILINE),
            "function": re.compile(r'^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?function\s+(\w+)', re.MULTILINE),
        },
    }

    def extract(self, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract symbols from file content.

        Args:
            content: File content as string
            language: Programming language

        Returns:
            List of symbol dicts: {"name", "type", "line", "signature", "docstring"}
        """
        symbols = []
        patterns = self.PATTERNS.get(language, {})

        if not patterns:
            # Fallback: try to find anything that looks like a function/class
            patterns = {
                "function": re.compile(r'^(?:function|def|fn|func)\s+(\w+)', re.MULTILINE),
                "class": re.compile(r'^class\s+(\w+)', re.MULTILINE),
            }

        lines = content.split('\n')

        for sym_type, pattern in patterns.items():
            for match in pattern.finditer(content):
                # Find line number
                line_num = content[:match.start()].count('\n') + 1

                # Get name (first non-empty group)
                name = next((g for g in match.groups() if g), match.group(0))

                # Build signature
                signature = match.group(0).strip()[:100]

                # Try to get docstring (next non-empty line after definition)
                docstring = self._extract_docstring(lines, line_num, language)

                symbols.append({
                    "name": name,
                    "type": sym_type,
                    "line": line_num,
                    "signature": signature,
                    "docstring": docstring,
                })

        # Sort by line number
        symbols.sort(key=lambda x: x["line"])

        # Remove duplicates (same name, same line)
        seen = set()
        unique = []
        for s in symbols:
            key = (s["name"], s["line"])
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique

    def _extract_docstring(self, lines: List[str], definition_line: int, language: str) -> str:
        """Extract docstring/comment after definition."""
        if definition_line >= len(lines):
            return ""

        # Look at next few lines
        for i in range(definition_line, min(definition_line + 5, len(lines))):
            line = lines[i].strip()

            if not line:
                continue

            # Python docstrings (check for triple quotes)
            if language == "python":
                if line.startswith(chr(34)*3) or line.startswith(chr(39)*3):
                    return line[:100]
                if line.startswith('#'):
                    return line[1:].strip()[:100]

            # JS/TS JSDoc
            if language in ("javascript", "typescript"):
                if line.startswith('/**') or line.startswith('/*'):
                    return line[:100]
                if line.startswith('//'):
                    return line[2:].strip()[:100]

            # Go comments
            if language == "go":
                if line.startswith('//'):
                    return line[2:].strip()[:100]

            # Rust comments
            if language == "rust":
                if line.startswith('///') or line.startswith('//!'):
                    return line[3:].strip()[:100]
                if line.startswith('//'):
                    return line[2:].strip()[:100]

            # Java/PHP comments
            if language in ("java", "php"):
                if line.startswith('/**') or line.startswith('/*'):
                    return line[:100]
                if line.startswith('//'):
                    return line[2:].strip()[:100]

            # If we hit code (not comment), stop
            if line and not line.startswith('#') and not line.startswith('//'):
                break

        return ""
