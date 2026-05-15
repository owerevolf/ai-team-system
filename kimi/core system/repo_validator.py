"""
RepoValidator — Validates proposed changes before they are applied.

Checks:
1. File existence
2. Duplicate symbols
3. Import integrity
4. Breaking changes
5. Syntax errors (basic)
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger


class RepoValidator:
    """
    Validates proposed code changes.

    Does NOT execute code — only static analysis.
    """

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)

    def validate(self, proposal: str, files: Dict, dependencies: Dict) -> Tuple[bool, str]:
        """
        Validate a proposed change.

        Args:
            proposal: The proposed change (text description or code)
            files: Current file index from ProjectManager
            dependencies: Current dependency graph

        Returns:
            (is_valid, reason)
        """
        checks = []

        # Check 1: Does target file exist?
        file_check = self._check_file_existence(proposal, files)
        if file_check:
            checks.append(file_check)

        # Check 2: Duplicate symbols?
        dup_check = self._check_duplicates(proposal, files)
        if dup_check:
            checks.append(dup_check)

        # Check 3: Import integrity
        import_check = self._check_imports(proposal, files)
        if import_check:
            checks.append(import_check)

        # Check 4: Breaking changes
        breaking_check = self._check_breaking_changes(proposal, files, dependencies)
        if breaking_check:
            checks.append(breaking_check)

        # Check 5: Basic syntax
        syntax_check = self._check_syntax(proposal)
        if syntax_check:
            checks.append(syntax_check)

        if checks:
            return False, "; ".join(checks)

        return True, "OK"

    def _check_file_existence(self, proposal: str, files: Dict) -> Optional[str]:
        """Check if target files exist."""
        # Extract file paths from proposal
        file_patterns = [
            r'(?:modify|edit|change|update|create|add)\s+[\"\']?([\w./]+)[\"\']?',
            r'([\w./]+\.(?:py|js|ts|jsx|tsx|html|css|json|yaml|yml|toml))',
        ]

        mentioned_files = set()
        for pattern in file_patterns:
            for match in re.finditer(pattern, proposal, re.IGNORECASE):
                mentioned_files.add(match.group(1))

        for file_path in mentioned_files:
            # Check if it's a create operation
            if any(word in proposal.lower() for word in ['create', 'add', 'new file']):
                # File should NOT exist for create
                if file_path in files:
                    return f"File already exists: {file_path}"
                continue

            # For modifications, file must exist
            if file_path not in files:
                return f"File not found: {file_path}"

        return None

    def _check_duplicates(self, proposal: str, files: Dict) -> Optional[str]:
        """Check if proposal creates duplicate symbols."""
        # Extract new symbol names from proposal
        new_symbols = []

        # Python: class X, def X
        for match in re.finditer(r'(?:class|def)\s+(\w+)', proposal):
            new_symbols.append((match.group(1), match.group(0).split()[0]))

        # JS/TS: class X, function X, const X
        for match in re.finditer(r'(?:class|function|const|let|var)\s+(\w+)', proposal):
            new_symbols.append((match.group(1), match.group(0).split()[0]))

        # Check against existing files
        for sym_name, sym_type in new_symbols:
            for file_path, entry in files.items():
                for sym in entry.symbols:
                    if sym["name"] == sym_name and sym["type"] == sym_type:
                        return f"Duplicate {sym_type} '{sym_name}' already in {file_path}"

        return None

    def _check_imports(self, proposal: str, files: Dict) -> Optional[str]:
        """Check if proposal uses non-existent imports."""
        # Extract imports from proposal
        imports = []

        # Python imports
        for match in re.finditer(r'(?:from|import)\s+([\w.]+)', proposal):
            imports.append(match.group(1))

        # JS/TS imports
        for match in re.finditer(r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]', proposal):
            imports.append(match.group(1))

        # Check if imports exist in project
        for imp in imports:
            # Skip standard library / external packages
            if self._is_external_import(imp):
                continue

            # Check if any file exports this
            found = False
            for file_path, entry in files.items():
                if imp in entry.exported or imp in file_path:
                    found = True
                    break

            if not found:
                return f"Import '{imp}' not found in project"

        return None

    def _check_breaking_changes(self, proposal: str, files: Dict, dependencies: Dict) -> Optional[str]:
        """Check if proposal breaks existing code."""
        # Check for removed functions/classes
        removed = []

        for match in re.finditer(r'(?:remove|delete)\s+(?:function|def|class|method)?\s*(\w+)', proposal, re.IGNORECASE):
            removed.append(match.group(1))

        for sym_name in removed:
            # Check if anything depends on this symbol
            for file_path, deps in dependencies.items():
                if sym_name in deps:
                    return f"Cannot remove '{sym_name}' — used by {file_path}"

        # Check for signature changes
        for match in re.finditer(r'(?:change|modify)\s+(?:function|def|method)?\s*(\w+)', proposal, re.IGNORECASE):
            sym_name = match.group(1)
            # This is a simplified check — full check would compare signatures
            for file_path, deps in dependencies.items():
                if sym_name in deps:
                    return f"Changing '{sym_name}' may break {file_path}"

        return None

    def _check_syntax(self, proposal: str) -> Optional[str]:
        """Basic syntax check for Python code in proposal."""
        # Extract code blocks
        code_blocks = re.findall(r'```(?:python)?\n(.*?)```', proposal, re.DOTALL)

        if not code_blocks:
            # Try to find indented code
            code_blocks = [proposal]

        for code in code_blocks:
            # Check for obvious syntax errors
            # Unbalanced parentheses
            parens = code.count('(') - code.count(')')
            if parens != 0:
                return f"Unbalanced parentheses: {parens} extra"

            # Unbalanced brackets
            brackets = code.count('[') - code.count(']')
            if brackets != 0:
                return f"Unbalanced brackets: {brackets} extra"

            # Unbalanced braces
            braces = code.count('{') - code.count('}')
            if braces != 0:
                return f"Unbalanced braces: {braces} extra"

            # Check indentation (basic)
            lines = code.split('\n')
            indent_stack = [0]
            for i, line in enumerate(lines, 1):
                if not line.strip() or line.strip().startswith('#'):
                    continue

                indent = len(line) - len(line.lstrip())

                if indent > indent_stack[-1]:
                    # Indentation increased — must be by 4 spaces
                    if indent - indent_stack[-1] != 4:
                        return f"Invalid indentation at line {i}: {indent} spaces (expected {indent_stack[-1] + 4})"
                    indent_stack.append(indent)
                elif indent < indent_stack[-1]:
                    # Indentation decreased
                    while indent_stack and indent < indent_stack[-1]:
                        indent_stack.pop()
                    if indent != indent_stack[-1]:
                        return f"Invalid dedent at line {i}"

        return None

    def _is_external_import(self, import_name: str) -> bool:
        """Check if import is from standard library or external package."""
        # Standard library modules (Python)
        stdlib = {
            'os', 'sys', 'json', 're', 'pathlib', 'typing', 'datetime',
            'collections', 'itertools', 'functools', 'math', 'random',
            'hashlib', 'logging', 'urllib', 'http', 'socket', 'threading',
            'multiprocessing', 'subprocess', 'tempfile', 'shutil', 'glob',
            'inspect', 'importlib', 'pkgutil', 'abc', 'enum', 'dataclasses',
            'contextlib', 'io', 'csv', 'xml', 'html', 'email', 'sqlite3',
            'unittest', 'pytest', 'flask', 'fastapi', 'django', 'requests',
            'numpy', 'pandas', 'matplotlib', 'sklearn', 'tensorflow',
            'torch', 'cv2', 'PIL', 'boto3', 'botocore', 'pydantic',
            'sqlalchemy', 'alembic', 'celery', 'redis', 'kafka',
            'elasticsearch', 'mongoengine', 'pymongo', 'psycopg2',
            'asyncio', 'aiohttp', 'tornado', 'twisted', 'scrapy',
        }

        # Check first part of dotted import
        first_part = import_name.split('.')[0]
        return first_part in stdlib
