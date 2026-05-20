"""
test_runner.py — Controlled Test Execution.

Supports: pytest, npm test, vitest, jest, cargo test.

Tests are part of governance, not just output.
Failed tests block patch approval.
"""

from __future__ import annotations

import subprocess
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class TestFramework(str):
    PYTEST = "pytest"
    NPM_TEST = "npm_test"
    VITEST = "vitest"
    JEST = "jest"
    CARGO_TEST = "cargo_test"


@dataclass
class TestFailure:
    """A single test failure."""
    test_name: str = ""
    file_path: str = ""
    line_number: int = 0
    message: str = ""
    error_type: str = ""


@dataclass
class TestRunResult:
    """Structured test execution result."""
    framework: str = ""
    status: str = ""  # passed, failed, error, timeout
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0
    duration_ms: float = 0.0
    output: str = ""
    failures: List[TestFailure] = field(default_factory=list)
    impacted_files: List[str] = field(default_factory=list)
    exit_code: int = 0
    error: str = ""

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.status != "error" and self.status != "timeout"

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.passed / self.total * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "status": self.status,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total": self.total,
            "duration_ms": round(self.duration_ms, 2),
            "pass_rate": self.pass_rate,
            "all_passed": self.all_passed,
            "failures": [
                {
                    "test_name": f.test_name,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "message": f.message[:500],
                    "error_type": f.error_type,
                }
                for f in self.failures
            ],
            "impacted_files": self.impacted_files,
            "exit_code": self.exit_code,
            "error": self.error[:500] if self.error else "",
        }


class TestRunner:
    """
    Controlled test execution.

    Auto-detects the test framework from project structure.
    Runs tests in a controlled manner with timeouts.
    Returns structured results.
    """

    # Timeout per framework (seconds)
    TIMEOUTS = {
        "pytest": 120,
        "npm_test": 120,
        "vitest": 120,
        "jest": 120,
        "cargo_test": 180,
    }

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()

    def detect_framework(self) -> Optional[str]:
        """Auto-detect the test framework from project structure."""
        # Check for Rust
        if (self._project_root / "Cargo.toml").exists():
            return "cargo_test"

        # Check for Node.js
        package_json = self._project_root / "package.json"
        if package_json.exists():
            try:
                content = package_json.read_text(encoding="utf-8")
                pkg = json.loads(content)
                scripts = pkg.get("scripts", {})
                dev_deps = pkg.get("devDependencies", {})
                deps = pkg.get("dependencies", {})

                # Check for vitest
                if "vitest" in dev_deps or "vitest" in deps:
                    return "vitest"
                # Check for jest
                if "jest" in dev_deps or "jest" in deps:
                    return "jest"
                # Check for test script
                if "test" in scripts:
                    return "npm_test"
            except (json.JSONDecodeError, IOError):
                pass

        # Check for Python
        if any(self._project_root.glob("test_*.py")) or \
           any(self._project_root.glob("*_test.py")) or \
           (self._project_root / "tests").is_dir() or \
           (self._project_root / "pytest.ini").exists() or \
           (self._project_root / "pyproject.toml").exists():
            return "pytest"

        return None

    def run(
        self,
        framework: str = "",
        test_path: str = "",
        extra_args: Optional[List[str]] = None,
        timeout: int = 0,
    ) -> TestRunResult:
        """
        Run tests with the specified framework.

        Args:
            framework: test framework to use (auto-detect if empty)
            test_path: specific test file/directory to run
            extra_args: additional arguments
            timeout: override timeout (seconds)
        """
        if not framework:
            framework = self.detect_framework() or "pytest"

        if framework == "pytest":
            return self._run_pytest(test_path, extra_args, timeout)
        elif framework == "npm_test":
            return self._run_npm_test(test_path, extra_args, timeout)
        elif framework == "vitest":
            return self._run_vitest(test_path, extra_args, timeout)
        elif framework == "jest":
            return self._run_jest(test_path, extra_args, timeout)
        elif framework == "cargo_test":
            return self._run_cargo_test(test_path, extra_args, timeout)
        else:
            return TestRunResult(
                framework=framework,
                status="error",
                error=f"Unknown framework: {framework}",
            )

    def _run_pytest(
        self, test_path: str, extra_args: Optional[List[str]], timeout: int
    ) -> TestRunResult:
        """Run pytest."""
        import sys
        timeout = timeout or self.TIMEOUTS["pytest"]
        cmd = [sys.executable, "-m", "pytest", "--tb=short", "-q", "--no-header"]
        if test_path:
            cmd.append(test_path)
        if extra_args:
            cmd.extend(extra_args)

        return self._execute("pytest", cmd, timeout, self._parse_pytest_output)

    def _run_npm_test(
        self, test_path: str, extra_args: Optional[List[str]], timeout: int
    ) -> TestRunResult:
        """Run npm test."""
        timeout = timeout or self.TIMEOUTS["npm_test"]
        cmd = ["npm", "test", "--", "--reporter=dot"]
        if test_path:
            cmd.append(test_path)
        if extra_args:
            cmd.extend(extra_args)

        return self._execute("npm_test", cmd, timeout, self._parse_npm_output)

    def _run_vitest(
        self, test_path: str, extra_args: Optional[List[str]], timeout: int
    ) -> TestRunResult:
        """Run vitest."""
        timeout = timeout or self.TIMEOUTS["vitest"]
        cmd = ["npx", "vitest", "run", "--reporter=verbose"]
        if test_path:
            cmd.append(test_path)
        if extra_args:
            cmd.extend(extra_args)

        return self._execute("vitest", cmd, timeout, self._parse_vitest_output)

    def _run_jest(
        self, test_path: str, extra_args: Optional[List[str]], timeout: int
    ) -> TestRunResult:
        """Run jest."""
        timeout = timeout or self.TIMEOUTS["jest"]
        cmd = ["npx", "jest", "--no-coverage", "--verbose"]
        if test_path:
            cmd.append(test_path)
        if extra_args:
            cmd.extend(extra_args)

        return self._execute("jest", cmd, timeout, self._parse_jest_output)

    def _run_cargo_test(
        self, test_path: str, extra_args: Optional[List[str]], timeout: int
    ) -> TestRunResult:
        """Run cargo test."""
        timeout = timeout or self.TIMEOUTS["cargo_test"]
        cmd = ["cargo", "test"]
        if test_path:
            cmd.append(test_path)
        if extra_args:
            cmd.extend(extra_args)

        return self._execute("cargo_test", cmd, timeout, self._parse_cargo_output)

    def _execute(
        self,
        framework: str,
        cmd: List[str],
        timeout: int,
        parser: callable,
    ) -> TestRunResult:
        """Execute a test command and parse results."""
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
            result.framework = framework
            result.duration_ms = duration_ms
            result.exit_code = proc.returncode
            result.output = output[:10000]

            if proc.returncode == 0:
                result.status = "passed"
            else:
                result.status = "failed"

            return result

        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - t0) * 1000
            return TestRunResult(
                framework=framework,
                status="timeout",
                duration_ms=duration_ms,
                error=f"Tests timed out after {timeout}s",
            )
        except FileNotFoundError as e:
            return TestRunResult(
                framework=framework,
                status="error",
                error=f"Command not found: {e}",
            )
        except Exception as e:
            return TestRunResult(
                framework=framework,
                status="error",
                error=str(e),
            )

    # ── Output Parsers ──

    def _parse_pytest_output(self, output: str) -> TestRunResult:
        """Parse pytest output."""
        result = TestRunResult()

        # Parse summary line: "5 passed, 2 failed, 1 skipped" or "1 passed in 0.00s" or "1 failed in 0.01s"
        # Try combined format first
        summary_match = re.search(
            r'(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+skipped)?',
            output,
        )
        if summary_match and summary_match.group(1):
            result.passed = int(summary_match.group(1))
            result.failed = int(summary_match.group(2) or 0)
            result.skipped = int(summary_match.group(3) or 0)
        else:
            # Try individual patterns
            passed_match = re.search(r'(\d+)\s+passed', output)
            failed_match = re.search(r'(\d+)\s+failed', output)
            skipped_match = re.search(r'(\d+)\s+skipped', output)
            result.passed = int(passed_match.group(1)) if passed_match else 0
            result.failed = int(failed_match.group(1)) if failed_match else 0
            result.skipped = int(skipped_match.group(1)) if skipped_match else 0

        result.total = result.passed + result.failed + result.skipped

        # Parse individual failures
        failure_blocks = re.findall(
            r'FAILED\s+(\S+)\s+-\s+(.+?)(?=\n\n|\nFAILED|\Z)',
            output,
            re.DOTALL,
        )
        for test_name, message in failure_blocks:
            failure = TestFailure(
                test_name=test_name.strip(),
                message=message.strip()[:500],
            )
            # Extract file path and line
            file_match = re.search(r'(\S+\.py):(\d+)', message)
            if file_match:
                failure.file_path = file_match.group(1)
                failure.line_number = int(file_match.group(2))
            result.failures.append(failure)

        # Extract impacted files
        for match in re.finditer(r'(\S+\.py)', output):
            path = match.group(1)
            if path not in result.impacted_files:
                result.impacted_files.append(path)

        return result

    def _parse_npm_output(self, output: str) -> TestRunResult:
        """Parse npm test output."""
        result = TestRunResult()
        # "Tests: 5 passed, 2 failed"
        match = re.search(r'Tests:\s+(\d+)\s+passed(?:,\s+(\d+)\s+failed)?', output)
        if match:
            result.passed = int(match.group(1))
            result.failed = int(match.group(2) or 0)
        result.total = result.passed + result.failed
        return result

    def _parse_vitest_output(self, output: str) -> TestRunResult:
        """Parse vitest output."""
        result = TestRunResult()
        # "Tests 5 passed (5)"
        match = re.search(r'Tests\s+(\d+)\s+passed', output)
        if match:
            result.passed = int(match.group(1))
        failed_match = re.search(r'(\d+)\s+failed', output)
        if failed_match:
            result.failed = int(failed_match.group(1))
        result.total = result.passed + result.failed
        return result

    def _parse_jest_output(self, output: str) -> TestRunResult:
        """Parse jest output."""
        result = TestRunResult()
        # "Tests: 5 passed, 2 total"
        match = re.search(r'Tests:\s+(\d+)\s+passed', output)
        if match:
            result.passed = int(match.group(1))
        failed_match = re.search(r'(\d+)\s+failed', output)
        if failed_match:
            result.failed = int(failed_match.group(1))
        total_match = re.search(r'(\d+)\s+total', output)
        if total_match:
            result.total = int(total_match.group(1))
        else:
            result.total = result.passed + result.failed
        return result

    def _parse_cargo_output(self, output: str) -> TestRunResult:
        """Parse cargo test output."""
        result = TestRunResult()
        # "test result: ok. 5 passed; 0 failed"
        match = re.search(r'test result:\s+\w+\.\s+(\d+)\s+passed(?:;\s+(\d+)\s+failed)?', output)
        if match:
            result.passed = int(match.group(1))
            result.failed = int(match.group(2) or 0)
        result.total = result.passed + result.failed
        return result
