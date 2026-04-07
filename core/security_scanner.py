"""
Security Scanner - Проверка кода на уязвимости
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SecurityIssue:
    file: str
    line: int
    severity: str
    message: str
    cwe: Optional[str] = None


class SecurityScanner:
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def scan(self) -> Dict[str, Any]:
        """Полный скан безопасности"""
        results = {
            "python": self._scan_python(),
            "dependencies": self._scan_dependencies(),
            "secrets": self._scan_secrets(),
            "timestamp": datetime.now().isoformat()
        }
        
        total_issues = sum(len(r.get("issues", [])) for r in results.values() if isinstance(r, dict))
        results["total_issues"] = total_issues
        results["passed"] = total_issues == 0
        
        return results
    
    def _scan_python(self) -> Dict[str, Any]:
        """Сканирование Python кода через bandit"""
        src_dir = self.project_path / "src"
        if not src_dir.exists():
            src_dir = self.project_path
        
        try:
            result = subprocess.run(
                ["python", "-m", "bandit", "-r", str(src_dir), "-f", "json", "-ll"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"status": "passed", "issues": []}
            
            data = json.loads(result.stdout)
            issues = []
            for item in data.get("results", []):
                issues.append(SecurityIssue(
                    file=item.get("filename", ""),
                    line=item.get("line_number", 0),
                    severity=item.get("issue_severity", "LOW"),
                    message=item.get("issue_text", ""),
                    cwe=item.get("issue_cwe", {}).get("id")
                ))
            
            return {"status": "failed", "issues": issues}
        except FileNotFoundError:
            return {"status": "skipped", "message": "bandit not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _scan_dependencies(self) -> Dict[str, Any]:
        """Проверка зависимостей на уязвимости"""
        req_file = self.project_path / "requirements.txt"
        if not req_file.exists():
            return {"status": "skipped", "message": "No requirements.txt"}
        
        try:
            result = subprocess.run(
                ["python", "-m", "safety", "check", "-r", str(req_file), "--json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"status": "passed", "issues": []}
            
            return {"status": "failed", "issues": [{"message": "Vulnerable dependencies found"}]}
        except FileNotFoundError:
            return {"status": "skipped", "message": "safety not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _scan_secrets(self) -> Dict[str, Any]:
        """Поиск секретов в коде"""
        issues = []
        secret_patterns = [
            r"api_key\s*=\s*['\"](?!your_|change_|sk-)",
            r"password\s*=\s*['\"](?!change|your|password)",
            r"secret_key\s*=\s*['\"](?!change|your)",
            r"token\s*=\s*['\"](?!your|change)",
            r"AWS_SECRET_ACCESS_KEY",
            r"PRIVATE KEY"
        ]
        
        import re
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.env', '.yaml', '.yml', '.json']:
                if '.git' in str(file_path) or 'venv' in str(file_path):
                    continue
                
                try:
                    content = file_path.read_text()
                    for pattern in secret_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            issues.append(SecurityIssue(
                                file=str(file_path.relative_to(self.project_path)),
                                line=0,
                                severity="HIGH",
                                message=f"Potential secret found: {pattern}"
                            ))
                except:
                    pass
        
        return {
            "status": "failed" if issues else "passed",
            "issues": issues
        }
    
    def get_report(self) -> str:
        """Форматированный отчёт"""
        results = self.scan()
        
        lines = ["═══ Security Report ═══"]
        lines.append(f"Total issues: {results['total_issues']}")
        lines.append(f"Status: {'✓ PASSED' if results['passed'] else '✗ FAILED'}")
        lines.append("")
        
        for scan_type, data in results.items():
            if isinstance(data, dict) and "issues" in data:
                if data["issues"]:
                    lines.append(f"--- {scan_type} ---")
                    for issue in data["issues"]:
                        if isinstance(issue, SecurityIssue):
                            lines.append(f"  [{issue.severity}] {issue.file}:{issue.line} - {issue.message}")
                        else:
                            lines.append(f"  {issue}")
        
        return "\n".join(lines)
