"""
P4 — Large Repository Survival (Phase 9)

Handles real-world repository challenges:
  - Monorepos (100k+ files, multi-package, mixed tooling)
  - Broken repos (failing builds, missing deps, partial clones)
  - Legacy repos (circular deps, poor architecture, giant files)

Key principle: system must survive in dirty reality, not just clean demos.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path
from enum import Enum


class RepoSizeCategory(Enum):
    SMALL = "small"           # < 100 files
    MEDIUM = "medium"         # 100-1000 files
    LARGE = "large"           # 1000-10000 files
    MONOREPO = "monorepo"     # > 10000 files


class RepoHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"
    UNKNOWN = "unknown"


@dataclass
class RepoProfile:
    """Profile of a repository for survival decisions."""
    path: str
    total_files: int = 0
    total_dirs: int = 0
    size_category: RepoSizeCategory = RepoSizeCategory.SMALL
    health: RepoHealth = RepoHealth.UNKNOWN
    has_git: bool = False
    has_tests: bool = False
    has_ci: bool = False
    languages: list[str] = field(default_factory=list)
    max_file_size_bytes: int = 0
    avg_file_size_bytes: int = 0
    circular_deps_count: int = 0
    broken_imports_count: int = 0
    missing_deps_count: int = 0
    scan_time_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "total_files": self.total_files,
            "total_dirs": self.total_dirs,
            "size_category": self.size_category.value,
            "health": self.health.value,
            "has_git": self.has_git,
            "has_tests": self.has_tests,
            "has_ci": self.has_ci,
            "languages": self.languages,
            "max_file_size_bytes": self.max_file_size_bytes,
            "avg_file_size_bytes": round(self.avg_file_size_bytes),
            "circular_deps_count": self.circular_deps_count,
            "broken_imports_count": self.broken_imports_count,
            "missing_deps_count": self.missing_deps_count,
            "scan_time_seconds": round(self.scan_time_seconds, 3),
            "errors": self.errors,
        }


class LargeRepoSurvival:
    """
    Analyzes and adapts to large/difficult repositories.

    Usage:
        survival = LargeRepoSurvival()
        profile = survival.analyze("/path/to/huge/repo")
        strategy = survival.get_strategy(profile)
    """

    # File count thresholds
    SMALL_THRESHOLD = 100
    MEDIUM_THRESHOLD = 1000
    LARGE_THRESHOLD = 10000

    # Max file size to index (1MB)
    MAX_FILE_SIZE = 1_048_576

    # Directories to always skip
    SKIP_DIRS = {".git", "__pycache__", "node_modules", "venv", ".venv", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", ".next", ".nuxt", "target", "vendor", ".eggs"}

    def analyze(self, project_path: str, max_scan_files: int = 50000) -> RepoProfile:
        """
        Analyze a repository and produce a survival profile.

        Args:
            project_path: Path to the repository.
            max_scan_files: Maximum files to scan (safety limit for huge repos).
        """
        start = time.time()
        profile = RepoProfile(path=project_path)
        path = Path(project_path)

        if not path.is_dir():
            profile.errors.append(f"Path is not a directory: {project_path}")
            profile.health = RepoHealth.BROKEN
            return profile

        try:
            file_count = 0
            dir_count = 0
            total_size = 0
            max_size = 0
            lang_extensions: dict[str, int] = {}

            for root, dirs, files in os.walk(project_path):
                # Prune skipped directories
                dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

                dir_count += len(dirs)

                for f in files:
                    file_count += 1
                    if file_count > max_scan_files:
                        profile.errors.append(f"Scan limit reached ({max_scan_files} files)")
                        break

                    fp = Path(root) / f
                    try:
                        size = fp.stat().st_size
                        total_size += size
                        max_size = max(max_size, size)

                        ext = fp.suffix.lower()
                        if ext:
                            lang_extensions[ext] = lang_extensions.get(ext, 0) + 1
                    except OSError:
                        continue

                if file_count > max_scan_files:
                    break

            profile.total_files = file_count
            profile.total_dirs = dir_count
            profile.max_file_size_bytes = max_size
            profile.avg_file_size_bytes = total_size / file_count if file_count > 0 else 0

            # Categorize size
            if file_count >= self.LARGE_THRESHOLD:
                profile.size_category = RepoSizeCategory.MONOREPO
            elif file_count >= self.MEDIUM_THRESHOLD:
                profile.size_category = RepoSizeCategory.LARGE
            elif file_count >= self.SMALL_THRESHOLD:
                profile.size_category = RepoSizeCategory.MEDIUM
            else:
                profile.size_category = RepoSizeCategory.SMALL

            # Detect languages
            ext_to_lang = {
                ".py": "python", ".js": "javascript", ".ts": "typescript",
                ".tsx": "typescript", ".jsx": "javascript", ".go": "go",
                ".rs": "rust", ".java": "java", ".rb": "ruby", ".php": "php",
                ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
                ".swift": "swift", ".dart": "dart", ".zig": "zig",
            }
            lang_counts: dict[str, int] = {}
            for ext, count in lang_extensions.items():
                lang = ext_to_lang.get(ext)
                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + count
            profile.languages = sorted(lang_counts, key=lambda l: lang_counts[l], reverse=True)[:5]

            # Check for git, tests, CI
            profile.has_git = (path / ".git").is_dir()
            profile.has_tests = any(
                (path / d).is_dir() for d in ("tests", "test", "__tests__", "spec")
            )
            profile.has_ci = any(
                (path / d).is_dir() for d in (".github", ".gitlab-ci")
            ) or (path / "Jenkinsfile").is_file()

            # Assess health
            if file_count > 0:
                if profile.broken_imports_count > 10 or profile.circular_deps_count > 5:
                    profile.health = RepoHealth.BROKEN
                elif profile.missing_deps_count > 5 or not profile.has_tests:
                    profile.health = RepoHealth.DEGRADED
                else:
                    profile.health = RepoHealth.HEALTHY

        except Exception as e:
            profile.errors.append(f"Analysis error: {e}")
            profile.health = RepoHealth.UNKNOWN

        profile.scan_time_seconds = time.time() - start
        return profile

    def get_strategy(self, profile: RepoProfile) -> dict[str, Any]:
        """
        Get an adaptation strategy based on the repo profile.

        Returns configuration adjustments for handling this specific repo.
        """
        strategy: dict[str, Any] = {
            "index_batch_size": 100,
            "max_file_size": self.MAX_FILE_SIZE,
            "skip_dirs": list(self.SKIP_DIRS),
            "use_incremental": True,
            "parallel_scanning": False,
            "memory_limit_mb": 256,
        }

        if profile.size_category == RepoSizeCategory.MONOREPO:
            strategy.update({
                "index_batch_size": 500,
                "parallel_scanning": True,
                "memory_limit_mb": 1024,
                "use_incremental": True,
                "scan_depth_limit": 5,
                "prioritize_packages": True,
            })
        elif profile.size_category == RepoSizeCategory.LARGE:
            strategy.update({
                "index_batch_size": 200,
                "parallel_scanning": True,
                "memory_limit_mb": 512,
                "use_incremental": True,
            })

        if profile.health == RepoHealth.BROKEN:
            strategy.update({
                "safe_mode": True,
                "skip_validation": False,
                "extra_safety_checks": True,
            })

        return strategy

    def estimate_index_time(self, profile: RepoProfile) -> dict[str, Any]:
        """Estimate indexing time based on repo profile."""
        # Rough estimates based on file count
        files = profile.total_files
        if files < 100:
            seconds = 1
        elif files < 1000:
            seconds = files * 0.01  # ~10ms per file
        elif files < 10000:
            seconds = files * 0.005  # ~5ms per file (optimized)
        else:
            seconds = files * 0.003  # ~3ms per file (parallel)

        return {
            "estimated_seconds": round(seconds, 1),
            "estimated_human": f"{round(seconds)}s" if seconds < 60 else f"{round(seconds / 60)}min",
            "files": files,
            "category": profile.size_category.value,
        }
