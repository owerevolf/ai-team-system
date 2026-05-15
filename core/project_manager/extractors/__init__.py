"""
Symbol Extractor — extracts classes, functions, imports from code.

Three-tier extraction:
1. AST parser (Python via built-in ast module) — most accurate
2. Regex parser (all supported languages) — fallback
3. Safe skip — if both fail, returns empty list, never crashes.

Also extracts: decorators, inheritance, async functions, routes/endpoints.
"""

import ast
import re
from typing import List, Tuple, Optional, Dict

from core.project_manager.models import SymbolEntry


# ─── Language-specific regex patterns (fallback) ───

PATTERNS = {
    'python': {
        'class': re.compile(r'^class\s+(\w+)', re.MULTILINE),
        'function': re.compile(r'^(?:async\s+)?def\s+(\w+)', re.MULTILINE),
        'import': re.compile(r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', re.MULTILINE),
        'decorator': re.compile(r'^\s*@(\w+(?:\.\w+)*)', re.MULTILINE),
    },
    'javascript': {
        'class': re.compile(r'^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)', re.MULTILINE),
        'function': re.compile(
            r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)|'
            r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)',
            re.MULTILINE
        ),
        'import': re.compile(
            r'^import\s+.*?from\s+[\'\"](.+?)[\'\"]|^import\s+[\'\"](.+?)[\'\"]',
            re.MULTILINE
        ),
        'export': re.compile(
            r'^export\s+(?:default\s+)?(?:class|function|const|let|var)?\s*(\w+)',
            re.MULTILINE
        ),
        'method': re.compile(
            r'^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{',
            re.MULTILINE
        ),
        'route': re.compile(
            r'\.(?:get|post|put|delete|patch|options|head|use)\s*\(\s*[\'\"](/[^\'\"]*)[\'\"]',
            re.MULTILINE
        ),
    },
    'typescript': {
        'class': re.compile(r'^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)', re.MULTILINE),
        'interface': re.compile(r'^\s*(?:export\s+)?interface\s+(\w+)', re.MULTILINE),
        'function': re.compile(
            r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)|'
            r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)',
            re.MULTILINE
        ),
        'import': re.compile(
            r'^import\s+.*?from\s+[\'\"](.+?)[\'\"]|^import\s+[\'\"](.+?)[\'\"]',
            re.MULTILINE
        ),
        'export': re.compile(
            r'^export\s+(?:default\s+)?(?:class|function|interface|const|let|var|type)?\s*(\w+)',
            re.MULTILINE
        ),
        'method': re.compile(
            r'^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*[:;]',
            re.MULTILINE
        ),
        'route': re.compile(
            r'\.(?:get|post|put|delete|patch|options|head|use)\s*\(\s*[\'\"](/[^\'\"]*)[\'\"]',
            re.MULTILINE
        ),
    },
    'go': {
        'function': re.compile(r'^func\s+(?:\([^)]*\)\s+)?(\w+)', re.MULTILINE),
        'struct': re.compile(r'^type\s+(\w+)\s+struct', re.MULTILINE),
        'interface': re.compile(r'^type\s+(\w+)\s+interface', re.MULTILINE),
        'import': re.compile(r'^import\s+[\'\"](.+?)[\'\"]', re.MULTILINE),
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
    """
    Extracts symbols from source code.

    Strategy:
    - Python: use ast module (accurate, gets decorators, inheritance, async)
    - Other languages: use regex patterns
    - On any error: return empty list, never crash
    """

    def extract_symbols(self, content: str, language: str) -> List[SymbolEntry]:
        """
        Extract symbols from file content.

        Returns empty list on any error — never crashes.
        """
        try:
            if language == 'python':
                return self._extract_python_ast(content)
            return self._extract_regex(content, language)
        except Exception:
            return []

    def _extract_python_ast(self, content: str) -> List[SymbolEntry]:
        """
        Extract Python symbols using the built-in ast module.

        Gets: classes (with bases), functions (with decorators, async),
        methods inside classes, top-level assignments.
        """
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fallback to regex if AST parse fails
            return self._extract_regex(content, 'python')

        symbols: List[SymbolEntry] = []
        lines = content.split('\n')

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                # Class definition
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(ast.unparse(base) if hasattr(ast, 'unparse') else base.attr)

                sig = f"class {node.name}"
                if bases:
                    sig += f"({', '.join(bases)})"

                symbols.append(SymbolEntry(
                    name=node.name,
                    type='class',
                    file_path='',
                    line=node.lineno,
                    signature=sig[:100],
                    decorators=[
                        ast.unparse(d) if hasattr(ast, 'unparse') else self._decorator_str(d)
                        for d in node.decorator_list
                    ],
                ))

                # Methods inside class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_sig = f"def {item.name}"
                        if item.args.args:
                            params = [a.arg for a in item.args.args]
                            method_sig += f"({', '.join(params[:3])}{'...' if len(params) > 3 else ''})"

                        symbols.append(SymbolEntry(
                            name=item.name,
                            type='method',
                            file_path='',
                            line=item.lineno,
                            signature=method_sig[:100],
                            decorators=[
                                ast.unparse(d) if hasattr(ast, 'unparse') else self._decorator_str(d)
                                for d in item.decorator_list
                            ],
                            parent=node.name,
                            is_async=isinstance(item, ast.AsyncFunctionDef),
                        ))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Top-level function
                sig = f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}"
                if node.args.args:
                    params = [a.arg for a in node.args.args]
                    sig += f"({', '.join(params[:3])}{'...' if len(params) > 3 else ''})"

                symbols.append(SymbolEntry(
                    name=node.name,
                    type='function',
                    file_path='',
                    line=node.lineno,
                    signature=sig[:100],
                    decorators=[
                        ast.unparse(d) if hasattr(ast, 'unparse') else self._decorator_str(d)
                        for d in node.decorator_list
                    ],
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                ))

            elif isinstance(node, ast.Assign):
                # Top-level assignments (constants, configs)
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        symbols.append(SymbolEntry(
                            name=target.id,
                            type='variable',
                            file_path='',
                            line=target.lineno,
                            signature=lines[target.lineno - 1].strip()[:100] if target.lineno <= len(lines) else '',
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

    def _decorator_str(self, node) -> str:
        """Convert AST decorator node to string (fallback for Python < 3.8)."""
        if isinstance(node, ast.Name):
            return f"@{node.id}"
        elif isinstance(node, ast.Attribute):
            return f"@{node.attr}"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"@{node.func.id}(...)"
            elif isinstance(node.func, ast.Attribute):
                return f"@{node.func.attr}(...)"
        return "@..."

    def _extract_regex(self, content: str, language: str) -> List[SymbolEntry]:
        """Extract symbols using regex patterns (fallback for non-Python)."""
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
                        file_path='',
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

    def extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import paths from file content."""
        try:
            if language == 'python':
                return self._extract_python_imports(content)

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

    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract Python imports using AST."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._extract_regex_imports(content, 'python')

        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if module:
                    imports.append(module)
                    # Also add specific imports
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")

        return imports

    def _extract_regex_imports(self, content: str, language: str) -> List[str]:
        """Fallback regex import extraction."""
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

    def extract_routes(self, content: str, language: str) -> List[Dict]:
        """
        Extract route/endpoint definitions.
        Returns list of {method, path, line}.
        """
        routes = []
        try:
            patterns = PATTERNS.get(language, {})
            route_pattern = patterns.get('route')
            if not route_pattern:
                return routes

            http_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']

            for match in route_pattern.finditer(content):
                path = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                # Try to determine HTTP method from context
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_content = content[line_start:match.start() + 50]
                method = 'ANY'
                for m in http_methods:
                    if f'.{m.lower()}' in line_content.lower():
                        method = m
                        break

                routes.append({
                    'method': method,
                    'path': path,
                    'line': line_num,
                })
        except Exception:
            pass

        return routes
