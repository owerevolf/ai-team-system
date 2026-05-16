"""
Project Sandboxing Module (P16) - AI Team System Phase 8.

Provides a safe execution environment for repo repair and feature development.
All git operations are performed via subprocess with a 30-second timeout.
Protected zones prevent accidental modification of build artifacts, dependency
directories, and sensitive files.

Usage:
    sandbox = ProjectSandbox("/path/to/project")
    checkpoint = sandbox.create_checkpoint("before-refactor")
    branch = sandbox.create_temp_branch("fix")
    # ... make changes ...
    sandbox.safe_write("src/main.py", new_content)
    diff = sandbox.get_diff_since_checkpoint(checkpoint)
    sandbox.cleanup_temp_branch(branch)
    sandbox.rollback(checkpoint)
"""

from __future__ import annotations

import datetime
import fnmatch
import subprocess
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Default protected file/directory patterns
# ---------------------------------------------------------------------------
DEFAULT_PROTECTED_PATTERNS: list[str] = [
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".env",
    "*.lock",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".next",
    ".nuxt",
    "target",
    "vendor",
]


class ProjectSandbox:
    """Safe execution environment wrapping a project directory.

    Wraps common git operations (checkpoint, rollback, temp branches) and
    enforces protected-zone rules so that build artifacts, dependency trees,
    and VCS metadata are never accidentally overwritten.

    Attributes:
        project_path: Absolute path to the managed project directory.
        protected_patterns: Glob-style patterns for paths that must not be
            written to by :meth:`safe_write`.
    """

    def __init__(self, project_path: str) -> None:
        """Initialise the sandbox.

        Args:
            project_path: Path to the project root directory. Created if it
                does not exist yet.
        """
        self.project_path: Path = Path(project_path).resolve()
        self.project_path.mkdir(parents=True, exist_ok=True)
        self.protected_patterns: list[str] = list(DEFAULT_PROTECTED_PATTERNS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_git(
        self,
        *args: str,
        timeout: int = 30,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run a git command inside *project_path*.

        Args:
            *args: Git sub-command and its arguments.
            timeout: Maximum seconds to wait (default 30).
            check: If True, raise on non-zero exit.

        Returns:
            The completed process object.
        """
        cmd = ["git", *args]
        return subprocess.run(
            cmd,
            cwd=str(self.project_path),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )

    def _ensure_git_repo(self) -> None:
        """Initialise a git repo if one does not already exist."""
        git_dir = self.project_path / ".git"
        if not git_dir.is_dir():
            self._run_git("init")
            # Set a default identity so commits don't fail in minimal envs.
            self._run_git("config", "user.email", "sandbox@ai-team.local")
            self._run_git("config", "user.name", "AI Team Sandbox")

    def _resolve_relative(self, file_path: str) -> Path:
        """Return *file_path* resolved relative to *project_path*.

        Args:
            file_path: Relative or absolute path.

        Returns:
            Resolved :class:`Path`.
        """
        p = Path(file_path)
        if p.is_absolute():
            return p
        return (self.project_path / p).resolve()

    # ------------------------------------------------------------------
    # Checkpoint / rollback
    # ------------------------------------------------------------------

    def create_checkpoint(self, label: str = "") -> str:
        """Stage all changes and commit them as a sandbox checkpoint.

        If the project is not inside a git repository one is initialised
        first.  The commit message follows the pattern ``sandbox: {label}``.

        Args:
            label: Human-readable label embedded in the commit message.

        Returns:
            The 40-character commit hash string.

        Raises:
            subprocess.TimeoutExpired: If git does not finish in 30 s.
            RuntimeError: If the commit cannot be created.
        """
        self._ensure_git_repo()
        self._run_git("add", "-A")
        message = f"sandbox: {label}" if label else "sandbox"
        result = self._run_git("commit", "--allow-empty", "-m", message)
        if result.returncode != 0:
            raise RuntimeError(
                f"git commit failed: {result.stderr.strip()}"
            )
        # Retrieve the hash of the commit we just made.
        hash_result = self._run_git("rev-parse", "HEAD")
        return hash_result.stdout.strip()

    def rollback(self, checkpoint_hash: str) -> bool:
        """Hard-reset the working tree to *checkpoint_hash*.

        Args:
            checkpoint_hash: Commit hash to reset to.

        Returns:
            True on success, False on failure.
        """
        try:
            result = self._run_git("reset", "--hard", checkpoint_hash)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False

    # ------------------------------------------------------------------
    # Temporary branches
    # ------------------------------------------------------------------

    def create_temp_branch(self, prefix: str = "sandbox") -> str:
        """Create and check out a temporary branch.

        The branch name is ``{prefix}-{YYYYMMDD-HHMMSS}``.

        Args:
            prefix: Branch-name prefix.

        Returns:
            The new branch name.
        """
        self._ensure_git_repo()
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"{prefix}-{timestamp}"
        self._run_git("checkout", "-b", branch_name)
        return branch_name

    def cleanup_temp_branch(
        self, branch: str, return_to: str = "main"
    ) -> bool:
        """Switch back to *return_to* and delete *branch*.

        Args:
            branch: Temporary branch to remove.
            return_to: Branch to check out before deletion.

        Returns:
            True on success, False on failure.
        """
        try:
            self._run_git("checkout", return_to)
            self._run_git("branch", "-D", branch)
            return True
        except (subprocess.TimeoutExpired, Exception):
            return False

    # ------------------------------------------------------------------
    # Protected zones
    # ------------------------------------------------------------------

    def get_protected_zones(self) -> list[str]:
        """Return the current list of protected glob patterns.

        Returns:
            List of pattern strings.
        """
        return list(self.protected_patterns)

    def is_file_protected(self, file_path: str) -> bool:
        """Check whether *file_path* matches any protected pattern.

        Matching is performed against each path component (directories and
        final filename) so that e.g. ``node_modules/foo/bar.js`` is caught
        even when only the ``node_modules`` component is protected.

        Args:
            file_path: Path to check (relative to project root or absolute).

        Returns:
            True if the path is protected.
        """
        resolved = self._resolve_relative(file_path)
        try:
            relative = resolved.relative_to(self.project_path)
        except ValueError:
            # Absolute path outside project — treat as protected to be safe.
            return True

        parts = relative.parts
        for pattern in self.protected_patterns:
            # Match against any individual path component.
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
            # Also match against the full relative path string.
            if fnmatch.fnmatch(str(relative), pattern):
                return True
        return False

    def safe_write(self, file_path: str, content: str) -> dict:
        """Write *content* to *file_path* only if the path is not protected.

        The file's parent directories are created automatically.

        Args:
            file_path: Destination path (relative to project root or absolute).
            content: Text content to write.

        Returns:
            Dict with keys ``success`` (bool) and ``error`` (str or None).
        """
        if self.is_file_protected(file_path):
            return {
                "success": False,
                "error": f"Path '{file_path}' is in a protected zone.",
            }
        try:
            target = self._resolve_relative(file_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"success": True, "error": None}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Diff / listing
    # ------------------------------------------------------------------

    def get_diff_since_checkpoint(self, checkpoint_hash: str) -> str:
        """Return the git diff between *checkpoint_hash* and the working tree.

        Args:
            checkpoint_hash: Base commit hash.

        Returns:
            Unified diff text, or an empty string on error.
        """
        try:
            result = self._run_git("diff", checkpoint_hash)
            return result.stdout
        except (subprocess.TimeoutExpired, Exception) as exc:
            return f"Error computing diff: {exc}"

    def list_checkpoints(self) -> list[dict]:
        """List all sandbox commits in reverse chronological order.

        Uses ``git log --grep="sandbox:"`` to filter commits created by
        :meth:`create_checkpoint`.

        Returns:
            List of dicts with keys ``hash``, ``message``, and ``date``.
        """
        try:
            result = self._run_git(
                "log",
                "--grep=sandbox:",
                "--format=%H%x00%s%x00%ci%x00",
            )
            if result.returncode != 0 or not result.stdout.strip():
                return []
            entries = []
            # Each record is separated by a null byte triplet + trailing null.
            raw = result.stdout.split("\x00")
            # Iterate in groups of 3 (hash, subject, date, empty).
            for i in range(0, len(raw) - 2, 3):
                h = raw[i].strip()
                msg = raw[i + 1].strip()
                date = raw[i + 2].strip()
                if h:
                    entries.append(
                        {"hash": h, "message": msg, "date": date}
                    )
            return entries
        except (subprocess.TimeoutExpired, Exception):
            return []
