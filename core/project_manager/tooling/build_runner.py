"""
build_runner.py — Controlled Build Execution.

Supports:
- npm build
- vite build
- python package validation
- docker compose config
- tsc validation

NOT production deploy. Only verification build.
"""

from __future__ import annotations

import subprocess
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class BuildResult:
    """Structured build result."""
    builder: str = ""
    status: str = ""  # success, failed, error, timeout
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    artifacts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "builder": self.builder,
            "status": self.status,
            "success": self.success,
            "output": self.output[:5000] if self.output else "",
            "error": self.error[:2000] if self.error else "",
            "exit_code": self.exit_code,
            "duration_ms": round(self.duration_ms, 2),
            "artifacts": self.artifacts,
            "warnings": self.warnings,
        }


class BuildRunner:
    """
    Controlled build execution.
    Verification builds only — no production deploy.
    """

    TIMEOUTS = {
        "npm_build": 120,
        "vite_build": 120,
        "python_check": 30,
        "docker_compose_config": 30,
        "tsc": 60,
    }

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()

    def detect_builders(self) -> List[str]:
        """Detect available builders."""
        available = []

        if (self._project_root / "package.json").exists():
            try:
                content = (self._project_root / "package.json").read_text(encoding="utf-8")
                pkg = json.loads(content)
                scripts = pkg.get("scripts", {})

                if "build" in scripts:
                    if "vite" in scripts.get("build", ""):
                        available.append("vite_build")
                    else:
                        available.append("npm_build")
            except (json.JSONDecodeError, IOError):
                pass

        if (self._project_root / "pyproject.toml").exists() or \
           (self._project_root / "setup.py").exists():
            available.append("python_check")

        if (self._project_root / "docker-compose.yml").exists() or \
           (self._project_root / "docker-compose.yaml").exists():
            available.append("docker_compose_config")

        if (self._project_root / "tsconfig.json").exists():
            available.append("tsc")

        return available

    def run(
        self,
        builder: str = "",
        extra_args: Optional[List[str]] = None,
    ) -> BuildResult:
        """
        Run a build.

        Args:
            builder: build tool to use (auto-detect if empty)
            extra_args: additional arguments
        """
        if not builder:
            available = self.detect_builders()
            if not available:
                return BuildResult(
                    builder="none",
                    status="error",
                    error="No builders detected",
                )
            builder = available[0]

        if builder == "npm_build":
            return self._run_npm_build(extra_args)
        elif builder == "vite_build":
            return self._run_vite_build(extra_args)
        elif builder == "python_check":
            return self._run_python_check(extra_args)
        elif builder == "docker_compose_config":
            return self._run_docker_compose_config(extra_args)
        elif builder == "tsc":
            return self._run_tsc(extra_args)
        else:
            return BuildResult(
                builder=builder,
                status="error",
                error=f"Unknown builder: {builder}",
            )

    def _run_npm_build(self, extra_args: Optional[List[str]]) -> BuildResult:
        """Run npm build."""
        cmd = ["npm", "run", "build"]
        if extra_args:
            cmd.extend(extra_args)
        return self._execute("npm_build", cmd, self.TIMEOUTS["npm_build"])

    def _run_vite_build(self, extra_args: Optional[List[str]]) -> BuildResult:
        """Run vite build."""
        cmd = ["npx", "vite", "build"]
        if extra_args:
            cmd.extend(extra_args)
        return self._execute("vite_build", cmd, self.TIMEOUTS["vite_build"])

    def _run_python_check(self, extra_args: Optional[List[str]]) -> BuildResult:
        """Run python package validation."""
        cmd = ["python", "-c", "import sys; sys.path.insert(0, '.'); from core import main; print('OK')"]
        if extra_args:
            cmd = extra_args
        return self._execute("python_check", cmd, self.TIMEOUTS["python_check"])

    def _run_docker_compose_config(self, extra_args: Optional[List[str]]) -> BuildResult:
        """Run docker compose config validation."""
        cmd = ["docker", "compose", "config"]
        if extra_args:
            cmd.extend(extra_args)
        return self._execute("docker_compose_config", cmd, self.TIMEOUTS["docker_compose_config"])

    def _run_tsc(self, extra_args: Optional[List[str]]) -> BuildResult:
        """Run TypeScript compiler validation."""
        cmd = ["npx", "tsc", "--noEmit"]
        if extra_args:
            cmd.extend(extra_args)
        return self._execute("tsc", cmd, self.TIMEOUTS["tsc"])

    def _execute(self, builder: str, cmd: List[str], timeout: int) -> BuildResult:
        """Execute a build command."""
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

            result = BuildResult(
                builder=builder,
                output=output[:10000],
                error=proc.stderr[:2000] if proc.returncode != 0 else "",
                exit_code=proc.returncode,
                duration_ms=duration_ms,
            )

            if proc.returncode == 0:
                result.status = "success"
            else:
                result.status = "failed"

            # Extract warnings
            for line in output.split("\n"):
                if "warning" in line.lower() or "warn" in line.lower():
                    result.warnings.append(line.strip()[:200])

            return result

        except subprocess.TimeoutExpired:
            return BuildResult(
                builder=builder,
                status="timeout",
                duration_ms=(time.monotonic() - t0) * 1000,
                error=f"Build timed out after {timeout}s",
            )
        except FileNotFoundError as e:
            return BuildResult(
                builder=builder,
                status="error",
                error=f"Command not found: {e}",
            )
        except Exception as e:
            return BuildResult(
                builder=builder,
                status="error",
                error=str(e),
            )
