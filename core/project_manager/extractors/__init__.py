"""
Symbol Extractor — extracts classes, functions, imports from code.

Uses regex only. No AST parser. Fault-tolerant.
If parsing fails — returns empty list, never crashes.
"""

import re
from typing import List, Tuple

from core.project_manager.models import SymbolEntry


# Language-specific regex patterns
PATTERNS = {
    'python': {
        'class': re.compile(r'^class\s+(\w+)', re.MULTILINE),
        'function': re.compile(r'^(?:async\s+)?def\s+(\w+)', re.MULTILINE),
        'import': re.compile(r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', re.MULTILINE),
    },
    'javascript': {
        'class': re.compile(r'^class\s+(\w+)', re.MULTILINE),
        'function': re.compile(r'^(?:async\s+)?function\s+(\w+)|^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)', re.MULTILINE),
        'import': re.compile(r'^import\s+.*?from\s+[\'"](.+?)[\'"]|^import\s+[\'"](.+?)[\'"]', re.MULTILINE),
        'export': re.compile(r'^export\s+(?:default\s+)?(?:class|function|const|let|var)?\s*(\w+)', re.MULTILINE),
    },
    'typescript': {
        'class': re.compile(r'^class\s+(\w+)', re.MULTILINE),
        'interface': re.compile(r'^interface\s+(\w+)', re.MULTILINE),
        'function': re.compile(r'^(?:async\s+)?function\s+(\w+)|^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)', re.MULTILINE),
        'import': re.compile(r'^import\s+.*?from\s+[\'"](.+?)[\'"]|^import\s+[\'"](.+?)[\'"]', re.MULTILINE),
        'export': re.compile(r'^export\s+(?:default\s+)?(?:class|function|interface|const|let|var|type)?\s*(\w+)', re.MULTILINE),
    },
    'go': {
        'function': re.compile(r'^func\s+(?:\([^)]*\)\s+)?(\w+)', re.MULTILINE),
        'struct': re.compile(r'^type\s+(\w+)\s+struct', re.MULTILINE),
        'interface': re.compile(r'^type\s+(\w+)\s+interface', re.MULTILINE),
        'import': re.compile(r'^import\s+[\'"](.+?)[\'"]', re.MULTILINE),
    },
    'rust': {
        'function': re.compile(r'^(?:pub\s+)?fn\s+(\w+)', re.MULTILINE),
        'struct': re.compile(r'^(?:pub\s+)?struct\s+(\w+)', re.MULTILINE),
        'trait': re.compile(r'^(?:pub\s+)?trait\s+(\w+)', re.MULTILINE),
        'impl': re.compile(r'^impl\s+(?:<[^>]+>\s+)?(\w+)', re.MULTILINE),
    },
    'java': {
        'class': re.compile(r'^(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?class\s+(\w+)', re.MULTILINE),
        'interface': re.compile(r'^(?:public\s+|private\s+|protected\s+)?interface\s+(\w+)', re.MULTILINE),
        'method': re.compile(r'^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:[\w<>\[\]]+)\s+(\w+)\s*\(', re.MULTILINE),
        'import': re.compile(r'^import\s+([\w.]+)', re.MULTILINE),
    },
    'php': {
        'class': re.compile(r'^class\s+(\w+)', re.MULTILINE),
        'function': re.compile(r'^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?function\s+(\w+)', re.MULTILINE),
    },
}


class SymbolExtractor:
    """Extracts symbols from source code using regex. Fault-tolerant."""

    def extract_symbols(self, content: str, language: str) -> List[SymbolEntry]:
        """
        Extract symbols from file content.

        Returns empty list on any error — never crashes.
        """
        try:
            patterns = PATTERNS.get(language)
            if not patterns:
                return self._fallback_extract(content)

            symbols = []
            for sym_type, pattern in patterns.items():
                if sym_type in ('import', 'export'):
                    continue
                for match in pattern.finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    name = next((g for g in match.groups() if g), '')
                    if name:
                        symbols.append(SymbolEntry(
                            name=name,
                            type=sym_type,
                            file_path='',  # filled by caller
                            line=line_num,
                            signature=match.group(0).strip()[:100],
                        ))

            # Deduplicate
            seen = set()
            unique = []
            for s in symbols:
                key = (s.name, s.line)
                if key not in seen:
                    seen.add(key)
                    unique.append(s)

            return unique

        except Exception:
            return []

    def extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import paths from file content."""
        try:
            patterns = PATTERNS.get(language, {})
            import_pattern = patterns.get('import')
            if not import_pattern:
                return []

            imports = []
            for match in import_pattern.finditer(content):
                path = next((g for g in match.groups() if g), '')
                if path:
                    imports.append(path)
            return imports

        except Exception:
            return []

    def extract_exports(self, content: str, language: str) -> List[str]:
        """Extract exported symbol names."""
        try:
            patterns = PATTERNS.get(language, {})
            export_pattern = patterns.get('export')
            if not export_pattern:
                return []

            exports = []
            for match in export_pattern.finditer(content):
                name = next((g for g in match.groups() if g), '')
                if name:
                    exports.append(name)
            return exports

        except Exception:
            return []

    def _fallback_extract(self, content: str) -> List[SymbolEntry]:
        """Generic fallback for unsupported languages."""
        symbols = []
        try:
            generic = {
                'class': re.compile(r'^class\s+(\w+)', re.MULTILINE),
                'function': re.compile(r'^(?:function|def|fn|func)\s+(\w+)', re.MULTILINE),
            }
            for sym_type, pattern in generic.items():
                for match in pattern.finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    symbols.append(SymbolEntry(
                        name=match.group(1),
                        type=sym_type,
                        file_path='',
                        line=line_num,
                        signature=match.group(0).strip()[:100],
                    ))
        except Exception:
            pass
        return symbols
