"""
Repo Scanner — project understanding engine.

Not just tree walk. Engineering understanding.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class RepoMap:
    """Structured map of a repository."""
    root_path: str = ""
    total_files: int = 0
    total_lines: int = 0
    languages: Dict[str, int] = field(default_factory=dict)  # ext -> count
    frameworks: List[str] = field(default_factory=list)
    entrypoints: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    doc_files: List[str] = field(default_factory=list)
    risky_zones: List[str] = field(default_factory=list)
    generated_files: List[str] = field(default_factory=list)
    huge_files: List[str] = field(default_factory=list)  # > 1000 lines
    dead_zones: List[str] = field(default_factory=list)  # empty dirs
    package_managers: List[str] = field(default_factory=list)
    has_docker: bool = False
    has_ci: bool = False


class RepoScanner:
    """
    Scans and understands a project repository.

    Detects:
    - frameworks, languages, package managers
    - docker, CI, tests, entrypoints
    - risky zones, generated files, huge files
    - dead zones, unstable modules
    """

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "fastapi": ["from fastapi", "import fastapi", "FastAPI()"],
        "django": ["from django", "import django", "django.conf"],
        "flask": ["from flask", "import flask", "Flask(__name__)"],
        "react": ["from 'react'", 'from "react"', "import React"],
        "vue": ["from 'vue'", 'from "vue"', "createApp("],
        "express": ["require('express')", "from 'express'"],
        "next": ["next.config", "getStaticProps", "getServerSideProps"],
    }

    # Entrypoint patterns
    ENTRYPOINT_PATTERNS = [
        "main.py", "app.py", "server.py", "index.py",
        "main.ts", "app.ts", "server.ts", "index.ts",
        "index.js", "server.js", "app.js",
        "manage.py", "wsgi.py", "asgi.py",
    ]

    # Config file patterns
    CONFIG_PATTERNS = [
        "pyproject.toml", "setup.py", "setup.cfg",
        "package.json", "package-lock.json",
        "requirements.txt", "Pipfile", "poetry.lock",
        "Dockerfile", "docker-compose.yml",
        ".env", ".env.example",
        "tsconfig.json", "webpack.config", "vite.config",
        "pytest.ini", "setup.cfg", "tox.ini",
        ".github/workflows", ".gitlab-ci.yml",
    ]

    # Generated file patterns
    GENERATED_PATTERNS = [
        "__pycache__", "*.pyc", "node_modules",
        "*.min.js", "*.min.css", "dist/", "build/",
        ".egg-info", "*.egg", ".tox",
    ]

    # Risky zone patterns
    RISKY_PATTERNS = [
        "auth", "security", "password", "secret", "token",
        "crypto", "ssl", "tls", "certificate",
        "migration", "schema", "database", "config",
        "middleware", "permission", "role",
    ]

    def __init__(self, root_path: str = "."):
        self._root = Path(root_path)
        self._ignore = {'.git', '__pycache__', 'node_modules', '.venv',
                       'venv', '.ai-team', '.tox', '.eggs', 'dist', 'build'}

    def scan(self) -> RepoMap:
        """Scan the repository and build a structured map."""
        repo_map = RepoMap(root_path=str(self._root))

        if not self._root.exists():
            return repo_map

        all_files = []
        for f in self._root.rglob("*"):
            if f.is_file() and not any(i in str(f) for i in self._ignore):
                all_files.append(f)
                rel = str(f.relative_to(self._root))

                # Count languages
                ext = f.suffix
                if ext:
                    repo_map.languages[ext] = repo_map.languages.get(ext, 0) + 1

                # Count lines
                try:
                    lines = f.read_text(encoding='utf-8').count('\n') + 1
                    repo_map.total_lines += lines
                    if lines > 1000:
                        repo_map.huge_files.append(rel)
                except (IOError, UnicodeDecodeError):
                    pass

                # Check entrypoints
                if f.name in self.ENTRYPOINT_PATTERNS:
                    repo_map.entrypoints.append(rel)

                # Check config files
                if any(p in rel for p in self.CONFIG_PATTERNS):
                    repo_map.config_files.append(rel)

                # Check test files
                if "test" in f.name.lower() or "spec" in f.name.lower():
                    repo_map.test_files.append(rel)

                # Check doc files
                if f.suffix in ('.md', '.rst', '.txt') or f.name.lower() == 'readme':
                    repo_map.doc_files.append(rel)

                # Check generated files
                if any(p in rel for p in self.GENERATED_PATTERNS):
                    repo_map.generated_files.append(rel)

                # Check risky zones
                if any(p in rel.lower() for p in self.RISKY_PATTERNS):
                    repo_map.risky_zones.append(rel)

        repo_map.total_files = len(all_files)

        # Detect frameworks from file contents
        repo_map.frameworks = self._detect_frameworks(all_files)

        # Detect package managers
        repo_map.package_managers = self._detect_package_managers()

        # Detect docker
        repo_map.has_docker = any(
            f.name == "Dockerfile" or f.name.startswith("docker-compose")
            for f in self._root.iterdir() if f.is_file()
        )

        # Detect CI
        repo_map.has_ci = (
            (self._root / ".github" / "workflows").exists() or
            (self._root / ".gitlab-ci.yml").exists() or
            (self._root / "Jenkinsfile").exists()
        )

        return repo_map

    def _detect_frameworks(self, files: List[Path]) -> List[str]:
        """Detect frameworks from file contents."""
        detected = set()
        # Only check a sample of files for performance
        sample = [f for f in files if f.suffix in ('.py', '.js', '.ts', '.tsx', '.jsx')][:50]
        for f in sample:
            try:
                content = f.read_text(encoding='utf-8', errors='ignore')[:5000]
                for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                    if any(p in content for p in patterns):
                        detected.add(framework)
            except (IOError, UnicodeDecodeError):
                pass
        return list(detected)

    def _detect_package_managers(self) -> List[str]:
        """Detect package managers from config files."""
        managers = []
        if (self._root / "pyproject.toml").exists():
            managers.append("poetry")
        if (self._root / "requirements.txt").exists():
            managers.append("pip")
        if (self._root / "Pipfile").exists():
            managers.append("pipenv")
        if (self._root / "package.json").exists():
            managers.append("npm")
        if (self._root / "yarn.lock").exists():
            managers.append("yarn")
        return managers

    def get_summary(self, repo_map: RepoMap) -> str:
        """Generate a human-readable summary of the repo."""
        lines = [
            f"Repository: {repo_map.root_path}",
            f"Files: {repo_map.total_files} | Lines: {repo_map.total_lines}",
        ]
        if repo_map.languages:
            langs = ", ".join(f"{ext}: {cnt}" for ext, cnt in
                            sorted(repo_map.languages.items(),
                                  key=lambda x: x[1], reverse=True)[:5])
            lines.append(f"Languages: {langs}")
        if repo_map.frameworks:
            lines.append(f"Frameworks: {', '.join(repo_map.frameworks)}")
        if repo_map.package_managers:
            lines.append(f"Package managers: {', '.join(repo_map.package_managers)}")
        if repo_map.entrypoints:
            lines.append(f"Entrypoints: {', '.join(repo_map.entrypoints[:5])}")
        if repo_map.has_docker:
            lines.append("Docker: yes")
        if repo_map.has_ci:
            lines.append("CI: yes")
        if repo_map.risky_zones:
            lines.append(f"Risky zones: {len(repo_map.risky_zones)} files")
        if repo_map.huge_files:
            lines.append(f"Huge files: {len(repo_map.huge_files)} files > 1000 lines")

        return "\n".join(lines)
