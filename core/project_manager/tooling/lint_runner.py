"""
lint_runner.py — Lint Validation.

Supports: ruff, flake8, black --check, eslint, prettier --check, mypy.

Lint is used as a validation signal — failed lint blocks patch approval.
"""

from __future__ import annotations

import subprocess
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class LintIssue:
    """A single lint issue."""
    file_path: str = ""
    line_number: int = 0
    column: int = 0
    code: str = ""
    message: str = ""
    severity: str = "warning"  # error, warning, info


@dataclass
class LintResult:
    """Structured lint result."""
    tool: str = ""
    status: str = ""  # passed, failed, error
    issues: List[LintIssue] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    duration_ms: float = 0.0
    output: str = ""
    exit_code: int = 0

    @property
    def passed(self) -> bool:
        return self.error_count == 0 and self.status != "error"

    @property
    def total_issues(self) -> int:
        return len(self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "status": self.status,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "total_issues": self.total_issues,
            "duration_ms": round(self.duration_ms, 2),
            "issues": [
                {
                    "file_path": i.file_path,
                    "line_number": i.line_number,
                    "column": i.column,
                    "code": i.code,
                    "message": i.message[:300],
                    "severity": i.severity,
                }
                for i in self.issues[:100]  # Limit to 100 issues
            ],
        }


class LintRunner:
    """
    Controlled lint execution.
    Auto-detects available linters.
    """

    TIMEOUTS = {
        "ruff": 30,
        "flake8": 30,
        "black": 30,
        "eslint": 60,
        "prettier": 30,
        "mypy": 60,
    }

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()

    def detect_linters(self) -> List[str]:
        """Detect available linters in the project."""
        available = []

        # Python linters
        has_py = any(self._project_root.glob("*.py")) or \
                 (self._project_root / "pyproject.toml").exists()

        if has_py:
            if self._command_exists("ruff"):
                available.append("ruff")
            if self._command_exists("flake8"):
                available.append("flake8")
            if self._command_exists("black"):
                available.append("black")
            if self._command_exists("mypy"):
                available.append("mypy")

        # JS/TS linters
        if (self._project_root / "package.json").exists():
            if self._command_exists("eslint") or \
               (self._project_root / "node_modules" / ".bin" / "eslint").exists():
                available.append("eslint")
            if self._command_exists("prettier") or \
               (self._project_root / "node_modules" / ".bin" / "prettier").exists():
                available.append("prettier")

        return available

    def run(
        self,
        tool: str = "",
        target_path: str = "",
        extra_args: Optional[List[str]] = None,
    ) -> LintResult:
        """
        Run a lint tool.

        Args:
            tool: lint tool to use (auto-detect if empty)
            target_path: file or directory to lint
            extra_args: additional arguments
        """
        if not tool:
            available = self.detect_linters()
            if not available:
                return LintResult(
                    tool="none",
                    status="error",
                    output="No linters detected",
                )
            tool = available[0]

        if tool == "ruff":
            return self._run_ruff(target_path, extra_args)
        elif tool == "flake8":
            return self._run_flake8(target_path, extra_args)
        elif tool == "black":
            return self._run_black(target_path, extra_args)
        elif tool == "eslint":
            return self._run_eslint(target_path, extra_args)
        elif tool == "prettier":
            return self._run_prettier(target_path, extra_args)
        elif tool == "mypy":
            return self._run_mypy(target_path, extra_args)
        else:
            return LintResult(
                tool=tool,
                status="error",
                output=f"Unknown lint tool: {tool}",
            )

    def run_all(self, target_path: str = "") -> List[LintResult]:
        """Run all available linters."""
        results = []
        for tool in self.detect_linters():
            result = self.run(tool, target_path)
            results.append(result)
        return results

    def _run_ruff(self, target_path: str, extra_args: Optional[List[str]]) -> LintResult:
        """Run ruff check."""
        cmd = ["ruff", "check", "--output-format=text"]
        if extra_args:
            cmd.extend(extra_args)
        if target_path:
            cmd.append(target_path)
        else:
            cmd.append(".")

        return self._execute("ruff", cmd, self.TIMEOUTS["ruff"], self._parse_ruff_output)

    def _run_flake8(self, target_path: str, extra_args: Optional[List[str]]) -> LintResult:
        """Run flake8."""
        cmd = ["flake8", "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s"]
        if extra_args:
            cmd.extend(extra_args)
        if target_path:
            cmd.append(target_path)
        else:
            cmd.append(".")

        return self._execute("flake8", cmd, self.TIMEOUTS["flake8"], self._parse_flake8_output)

    def _run_black(self, target_path: str, extra_args: Optional[List[str]]) -> LintResult:
        """Run black --check."""
        cmd = ["black", "--check", "--diff"]
        if extra_args:
            cmd.extend(extra_args)
        if target_path:
            cmd.append(target_path)
        else:
            cmd.append(".")

        return self._execute("black", cmd, self.TIMEOUTS["black"], self._parse_black_output)

    def _run_eslint(self, target_path: str, extra_args: Optional[List[str]]) -> LintResult:
        """Run eslint."""
        cmd = ["npx", "eslint", "--format=compact"]
        if extra_args:
            cmd.extend(extra_args)
        if target_path:
            cmd.append(target_path)
        else:
            cmd.append(".")

        return self._execute("eslint", cmd, self.TIMEOUTS["eslint"], self._parse_eslint_output)

    def _run_prettier(self, target_path: str, extra_args: Optional[List[str]]) -> LintResult:
        """Run prettier --check."""
        cmd = ["npx", "prettier", "--check"]
        if extra_args:
            cmd.extend(extra_args)
        if target_path:
            cmd.append(target_path)
        else:
            cmd.append(".")

        return self._execute("prettier", cmd, self.TIMEOUTS["prettier"], self._parse_prettier_output)

    def _run_mypy(self, target_path: str, extra_args: Optional[List[str]]) -> LintResult:
        """Run mypy."""
        cmd = ["mypy", "--no-error-summary"]
        if extra_args:
            cmd.extend(extra_args)
        if target_path:
            cmd.append(target_path)
        else:
            cmd.append(".")

        return self._execute("mypy", cmd, self.TIMEOUTS["mypy"], self._parse_mypy_output)

    def _execute(
        self, tool: str, cmd: List[str], timeout: int, parser: callable
    ) -> LintResult:
        """Execute a lint command and parse results."""
        import time
        t0 = time.monotonic()

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self._project_root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration_ms = (time.monotonic() - t0) * 1000
            output = proc.stdout + "\n" + proc.stderr

            result = parser(output)
            result.tool = tool
            result.duration_ms = duration_ms
            result.exit_code = proc.returncode
            result.output = output[:5000]

            if proc.returncode == 0:
                result.status = "passed"
            else:
                result.status = "failed"

            return result

        except subprocess.TimeoutExpired:
            return LintResult(
                tool=tool,
                status="error",
                duration_ms=(time.monotonic() - t0) * 1000,
                output=f"Lint timed out after {timeout}s",
            )
        except FileNotFoundError:
            return LintResult(
                tool=tool,
                status="error",
                output=f"Command not found: {cmd[0]}",
            )
        except Exception as e:
            return LintResult(
                tool=tool,
                status="error",
                output=str(e),
            )

    # ── Output Parsers ──

    def _parse_ruff_output(self, output: str) -> LintResult:
        """Parse ruff output: file:line:col CODE message"""
        result = LintResult()
        pattern = re.compile(r'^(.+?):(\d+):(\d+):\s+(\w+)\s+(.+)$')
        for line in output.strip().split("\n"):
            match = pattern.match(line.strip())
            if match:
                issue = LintIssue(
                    file_path=match.group(1),
                    line_number=int(match.group(2)),
                    column=int(match.group(3)),
                    code=match.group(4),
                    message=match.group(5),
                    severity="error" if match.group(4).startswith("E") else "warning",
                )
                result.issues.append(issue)
                if issue.severity == "error":
                    result.error_count += 1
                else:
                    result.warning_count += 1
        return result

    def _parse_flake8_output(self, output: str) -> LintResult:
        """Parse flake8 output: file:line:col CODE message"""
        return self._parse_ruff_output(output)  # Same format

    def _parse_black_output(self, output: str) -> LintResult:
        """Parse black --check output."""
        result = LintResult()
        if "would reformat" in output:
            file_match = re.search(r'would reformat\s+(.+)', output)
            if file_match:
                issue = LintIssue(
                    file_path=file_match.group(1).strip(),
                    code="BLACK",
                    message="File would be reformatted by black",
                    severity="warning",
                )
                result.issues.append(issue)
                result.warning_count += 1
        return result

    def _parse_eslint_output(self, output: str) -> LintResult:
        """Parse eslint compact output: file: line X, col Y, Message - rule"""
        result = LintResult()
        pattern = re.compile(
            r'^(.+?):\s+line\s+(\d+),\s+col\s+(\d+),\s+(.+?)(?:\s+-\s+(.+))?$'
        )
        for line in output.strip().split("\n"):
            match = pattern.match(line.strip())
            if match:
                severity_str = match.group(4).lower()
                issue = LintIssue(
                    file_path=match.group(1),
                    line_number=int(match.group(2)),
                    column=int(match.group(3)),
                    message=severity_str,
                    code=match.group(6) or "",
                    severity="error" if "error" in severity_str else "warning",
                )
                result.issues.append(issue)
                if issue.severity == "error":
                    result.error_count += 1
                else:
                    result.warning_count += 1
        return result

    def _parse_prettier_output(self, output: str) -> LintResult:
        """Parse prettier --check output."""
        result = LintResult()
        for line in output.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("[") and not line.startswith("Checking"):
                issue = LintIssue(
                    file_path=line,
                    code="PRETTIER",
                    message="File would be reformatted by prettier",
                    severity="warning",
                )
                result.issues.append(issue)
                result.warning_count += 1
        return result

    def _parse_mypy_output(self, output: str) -> LintResult:
        """Parse mypy output: file:line: severity: message"""
        result = LintResult()
        pattern = re.compile(r'^(.+?):(\d+):\s+(error|warning|note):\s+(.+)$')
        for line in output.strip().split("\n"):
            match = pattern.match(line.strip())
            if match:
                issue = LintIssue(
                    file_path=match.group(1),
                    line_number=int(match.group(2)),
                    message=match.group(4),
                    code="MYPY",
                    severity=match.group(3) if match.group(3) in ("error", "warning") else "info",
                )
                result.issues.append(issue)
                if issue.severity == "error":
                    result.error_count += 1
                else:
                    result.warning_count += 1
        return result

    @staticmethod
    def _command_exists(cmd: str) -> bool:
        """Check if a command exists."""
        try:
            subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
