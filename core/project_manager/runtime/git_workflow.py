"""
P2 — Git Workflow Integration.

Full git lifecycle integration:
- Branch-aware execution
- PR generation
- Commit grouping
- Semantic commit analysis
- Diff summaries
- Merge safety checks
- Rollback branches
- Branch divergence detection
- Stale branch detection
- Conflicting changeset detection
"""

import subprocess
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class BranchType(Enum):
    MAIN = "main"
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    HOTFIX = "hotfix"
    RELEASE = "release"
    UNKNOWN = "unknown"


class CommitType(Enum):
    FEAT = "feat"
    FIX = "fix"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    CHORE = "chore"
    PERF = "perf"
    STYLE = "style"
    CI = "ci"
    UNKNOWN = "unknown"


@dataclass
class BranchInfo:
    """Information about a git branch."""
    name: str
    branch_type: BranchType
    is_active: bool
    ahead: int = 0  # commits ahead of remote
    behind: int = 0  # commits behind remote
    last_commit: str = ""
    last_commit_msg: str = ""
    last_commit_date: str = ""
    is_stale: bool = False  # no commits in 30 days
    diverged: bool = False  # diverged from remote


@dataclass
class CommitInfo:
    """Parsed commit information."""
    hash: str
    short_hash: str
    message: str
    commit_type: CommitType
    scope: str = ""
    subject: str = ""
    body: str = ""
    author: str = ""
    date: str = ""
    files_changed: List[str] = field(default_factory=list)
    is_breaking: bool = False


@dataclass
class DiffSummary:
    """Summary of changes."""
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    files: List[str] = field(default_factory=list)
    has_tests: bool = False
    has_config: bool = False
    has_docs: bool = False
    risk_indicators: List[str] = field(default_factory=list)


@dataclass
class MergeSafety:
    """Merge safety assessment."""
    is_safe: bool = True
    conflicts: List[str] = field(default_factory=list)
    risk_level: str = "low"
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class GitWorkflowIntegration:
    """
    Full git workflow integration for the platform.
    Branch-aware, PR-ready, merge-safe.
    """

    # Conventional commit pattern
    COMMIT_PATTERN = re.compile(
        r'^(?P<type>feat|fix|refactor|docs|test|chore|perf|style|ci)'
        r'(?:\((?P<scope>[^)]+)\))?'
        r'(?P<breaking>!)?:\s*(?P<subject>.+)$'
    )

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()

    # ── Branch Operations ──

    def get_branch_info(self, branch: str = "") -> BranchInfo:
        """Get detailed information about a branch."""
        if not branch:
            branch = self._current_branch()

        info = BranchInfo(
            name=branch,
            branch_type=self._classify_branch(branch),
            is_active=(branch == self._current_branch()),
        )

        # Last commit
        result = self._git("log", "-1", "--format=%H|%s|%an|%ai", branch)
        if result:
            parts = result.split("|", 3)
            if len(parts) >= 4:
                info.last_commit = parts[0][:12]
                info.last_commit_msg = parts[1]
                info.last_commit_date = parts[3]

        # Ahead/behind
        ahead_behind = self._git("rev-list", "--left-right", "--count",
                                  f"{branch}...origin/{branch}")
        if ahead_behind:
            parts = ahead_behind.split()
            if len(parts) == 2:
                info.behind = int(parts[0])
                info.ahead = int(parts[1])

        # Stale check (no commits in 30 days)
        if info.last_commit_date:
            try:
                from datetime import datetime
                commit_date = datetime.fromisoformat(info.last_commit_date.strip())
                days_old = (datetime.now() - commit_date).days
                info.is_stale = days_old > 30
            except (ValueError, TypeError):
                pass

        # Diverged check
        info.diverged = info.ahead > 0 and info.behind > 0

        return info

    def list_branches(self, include_remote: bool = False) -> List[BranchInfo]:
        """List all branches with info."""
        branches = []
        result = self._git("branch", "-a" if include_remote else "")
        if not result:
            return branches

        for line in result.strip().split("\n"):
            name = line.strip().lstrip("* ").strip()
            if not name or "HEAD" in name:
                continue
            if not include_remote and name.startswith("remotes/"):
                continue
            branches.append(self.get_branch_info(name))

        return branches

    def create_work_branch(self, branch_type: BranchType, name: str,
                           base: str = "main") -> Tuple[bool, str]:
        """Create a properly named work branch."""
        prefix = {
            BranchType.FEATURE: "feature",
            BranchType.BUGFIX: "bugfix",
            BranchType.REFACTOR: "refactor",
            BranchType.HOTFIX: "hotfix",
            BranchType.RELEASE: "release",
        }.get(branch_type, "work")

        branch_name = f"{prefix}/{name}"

        # Checkout base first
        self._git("checkout", base)
        # Create and checkout new branch
        result = self._git("checkout", "-b", branch_name)
        return (result is not None and "error" not in result.lower()), branch_name

    def _classify_branch(self, name: str) -> BranchType:
        """Classify a branch by its name."""
        if name in ("main", "master"):
            return BranchType.MAIN
        if name.startswith("feature/") or name.startswith("feat/"):
            return BranchType.FEATURE
        if name.startswith("bugfix/") or name.startswith("fix/"):
            return BranchType.BUGFIX
        if name.startswith("refactor/"):
            return BranchType.REFACTOR
        if name.startswith("hotfix/"):
            return BranchType.HOTFIX
        if name.startswith("release/"):
            return BranchType.RELEASE
        return BranchType.UNKNOWN

    # ── Commit Operations ──

    def parse_commit(self, message: str) -> CommitInfo:
        """Parse a conventional commit message."""
        info = CommitInfo(
            hash="",
            short_hash="",
            message=message,
            commit_type=CommitType.UNKNOWN,
            subject=message,
        )

        match = self.COMMIT_PATTERN.match(message.strip())
        if match:
            type_str = match.group("type")
            info.commit_type = CommitType(type_str) if type_str in [t.value for t in CommitType] else CommitType.UNKNOWN
            info.scope = match.group("scope") or ""
            info.subject = match.group("subject") or ""
            info.is_breaking = match.group("breaking") == "!"

        return info

    def get_commits(self, branch: str = "", limit: int = 20,
                    since: str = "") -> List[CommitInfo]:
        """Get parsed commit history."""
        args = ["log", "--format=%H|%s|%an|%ai"]
        if limit > 0:
            args.extend(["-n", str(limit)])
        if since:
            args.extend([f"--since={since}"])
        if branch:
            args.append(branch)

        result = self._git(*args)
        if not result:
            return []

        commits = []
        for line in result.strip().split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) >= 4:
                parsed = self.parse_commit(parts[1])
                parsed.hash = parts[0]
                parsed.short_hash = parts[0][:8]
                parsed.author = parts[2]
                parsed.date = parts[3]
                commits.append(parsed)

        return commits

    def group_commits_by_type(self, commits: List[CommitInfo]) -> Dict[str, List[CommitInfo]]:
        """Group commits by their type."""
        groups: Dict[str, List[CommitInfo]] = {}
        for commit in commits:
            key = commit.commit_type.value
            if key not in groups:
                groups[key] = []
            groups[key].append(commit)
        return groups

    def generate_commit_message(self, files_changed: List[str],
                                 diff_summary: DiffSummary) -> str:
        """Generate a semantic commit message from changes."""
        # Determine commit type from files
        if any(f.startswith("test") or f.startswith("tests") for f in files_changed):
            commit_type = CommitType.TEST
        elif any(f.endswith((".md", ".rst", ".txt")) for f in files_changed):
            commit_type = CommitType.DOCS
        elif any("config" in f.lower() or f.endswith((".yaml", ".yml", ".toml")) for f in files_changed):
            commit_type = CommitType.CHORE
        else:
            commit_type = CommitType.FEAT

        # Determine scope from common path prefix
        scope = self._detect_scope(files_changed)

        # Build message
        scope_str = f"({scope})" if scope else ""
        file_list = ", ".join(files_changed[:5])
        if len(files_changed) > 5:
            file_list += f" and {len(files_changed) - 5} more"

        return f"{commit_type.value}{scope_str}: update {file_list}"

    def _detect_scope(self, files: List[str]) -> str:
        """Detect the common scope from a list of files."""
        if not files:
            return ""
        parts = [f.split("/")[0] for f in files if "/" in f]
        if parts:
            from collections import Counter
            most_common = Counter(parts).most_common(1)
            if most_common:
                return most_common[0][0]
        return ""

    # ── Diff & Summary ──

    def get_diff_summary(self, ref_a: str = "HEAD~1",
                         ref_b: str = "HEAD") -> DiffSummary:
        """Get a summary of changes between two refs."""
        summary = DiffSummary()

        # File list
        files = self._git("diff", "--name-only", ref_a, ref_b)
        if files:
            summary.files = [f for f in files.strip().split("\n") if f]
            summary.files_changed = len(summary.files)

        # Stats
        stats = self._git("diff", "--shortstat", ref_a, ref_b)
        if stats:
            insertions = re.search(r'(\d+) insertion', stats)
            deletions = re.search(r'(\d+) deletion', stats)
            if insertions:
                summary.insertions = int(insertions.group(1))
            if deletions:
                summary.deletions = int(deletions.group(1))

        # Risk indicators
        for f in summary.files:
            if "test" in f:
                summary.has_tests = True
            if "config" in f.lower() or f.endswith((".yaml", ".yml", ".toml", ".env")):
                summary.has_config = True
            if f.endswith((".md", ".rst")):
                summary.has_docs = True

        # Risk indicators
        if summary.files_changed > 20:
            summary.risk_indicators.append("Large number of files changed")
        if summary.insertions > 500:
            summary.risk_indicators.append("Large insertion size")
        if not summary.has_tests and summary.files_changed > 5:
            summary.risk_indicators.append("No test files in changes")
        if summary.has_config:
            summary.risk_indicators.append("Configuration files modified")

        return summary

    # ── Merge Safety ──

    def check_merge_safety(self, source: str, target: str = "main") -> MergeSafety:
        """Check if merging source into target is safe."""
        safety = MergeSafety()

        # Check for conflicts
        # First, try a dry-run merge
        self._git("checkout", target)
        merge_result = self._git("merge", "--no-commit", "--no-ff", source)

        if merge_result is None or "conflict" in merge_result.lower():
            safety.is_safe = False
            safety.risk_level = "high"
            # Get conflict list
            conflicts = self._git("diff", "--name-only", "--diff-filter=U")
            if conflicts:
                safety.conflicts = [f for f in conflicts.strip().split("\n") if f]
            safety.warnings.append(f"Merge conflicts in: {', '.join(safety.conflicts[:5])}")
            # Abort the merge
            self._git("merge", "--abort")
        else:
            # Clean up — reset to pre-merge state
            self._git("reset", "--hard", "HEAD")

        # Check branch divergence
        source_info = self.get_branch_info(source)
        if source_info.diverged:
            safety.warnings.append("Branch has diverged from remote — rebase recommended")
            safety.risk_level = "medium"

        if source_info.is_stale:
            safety.warnings.append("Branch is stale (no commits in 30+ days)")

        # Recommendations
        if safety.is_safe and source_info.ahead > 10:
            safety.recommendations.append("Consider squashing commits before merge")
        if not safety.is_safe:
            safety.recommendations.append("Resolve conflicts manually before merging")
            safety.recommendations.append("Run full validation after conflict resolution")

        return safety

    # ── PR Generation ──

    def generate_pr_description(self, branch: str,
                                 commits: List[CommitInfo] = None) -> str:
        """Generate a PR description from branch and commits."""
        if commits is None:
            commits = self.get_commits(branch)

        branch_info = self.get_branch_info(branch)
        groups = self.group_commits_by_type(commits)

        lines = [
            "## Summary",
            "",
            f"Branch: `{branch}`",
            f"Type: {branch_info.branch_type.value}",
            f"Commits: {len(commits)}",
            "",
        ]

        # Group commits by type
        type_labels = {
            "feat": "Features",
            "fix": "Bug Fixes",
            "refactor": "Refactoring",
            "docs": "Documentation",
            "test": "Tests",
            "chore": "Chores",
            "perf": "Performance",
        }

        for type_name, label in type_labels.items():
            if type_name in groups:
                lines.append(f"### {label}")
                for commit in groups[type_name]:
                    scope = f"**{commit.scope}**: " if commit.scope else ""
                    breaking = " [BREAKING]" if commit.is_breaking else ""
                    lines.append(f"- {scope}{commit.subject}{breaking}")
                lines.append("")

        # Risk indicators
        if branch_info.diverged:
            lines.append("⚠️ Branch has diverged from remote — rebase recommended")
        if branch_info.is_stale:
            lines.append("⚠️ Branch is stale")

        return "\n".join(lines)

    # ── Rollback ──

    def create_rollback_branch(self, from_ref: str,
                                reason: str = "") -> Tuple[bool, str]:
        """Create a rollback branch from a specific ref."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        branch_name = f"rollback/{timestamp}"
        if reason:
            safe_reason = re.sub(r'[^\w\-]', '_', reason[:30])
            branch_name += f"_{safe_reason}"

        self._git("branch", branch_name, from_ref)
        return True, branch_name

    # ── Low-level git ──

    def _git(self, *args) -> Optional[str]:
        """Run a git command and return stdout."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None

    def _current_branch(self) -> str:
        """Get the current branch name."""
        result = self._git("rev-parse", "--abbrev-ref", "HEAD")
        return result.strip() if result else "unknown"
