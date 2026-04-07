"""
Agent Sandbox - Безопасное выполнение кода агентов
"""

import ast
import builtins
import re
from typing import List, Set, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SandboxResult:
    safe: bool
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class CodeSandbox:
    """Статический анализ кода перед выполнением"""
    
    DANGEROUS_FUNCTIONS = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'input', 'breakpoint', 'getattr', 'setattr', 'delattr',
        'globals', 'locals', 'vars', 'dir'
    }
    
    DANGEROUS_MODULES = {
        'os', 'subprocess', 'shutil', 'sys', 'ctypes',
        'pickle', 'marshal', 'socket', 'http', 'urllib',
        'ftplib', 'smtplib', 'telnetlib'
    }
    
    DANGEROUS_PATTERNS = [
        r'os\.system\s*\(',
        r'subprocess\.',
        r'__import__\s*\(',
        r'eval\s*\(',
        r'exec\s*\(',
        r'shutil\.',
        r'rm\s+-rf',
        r'drop\s+table',
        r'delete\s+from',
    ]
    
    def check_code(self, code: str, language: str = "python") -> SandboxResult:
        """Проверка кода на безопасность"""
        issues = []
        
        if language == "python":
            issues.extend(self._check_python(code))
        elif language in ["javascript", "typescript"]:
            issues.extend(self._check_javascript(code))
        
        return SandboxResult(
            safe=len(issues) == 0,
            issues=issues
        )
    
    def _check_python(self, code: str) -> List[str]:
        """Проверка Python кода"""
        issues = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                issues.append(f"Dangerous pattern: {pattern}")
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.DANGEROUS_FUNCTIONS:
                            issues.append(f"Dangerous function: {node.func.id}")
                    elif isinstance(node.func, ast.Attribute):
                        if node.func.attr in self.DANGEROUS_FUNCTIONS:
                            issues.append(f"Dangerous method: {node.func.attr}")
                
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.DANGEROUS_MODULES:
                            issues.append(f"Dangerous module: {alias.name}")
                
                if isinstance(node, ast.ImportFrom):
                    if node.module in self.DANGEROUS_MODULES:
                        issues.append(f"Dangerous module: {node.module}")
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        
        return issues
    
    def _check_javascript(self, code: str) -> List[str]:
        """Проверка JS кода"""
        issues = []
        
        js_patterns = [
            (r'eval\s*\(', 'eval() usage'),
            (r'document\.write\s*\(', 'document.write()'),
            (r'innerHTML\s*=', 'innerHTML assignment'),
            (r'new\s+Function\s*\(', 'Function constructor'),
            (r'process\.exec\s*\(', 'process.exec()'),
            (r'require\s*\(\s*["\']child_process["\']', 'child_process'),
        ]
        
        for pattern, desc in js_patterns:
            if re.search(pattern, code):
                issues.append(f"Dangerous pattern: {desc}")
        
        return issues
    
    def sanitize_code(self, code: str, language: str = "python") -> str:
        """Очистка кода от опасных конструкций"""
        if language == "python":
            return self._sanitize_python(code)
        return code
    
    def _sanitize_python(self, code: str) -> str:
        """Очистка Python кода"""
        lines = code.split('\n')
        safe_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') or not stripped:
                safe_lines.append(line)
                continue
            
            is_safe = True
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, line):
                    safe_lines.append(f"# [SANDBOX BLOCKED] {line}")
                    is_safe = False
                    break
            
            if is_safe:
                safe_lines.append(line)
        
        return '\n'.join(safe_lines)
