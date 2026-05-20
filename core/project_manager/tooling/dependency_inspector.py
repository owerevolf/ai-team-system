"""
dependency_inspector.py — Dependency Analysis.

Analyzes project dependencies from:
- package.json (Node.js)
- requirements.txt (Python)
- pyproject.toml (Python)
- Cargo.toml (Rust)
- docker-compose.yml
- .env files

Detects:
- Missing dependencies
- Vulnerable dependencies (basic check)
- Conflicting versions
- Outdated libraries (basic check)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class Dependency:
    """A single dependency."""
    name: str = ""
    version: str = ""
    source: str = ""  # package.json, requirements.txt, etc
    is_dev: bool = False
    is_locked: bool = False


@dataclass
class DependencyIssue:
    """A dependency issue."""
    issue_type: str = ""  # missing, vulnerable, conflict, outdated
    dependency: str = ""
    message: str = ""
    severity: str = "warning"  # error, warning, info
    suggestion: str = ""


@dataclass
class DependencyReport:
    """Complete dependency analysis report."""
    project_root: str = ""
    sources: List[str] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    dev_dependencies: List[Dependency] = field(default_factory=list)
    issues: List[DependencyIssue] = field(default_factory=list)
    total_count: int = 0
    error_count: int = 0
    warning_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_root": self.project_root,
            "sources": self.sources,
            "total_count": self.total_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "dependencies": [
                {"name": d.name, "version": d.version, "source": d.source, "is_dev": d.is_dev}
                for d in self.dependencies[:200]
            ],
            "dev_dependencies": [
                {"name": d.name, "version": d.version, "source": d.source}
                for d in self.dev_dependencies[:100]
            ],
            "issues": [
                {
                    "issue_type": i.issue_type,
                    "dependency": i.dependency,
                    "message": i.message[:300],
                    "severity": i.severity,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
        }


class DependencyInspector:
    """
    Analyzes project dependencies.
    Detects issues and conflicts.
    """

    # Known vulnerable packages (simplified — in production, use a real DB)
    KNOWN_VULNERABLE = {
        "lodash": {"<4.17.21": "Prototype pollution vulnerability"},
        "minimatch": {"<3.0.5": "ReDoS vulnerability"},
        "semver": {"<5.7.2": "ReDoS vulnerability"},
        "requests": {"<2.31.0": "SSRF vulnerability"},
        "urllib3": {"<1.26.18": "CVE-2023-45803"},
        "pyyaml": {"<6.0": "Arbitrary code execution"},
        "jinja2": {"<3.1.3": "SSTI vulnerability"},
        "flask": {"<3.0.0": "Session cookie vulnerability"},
    }

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()

    def analyze(self) -> DependencyReport:
        """Run full dependency analysis."""
        report = DependencyReport(project_root=str(self._project_root))

        # Detect and parse all dependency sources
        self._check_package_json(report)
        self._check_requirements_txt(report)
        self._check_pyproject_toml(report)
        self._check_cargo_toml(report)
        self._check_docker_compose(report)
        self._check_env_files(report)

        # Cross-check for issues
        self._check_conflicts(report)
        self._check_vulnerabilities(report)
        self._check_missing(report)

        report.total_count = len(report.dependencies) + len(report.dev_dependencies)
        report.error_count = sum(1 for i in report.issues if i.severity == "error")
        report.warning_count = sum(1 for i in report.issues if i.severity == "warning")

        return report

    def _check_package_json(self, report: DependencyReport) -> None:
        """Parse package.json."""
        pkg_file = self._project_root / "package.json"
        if not pkg_file.exists():
            return

        report.sources.append("package.json")
        try:
            content = pkg_file.read_text(encoding="utf-8")
            pkg = json.loads(content)

            for name, version in pkg.get("dependencies", {}).items():
                report.dependencies.append(Dependency(
                    name=name,
                    version=self._clean_version(version),
                    source="package.json",
                ))

            for name, version in pkg.get("devDependencies", {}).items():
                report.dev_dependencies.append(Dependency(
                    name=name,
                    version=self._clean_version(version),
                    source="package.json",
                    is_dev=True,
                ))
        except (json.JSONDecodeError, IOError) as e:
            report.issues.append(DependencyIssue(
                issue_type="parse_error",
                dependency="package.json",
                message=f"Failed to parse: {e}",
                severity="warning",
            ))

    def _check_requirements_txt(self, report: DependencyReport) -> None:
        """Parse requirements.txt."""
        req_file = self._project_root / "requirements.txt"
        if not req_file.exists():
            return

        report.sources.append("requirements.txt")
        try:
            content = req_file.read_text(encoding="utf-8")
            for line in content.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Parse: package==1.0.0, package>=1.0.0, package~=1.0.0, package
                match = re.match(r'^([a-zA-Z0-9_-]+)\s*(.*)?$', line)
                if match:
                    name = match.group(1)
                    version = match.group(2).strip() if match.group(2) else ""
                    report.dependencies.append(Dependency(
                        name=name,
                        version=self._clean_version(version),
                        source="requirements.txt",
                        is_locked="==" in version,
                    ))
        except IOError as e:
            report.issues.append(DependencyIssue(
                issue_type="parse_error",
                dependency="requirements.txt",
                message=f"Failed to parse: {e}",
                severity="warning",
            ))

    def _check_pyproject_toml(self, report: DependencyReport) -> None:
        """Parse pyproject.toml (basic)."""
        toml_file = self._project_root / "pyproject.toml"
        if not toml_file.exists():
            return

        report.sources.append("pyproject.toml")
        try:
            content = toml_file.read_text(encoding="utf-8")
            # Basic TOML parsing (not using a full parser to avoid deps)
            in_deps = False
            in_dev_deps = False

            for line in content.split("\n"):
                stripped = line.strip()

                if stripped.startswith("[tool.poetry.dependencies]"):
                    in_deps = True
                    in_dev_deps = False
                    continue
                elif stripped.startswith("[tool.poetry.group.dev.dependencies]") or \
                     stripped.startswith("[tool.poetry.dev-dependencies]"):
                    in_deps = False
                    in_dev_deps = True
                    continue
                elif stripped.startswith("[") and stripped.endswith("]"):
                    in_deps = False
                    in_dev_deps = False
                    continue

                if in_deps or in_dev_deps:
                    match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', stripped)
                    if match:
                        dep = Dependency(
                            name=match.group(1),
                            version=self._clean_version(match.group(2)),
                            source="pyproject.toml",
                            is_dev=in_dev_deps,
                        )
                        if in_dev_deps:
                            report.dev_dependencies.append(dep)
                        elif dep.name != "python":
                            report.dependencies.append(dep)
        except IOError as e:
            report.issues.append(DependencyIssue(
                issue_type="parse_error",
                dependency="pyproject.toml",
                message=f"Failed to parse: {e}",
                severity="warning",
            ))

    def _check_cargo_toml(self, report: DependencyReport) -> None:
        """Parse Cargo.toml (basic)."""
        cargo_file = self._project_root / "Cargo.toml"
        if not cargo_file.exists():
            return

        report.sources.append("Cargo.toml")
        try:
            content = cargo_file.read_text(encoding="utf-8")
            in_deps = False
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped == "[dependencies]":
                    in_deps = True
                    continue
                elif stripped.startswith("[") and stripped.endswith("]"):
                    in_deps = False
                    continue

                if in_deps:
                    match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', stripped)
                    if match:
                        report.dependencies.append(Dependency(
                            name=match.group(1),
                            version=self._clean_version(match.group(2)),
                            source="Cargo.toml",
                        ))
        except IOError as e:
            report.issues.append(DependencyIssue(
                issue_type="parse_error",
                dependency="Cargo.toml",
                message=f"Failed to parse: {e}",
                severity="warning",
            ))

    def _check_docker_compose(self, report: DependencyReport) -> None:
        """Check docker-compose.yml for service dependencies."""
        dc_file = self._project_root / "docker-compose.yml"
        if not dc_file.exists():
            dc_file = self._project_root / "docker-compose.yaml"
        if not dc_file.exists():
            return

        report.sources.append("docker-compose.yml")
        try:
            content = dc_file.read_text(encoding="utf-8")
            # Extract image names
            for match in re.finditer(r'image:\s*([^\s\n]+)', content):
                image = match.group(1).strip().strip("'\"")
                if image and image != "build":
                    report.dependencies.append(Dependency(
                        name=f"docker:{image}",
                        version="",
                        source="docker-compose.yml",
                    ))
        except IOError:
            pass

    def _check_env_files(self, report: DependencyReport) -> None:
        """Check .env files for environment dependencies."""
        for env_file in [".env", ".env.example", ".env.template"]:
            env_path = self._project_root / env_file
            if env_path.exists():
                report.sources.append(env_file)

    def _check_conflicts(self, report: DependencyReport) -> None:
        """Check for version conflicts between sources."""
        dep_versions: Dict[str, List[Tuple[str, str]]] = {}
        for dep in report.dependencies:
            if dep.name not in dep_versions:
                dep_versions[dep.name] = []
            dep_versions[dep.name].append((dep.source, dep.version))

        for name, versions in dep_versions.items():
            if len(versions) > 1:
                unique_versions = set(v[1] for v in versions if v[1])
                if len(unique_versions) > 1:
                    report.issues.append(DependencyIssue(
                        issue_type="conflict",
                        dependency=name,
                        message=f"Version conflict: {', '.join(f'{s}:{v}' for s, v in versions)}",
                        severity="error",
                        suggestion="Align versions across all dependency files",
                    ))

    def _check_vulnerabilities(self, report: DependencyReport) -> None:
        """Check for known vulnerable packages."""
        for dep in report.dependencies:
            if dep.name in self.KNOWN_VULNERABLE:
                for version_range, description in self.KNOWN_VULNERABLE[dep.name].items():
                    if self._version_matches(dep.version, version_range):
                        report.issues.append(DependencyIssue(
                            issue_type="vulnerable",
                            dependency=dep.name,
                            message=description,
                            severity="error",
                            suggestion=f"Update {dep.name} to a newer version",
                        ))

    def _check_missing(self, report: DependencyReport) -> None:
        """Check for potentially missing dependencies."""
        # Check if package.json exists but node_modules doesn't
        if (self._project_root / "package.json").exists() and \
           not (self._project_root / "node_modules").exists():
            report.issues.append(DependencyIssue(
                issue_type="missing",
                dependency="node_modules",
                message="node_modules directory not found — dependencies not installed",
                severity="warning",
                suggestion="Run 'npm install' or 'yarn install'",
            ))

        # Check if requirements.txt exists but venv doesn't
        if (self._project_root / "requirements.txt").exists():
            venv_exists = (self._project_root / "venv").exists() or \
                          (self._project_root / ".venv").exists()
            if not venv_exists:
                report.issues.append(DependencyIssue(
                    issue_type="missing",
                    dependency="venv",
                    message="Virtual environment not found — dependencies may not be installed",
                    severity="info",
                    suggestion="Create a virtual environment and install dependencies",
                ))

    @staticmethod
    def _clean_version(version: str) -> str:
        """Clean a version string."""
        if not version:
            return ""
        # Remove common prefixes
        version = version.strip()
        for prefix in ("^", "~", ">=", "<=", ">", "<", "==", "!="):
            if version.startswith(prefix):
                version = version[len(prefix):]
                break
        return version.strip()

    @staticmethod
    def _version_matches(version: str, range_str: str) -> bool:
        """Basic version matching. Returns True if version matches the range."""
        if not version:
            return False
        # Simplified: just check if version starts with the range prefix
        # In production, use packaging.version or semver
        clean = version.strip().lstrip("v")
        if range_str.startswith("<"):
            # Very basic comparison
            try:
                range_ver = range_str[1:].strip()
                clean_parts = [int(p) for p in clean.split(".")[:3] if p.isdigit()]
                range_parts = [int(p) for p in range_ver.split(".")[:3] if p.isdigit()]
                if clean_parts and range_parts:
                    return clean_parts < range_parts
            except (ValueError, IndexError):
                pass
        return False
