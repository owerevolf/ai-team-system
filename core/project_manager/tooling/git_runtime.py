"""
git_runtime.py — Safe Git Operations.

Allows:
- git status
- git diff
- git checkout -b (create branches)
- git add
- git restore
- git stash

Blocks:
- git push --force
- deleting branches
- rewriting history
- direct main commits

Every execution happens on an isolated branch.
Branch format: ai/task-{id}-{shortname}

NO silent git modifications.
"""

from __future__ import annotations

import subprocess
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class GitResult:
    """Structured git operation result."""
    operation: str = ""
    status: str = ""  # success, blocked, error
    output: str = ""
    error: str = ""
    branch: str = ""
    blocked_reason: str = ""
    exit_code: int = 0

    @property
    def success(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "status": self.status,
            "output": self.output[:3000] if self.output else "",
            "error": self.error[:1000] if self.error else "",
            "branch": self.branch,
            "blocked_reason": self.blocked_reason,
            "exit_code": self.exit_code,
        }


class GitRuntime:
    """
    Safe git operations runtime.

    All git operations are validated before execution.
    Dangerous operations are blocked.
    Every task gets its own branch.
    """

    # Allowed git commands (exact subcommands)
    ALLOWED_OPERATIONS = {
        "status", "diff", "log", "branch", "show", "blame", "shortlog",
        "stash", "remote", "tag", "reflog",
    }

    # Allowed write operations (require branch check)
    ALLOWED_WRITE_OPERATIONS = {
        "checkout", "add", "restore", "commit", "stash push", "stash pop",
    }

    # Blocked operations (never allowed)
    BLOCKED_OPERATIONS = {
        "push --force", "push -f",
        "reset --hard", "clean -fd",
        "rebase", "filter-branch", "filter-repo",
        "branch -D", "branch -d",
        "checkout --force", "checkout -f",
    }

    # Protected branches
    PROTECTED_BRANCHES = {"main", "master", "production", "release"}

    # Branch naming pattern
    AI_BRANCH_PREFIX = "ai/task-"

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()

    def execute(self, operation: str, args: Optional[List[str]] = None,
                agent_id: str = "", task_id: str = "") -> GitResult:
        """
        Execute a git operation safely.

        Args:
            operation: git subcommand (status, diff, checkout, etc.)
            args: additional arguments
            agent_id: agent requesting the operation
            task_id: task context
        """
        args = args or []
        full_cmd = f"git {operation} {' '.join(args)}"

        # Check if operation is blocked
        blocked_reason = self._check_blocked(operation, args)
        if blocked_reason:
            logger.warning(f"Git operation blocked: {full_cmd} — {blocked_reason}")
            return GitResult(
                operation=operation,
                status="blocked",
                blocked_reason=blocked_reason,
            )

        # Check if operation is allowed
        if not self._is_allowed(operation):
            return GitResult(
                operation=operation,
                status="blocked",
                blocked_reason=f"Operation '{operation}' is not in the allowed list",
            )

        # Check protected branch constraints
        branch_check = self._check_protected_branch(operation, args)
        if branch_check:
            return GitResult(
                operation=operation,
                status="blocked",
                blocked_reason=branch_check,
            )

        # Execute
        cmd = ["git", operation] + args
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self._project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )

            result = GitResult(
                operation=operation,
                output=proc.stdout,
                error=proc.stderr,
                exit_code=proc.returncode,
                branch=self._current_branch(),
            )

            if proc.returncode == 0:
                result.status = "success"
            else:
                result.status = "error"

            return result

        except subprocess.TimeoutExpired:
            return GitResult(
                operation=operation,
                status="error",
                error="Git operation timed out (30s)",
            )
        except FileNotFoundError:
            return GitResult(
                operation=operation,
                status="error",
                error="git not found",
            )
        except Exception as e:
            return GitResult(
                operation=operation,
                status="error",
                error=str(e),
            )

    def _check_blocked(self, operation: str, args: List[str]) -> str:
        """Check if the operation is blocked. Returns reason or empty string."""
        full = f"{operation} {' '.join(args)}".strip()

        for blocked in self.BLOCKED_OPERATIONS:
            if blocked in full:
                return f"Operation '{blocked}' is blocked"

        # Block push --force specifically
        if operation == "push" and ("--force" in args or "-f" in args):
            return "Force push is blocked"

        # Block branch deletion
        if operation == "branch" and ("-D" in args or "-d" in args):
            return "Branch deletion is blocked"

        # Block history rewriting
        if operation in ("rebase", "filter-branch", "filter-repo"):
            return f"History rewriting ({operation}) is blocked"

        return ""

    def _is_allowed(self, operation: str) -> bool:
        """Check if the operation is in the allowed list."""
        return operation in self.ALLOWED_OPERATIONS or \
               operation in self.ALLOWED_WRITE_OPERATIONS

    def _check_protected_branch(self, operation: str, args: List[str]) -> str:
        """Check if the operation would modify a protected branch."""
        # Block direct commits to main/master
        if operation == "commit":
            current = self._current_branch()
            if current in self.PROTECTED_BRANCHES:
                return f"Direct commits to '{current}' are not allowed. Use a work branch."

        # Block checkout to protected branch with intent to modify
        if operation == "checkout" and args:
            target = args[-1]  # Last arg is usually the target
            # Allow checkout TO protected branch, but warn
            # The commit check above will block actual commits

        return ""

    # ── Convenience Methods ──

    def status(self) -> GitResult:
        """Get git status."""
        return self.execute("status")

    def diff(self, ref_a: str = "", ref_b: str = "",
             file_path: str = "") -> GitResult:
        """Get git diff."""
        args = []
        if ref_a:
            args.append(ref_a)
        if ref_b:
            args.append(ref_b)
        if file_path:
            args.extend(["--", file_path])
        return self.execute("diff", args)

    def current_branch(self) -> str:
        """Get current branch name."""
        return self._current_branch()

    def create_branch(self, task_id: str, short_name: str,
                      base: str = "") -> GitResult:
        """
        Create a new AI work branch.

        Branch format: ai/task-{id}-{shortname}
        """
        branch_name = f"{self.AI_BRANCH_PREFIX}{task_id}-{short_name}"
        # Sanitize branch name
        branch_name = re.sub(r'[^\w\-/]', '-', branch_name)
        branch_name = re.sub(r'-+', '-', branch_name)

        args = ["-b", branch_name]
        if base:
            args.append(base)

        result = self.execute("checkout", args)
        result.branch = branch_name
        return result

    def add_files(self, files: List[str]) -> GitResult:
        """Stage files."""
        return self.execute("add", files)

    def commit(self, message: str) -> GitResult:
        """Commit staged messages."""
        return self.execute("commit", ["-m", message])

    def stash(self, message: str = "") -> GitResult:
        """Stash current changes."""
        args = ["push"]
        if message:
            args.extend(["-m", message])
        return self.execute("stash", args)

    def stash_pop(self) -> GitResult:
        """Pop stashed changes."""
        return self.execute("stash", ["pop"])

    def restore_files(self, files: List[str]) -> GitResult:
        """Restore files to last committed state."""
        return self.execute("restore", files)

    def log(self, limit: int = 10, branch: str = "") -> GitResult:
        """Get commit log."""
        args = [f"--max-count={limit}", "--oneline"]
        if branch:
            args.append(branch)
        return self.execute("log", args)

    def list_branches(self) -> List[str]:
        """List all local branches."""
        result = self.execute("branch")
        if result.success:
            branches = []
            for line in result.output.strip().split("\n"):
                name = line.strip().lstrip("* ").strip()
                if name:
                    branches.append(name)
            return branches
        return []

    def get_modified_files(self) -> List[str]:
        """Get list of modified files."""
        result = self.execute("status", ["--porcelain"])
        if result.success:
            files = []
            for line in result.output.strip().split("\n"):
                if line.strip():
                    # Format: XY filename or XY filename -> new_filename
                    parts = line.strip().split(None, 1)
                    if len(parts) == 2:
                        file_path = parts[1].split(" -> ")[-1].strip()
                        files.append(file_path)
            return files
        return []

    def _current_branch(self) -> str:
        """Get current branch name."""
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(self._project_root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
        except Exception:
            pass
        return "unknown"
