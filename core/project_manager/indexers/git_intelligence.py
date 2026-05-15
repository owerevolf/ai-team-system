"""
Git Intelligence — reads git state for ProjectManager.

Deterministic. Only reads git state, never modifies it.
Uses subprocess to call git commands.
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from core.project_manager.models import GitState
from loguru import logger


class GitIntelligence:
    """Reads and caches git repository state."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self._cache: Optional[GitState] = None
        self._cache_time: float = 0

    def get_state(self, use_cache: bool = True, cache_ttl: float = 5.0) -> GitState:
        """
        Get current git state.

        Args:
            use_cache: Return cached state if fresh enough
            cache_ttl: Cache time-to-live in seconds
        """
        import time
        if use_cache and self._cache and (time.time() - self._cache_time) < cache_ttl:
            return self._cache

        state = GitState()

        if not self._is_git_repo():
            return state

        try:
            state.branch = self._git("rev-parse", "--abbrev-ref", "HEAD").strip()
            state.commit_hash = self._git("rev-parse", "HEAD").strip()[:12]

            # Last commit info
            log_line = self._git("log", "-1", "--format=%H|%s|%an|%ai").strip()
            if "|" in log_line:
                parts = log_line.split("|", 3)
                if len(parts) >= 4:
                    state.commit_hash = parts[0][:12]
                    state.commit_message = parts[1]
                    state.commit_author = parts[2]
                    state.commit_date = parts[3]

            # Changed files
            diff_output = self._git("status", "--porcelain").strip()
            if diff_output:
                state.is_clean = False
                for line in diff_output.split("\n"):
                    line = line.strip()
                    if len(line) >= 3:
                        status = line[:2]
                        filepath = line[3:].strip()
                        if status.startswith("??"):
                            state.untracked_files.append(filepath)
                        elif status.startswith("A") or status.startswith("M") or status.startswith("R") or status.startswith("C"):
                            state.staged_files.append(filepath)
                        else:
                            state.changed_files.append(filepath)

            # Recent commits
            recent = self._git("log", "--oneline", "-10", "--format=%h|%s|%ar").strip()
            if recent:
                for line in recent.split("\n"):
                    parts = line.split("|", 2)
                    if len(parts) >= 3:
                        state.recent_commits.append({
                            "hash": parts[0],
                            "message": parts[1],
                            "relative_date": parts[2],
                        })

        except Exception as e:
            logger.warning(f"Git intelligence error: {e}")

        self._cache = state
        self._cache_time = time.time()
        return state

    def get_changed_files_since(self, ref: str = "HEAD~1") -> List[str]:
        """Get list of files changed since a git ref."""
        try:
            output = self._git("diff", "--name-only", ref).strip()
            if output:
                return output.split("\n")
        except Exception:
            pass
        return []

    def get_file_authors(self, filepath: str) -> List[str]:
        """Get authors who modified a file."""
        try:
            output = self._git("log", "--format=%an", "--", filepath).strip()
            if output:
                authors = list(dict.fromkeys(output.split("\n")))  # unique, preserve order
                return authors[:5]
        except Exception:
            pass
        return []

    def get_file_last_modified(self, filepath: str) -> str:
        """Get last modification date of a file from git."""
        try:
            output = self._git("log", "-1", "--format=%ai", "--", filepath).strip()
            return output
        except Exception:
            return ""

    def get_recently_active_files(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get files modified in the last N days."""
        try:
            output = self._git(
                "log", f"--since={days} days ago",
                "--name-only", "--format=---",
            ).strip()
            if not output:
                return []

            files: Dict[str, int] = {}
            for line in output.split("\n"):
                line = line.strip()
                if line and not line.startswith("---"):
                    files[line] = files.get(line, 0) + 1

            # Sort by change frequency
            sorted_files = sorted(files.items(), key=lambda x: -x[1])
            return [{"path": p, "changes": c} for p, c in sorted_files[:limit]]
        except Exception:
            return []

    def _is_git_repo(self) -> bool:
        """Check if project is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _git(self, *args) -> str:
        """Run a git command and return stdout."""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(self.project_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout
