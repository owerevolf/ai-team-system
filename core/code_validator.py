"""
Code Validator - Проверяет сгенерированный код
"""

import subprocess
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationResult:
    file: str
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CodeValidator:
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def validate_all(self, files: List[str]) -> List[ValidationResult]:
        """Валидация всех файлов"""
        results = []
        
        for file_path in files:
            full_path = self.project_path / file_path
            
            if not full_path.exists():
                results.append(ValidationResult(
                    file=file_path,
                    valid=False,
                    errors=["File not found"]
                ))
                continue
            
            result = self.validate_file(full_path, file_path)
            results.append(result)
        
        return results
    
    def validate_file(self, full_path: Path, relative_path: str) -> ValidationResult:
        """Валидация одного файла"""
        ext = full_path.suffix.lower()
        
        if ext == ".py":
            return self._validate_python(full_path, relative_path)
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            return self._validate_javascript(full_path, relative_path)
        elif ext in [".html"]:
            return self._validate_html(full_path, relative_path)
        elif ext in [".json"]:
            return self._validate_json(full_path, relative_path)
        elif ext in [".yaml", ".yml"]:
            return self._validate_yaml(full_path, relative_path)
        else:
            return ValidationResult(file=relative_path, valid=True)
    
    def _validate_python(self, path: Path, relative: str) -> ValidationResult:
        """Проверка Python синтаксиса"""
        errors = []
        warnings = []
        
        try:
            compile(path.read_text(), str(path), 'exec')
        except SyntaxError as e:
            errors.append(f"SyntaxError: line {e.lineno}: {e.msg}")
        
        content = path.read_text()
        
        if "import" not in content and "def " not in content and "class " not in content:
            if len(content) > 50:
                warnings.append("No imports or functions found")
        
        if "print(" in content and "test" not in str(path).lower():
            warnings.append("Contains print statements")
        
        return ValidationResult(
            file=relative,
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_javascript(self, path: Path, relative: str) -> ValidationResult:
        """Базовая проверка JS"""
        errors = []
        content = path.read_text()
        
        open_braces = content.count('{')
        close_braces = content.count('}')
        
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {{ = {open_braces}, }} = {close_braces}")
        
        return ValidationResult(file=relative, valid=len(errors) == 0, errors=errors)
    
    def _validate_html(self, path: Path, relative: str) -> ValidationResult:
        errors = []
        content = path.read_text()
        
        if '<html' in content and '</html>' not in content:
            errors.append("Missing </html> tag")
        
        if '<body' in content and '</body>' not in content:
            errors.append("Missing </body> tag")
        
        return ValidationResult(file=relative, valid=len(errors) == 0, errors=errors)
    
    def _validate_json(self, path: Path, relative: str) -> ValidationResult:
        import json
        try:
            json.loads(path.read_text())
            return ValidationResult(file=relative, valid=True)
        except json.JSONDecodeError as e:
            return ValidationResult(
                file=relative,
                valid=False,
                errors=[f"JSON error: line {e.lineno}: {e.msg}"]
            )
    
    def _validate_yaml(self, path: Path, relative: str) -> ValidationResult:
        try:
            import yaml
            yaml.safe_load(path.read_text())
            return ValidationResult(file=relative, valid=True)
        except yaml.YAMLError as e:
            return ValidationResult(
                file=relative,
                valid=False,
                errors=[f"YAML error: {e}"]
            )
    
    def run_pytest(self) -> Dict[str, Any]:
        """Запуск pytest"""
        tests_dir = self.project_path / "tests"
        if not tests_dir.exists():
            return {"success": True, "message": "No tests directory"}
        
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:3000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Tests timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        total = len(results)
        valid = sum(1 for r in results if r.valid)
        errors = sum(len(r.errors) for r in results)
        warnings = sum(len(r.warnings) for r in results)
        
        return {
            "total_files": total,
            "valid_files": valid,
            "invalid_files": total - valid,
            "total_errors": errors,
            "total_warnings": warnings,
            "all_valid": valid == total
        }
