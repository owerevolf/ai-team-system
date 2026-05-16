"""
Patch Review UX Module (P10)
============================

Generates structured review information for git diffs/patches.
Provides risk assessment, rollback planning, and human-readable
summaries suitable for browser display.

Risk Heuristics (deterministic):
  - High:   >10 files changed, OR entry point changed, OR config changed, OR >200 lines
  - Medium: 3-10 files, OR 50-200 lines, OR test files changed
  - Low:    <3 files, <50 lines, no entry points
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# File patterns considered "entry points" for risk assessment
ENTRY_POINT_PATTERNS = [
    re.compile(r"main\.(py|js|ts|go|rs|java)$"),
    re.compile(r"app\.(py|js|ts|go|rs|java)$"),
    re.compile(r"index\.(py|js|ts)$"),
    re.compile(r"server\.(py|js|ts|go)$"),
    re.compile(r"manage\.py$"),
    re.compile(r"wsgi\.py$"),
    re.compile(r"asgi\.py$"),
    re.compile(r"__main__\.py$"),
    re.compile(r"__init__\.py$"),
    re.compile(r"cli\.(py|js|ts|go)$"),
    re.compile(r"setup\.py$"),
    re.compile(r"setup\.cfg$"),
]

# File patterns considered "config files"
CONFIG_PATTERNS = [
    re.compile(r"\.env(\..+)?$"),
    re.compile(r"config\.(py|js|ts|json|yaml|yml|toml|ini|cfg|conf)$"),
    re.compile(r"settings\.(py|js|ts|json|yaml|yml)$"),
    re.compile(r"(pyproject|package|composer|Makefile|Dockerfile|docker-compose)\.(.*)$"),
    re.compile(r"\.ya?ml$"),
    re.compile(r"\.toml$"),
    re.compile(r"\.ini$"),
    re.compile(r"\.cfg$"),
    re.compile(r"\.conf$"),
    re.compile(r"\.json$"),
    re.compile(r"requirements.*\.txt$"),
    re.compile(r"\.lock$"),
    re.compile(r"tsconfig.*\.json$"),
    re.compile(r"webpack\.(.*)\.js$"),
    re.compile(r"vite\.(.*)\.(js|ts)$"),
    re.compile(r"babel\.(.*)\.(js|json)$"),
    re.compile(r"\.eslintrc(.*)$"),
    re.compile(r"\.prettierrc(.*)$"),
]

# File patterns considered "test files"
TEST_PATTERNS = [
    re.compile(r"test_.*\.py$"),
    re.compile(r".*_test\.(py|js|ts|go|rs|java)$"),
    re.compile(r".*\.test\.(js|ts)$"),
    re.compile(r".*\.spec\.(js|ts|py)$"),
    re.compile(r"tests?/"),
    re.compile(r"__tests__/"),
]

# Validation checks that may be affected by file changes
VALIDATION_CHECKS = {
    "lint": {"patterns": [re.compile(r"\.(py|js|ts|go|rs|java|rb|cpp|c|h)$")], "description": "Linting"},
    "type_check": {"patterns": [re.compile(r"\.(ts|py)$")], "description": "Type checking"},
    "unit_tests": {"patterns": TEST_PATTERNS, "description": "Unit tests"},
    "integration_tests": {"patterns": [re.compile(r"integration"), re.compile(r"e2e")], "description": "Integration tests"},
    "build": {"patterns": [re.compile(r"\.(ts|js|go|rs|java|cpp|c)$")], "description": "Build"},
    "security_scan": {"patterns": [re.compile(r"\.(py|js|ts|go|rs|java)$"), re.compile(r"config"), re.compile(r"\.env")], "description": "Security scan"},
    "dependency_check": {"patterns": [re.compile(r"(requirements|package|pyproject|go\.mod|Cargo\.toml|Gemfile)")], "description": "Dependency check"},
    "config_validation": {"patterns": CONFIG_PATTERNS, "description": "Config validation"},
}


# ---------------------------------------------------------------------------
# Helper: parse a unified diff
# ---------------------------------------------------------------------------

def _parse_diff_files(diff_text: str) -> list[str]:
    """Extract changed file paths from a unified diff."""
    files: list[str] = []
    for line in diff_text.splitlines():
        # Match both "diff --git a/path b/path" and "--- a/path" / "+++ b/path"
        m = re.match(r"^diff --git a/(.+?) b/(.+)$", line)
        if m:
            files.append(m.group(2))
            continue
        m = re.match(r"^\+\+\+ b/(.+)$", line)
        if m and m.group(1) not in files:
            files.append(m.group(1))
    return files


def _count_diff_lines(diff_text: str) -> tuple[int, int]:
    """Count added and deleted lines in a unified diff (excluding diff headers)."""
    added = 0
    deleted = 0
    for line in diff_text.splitlines():
        # Skip diff metadata lines
        if line.startswith("diff --git") or line.startswith("--- ") or line.startswith("+++ "):
            continue
        if line.startswith("@@") or line.startswith("index ") or line.startswith("new file") or line.startswith("deleted file"):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    return added, deleted


def _is_entry_point(file_path: str) -> bool:
    """Check if a file is an entry point."""
    basename = Path(file_path).name
    return any(p.search(basename) for p in ENTRY_POINT_PATTERNS)


def _is_config_file(file_path: str) -> bool:
    """Check if a file is a config file."""
    basename = Path(file_path).name
    return any(p.search(basename) for p in CONFIG_PATTERNS)


def _is_test_file(file_path: str) -> bool:
    """Check if a file is a test file."""
    return any(p.search(file_path) for p in TEST_PATTERNS)


def _extract_modules(file_paths: list[str]) -> list[str]:
    """Extract unique top-level module/directory names from file paths."""
    modules: set[str] = set()
    for fp in file_paths:
        parts = Path(fp).parts
        if parts:
            modules.add(parts[0])
    return sorted(modules)


def _determine_validation_impact(file_paths: list[str]) -> list[dict[str, str]]:
    """Determine which validation checks are affected by the changed files."""
    impacted: list[dict[str, str]] = []
    seen: set[str] = set()
    for check_name, check_info in VALIDATION_CHECKS.items():
        for fp in file_paths:
            for pattern in check_info["patterns"]:
                if pattern.search(fp) and check_name not in seen:
                    impacted.append({"check": check_name, "description": check_info["description"]})
                    seen.add(check_name)
                    break
    return impacted


def _get_git_head(project_path: str) -> str:
    """Get the current git HEAD hash, or 'unknown' if not available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return "unknown"


def _compute_risk_score(
    num_files: int,
    lines_added: int,
    lines_deleted: int,
    has_entry_point: bool,
    has_config: bool,
    has_tests: bool,
) -> float:
    """
    Compute a risk score from 0.0 (safe) to 1.0 (dangerous).

    Weighted factors:
      - File count:       up to 0.25
      - Line volume:      up to 0.25
      - Entry point:      0.20 if present
      - Config change:    0.20 if present
      - Test change:      0.10 if present
    """
    score = 0.0

    # File count contribution (saturates at 15 files)
    score += min(num_files / 15.0, 1.0) * 0.25

    # Line volume contribution (saturates at 300 total lines)
    total_lines = lines_added + lines_deleted
    score += min(total_lines / 300.0, 1.0) * 0.25

    # Binary flags
    if has_entry_point:
        score += 0.20
    if has_config:
        score += 0.20
    if has_tests:
        score += 0.10

    return round(min(score, 1.0), 3)


def _compute_confidence_score(
    num_files: int,
    lines_added: int,
    lines_deleted: int,
    has_entry_point: bool,
    has_config: bool,
) -> float:
    """
    Compute a confidence score from 0.0 (low confidence / risky) to 1.0 (high confidence / safe).

    Inverse of risk: smaller, focused patches get higher confidence.
    """
    score = 1.0

    # Penalize large file counts
    score -= min(num_files / 20.0, 0.4)

    # Penalize large line counts
    total_lines = lines_added + lines_deleted
    score -= min(total_lines / 500.0, 0.3)

    # Penalize sensitive changes
    if has_entry_point:
        score -= 0.15
    if has_config:
        score -= 0.15

    return round(max(score, 0.0), 3)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PatchReview:
    """
    Generates structured review information for git diffs.

    Usage:
        reviewer = PatchReview()
        review = reviewer.generate_review(diff_text, "/path/to/project")
        print(reviewer.format_review_for_display(review))
    """

    def generate_review(self, diff_text: str, project_path: str) -> dict[str, Any]:
        """
        Analyse a git diff and return a structured review.

        Args:
            diff_text:  The raw git diff output (unified diff format).
            project_path: Absolute path to the project root (used for git commands).

        Returns:
            dict with keys:
                files_changed, lines_added, lines_deleted, risk_level,
                risk_score, affected_modules, validation_impact,
                rollback_plan, confidence_score, summary
        """
        files_changed = _parse_diff_files(diff_text)
        lines_added, lines_deleted = _count_diff_lines(diff_text)
        num_files = len(files_changed)

        has_entry_point = any(_is_entry_point(f) for f in files_changed)
        has_config = any(_is_config_file(f) for f in files_changed)
        has_tests = any(_is_test_file(f) in files_changed for f in [True] if False) or any(_is_test_file(f) for f in files_changed)

        # Determine risk level
        total_lines = lines_added + lines_deleted
        if num_files > 10 or has_entry_point or has_config or total_lines > 200:
            risk_level = "high"
        elif 3 <= num_files <= 10 or 50 <= total_lines <= 200 or has_tests:
            risk_level = "medium"
        else:
            risk_level = "low"

        risk_score = _compute_risk_score(num_files, lines_added, lines_deleted, has_entry_point, has_config, has_tests)
        confidence_score = _compute_confidence_score(num_files, lines_added, lines_deleted, has_entry_point, has_config)
        affected_modules = _extract_modules(files_changed)
        validation_impact = _determine_validation_impact(files_changed)

        # Rollback plan
        head_hash = _get_git_head(project_path)
        rollback_plan = {
            "type": "git_reset",
            "command": f"git reset --hard {head_hash}",
            "description": f"Reset to current HEAD ({head_hash}) to undo all changes in this patch.",
        }

        # Summary
        summary = (
            f"Patch modifies {num_files} file{'s' if num_files != 1 else ''} "
            f"(+{lines_added}/-{lines_deleted} lines) across {len(affected_modules)} module{'s' if len(affected_modules) != 1 else ''} "
            f"— {risk_level.upper()} risk"
        )

        return {
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "affected_modules": affected_modules,
            "validation_impact": validation_impact,
            "rollback_plan": rollback_plan,
            "confidence_score": confidence_score,
            "summary": summary,
        }

    def format_review_for_display(self, review: dict[str, Any]) -> str:
        """
        Format a review dict as a human-readable string for browser/terminal display.

        Args:
            review: The dict returned by generate_review().

        Returns:
            A formatted multi-line string.
        """
        lines: list[str] = []
        sep = "=" * 60

        lines.append(sep)
        lines.append("  PATCH REVIEW REPORT")
        lines.append(sep)
        lines.append("")

        # Summary
        lines.append(f"  Summary: {review['summary']}")
        lines.append("")

        # Risk
        risk_level = review["risk_level"].upper()
        risk_score = review["risk_score"]
        confidence = review["confidence_score"]
        lines.append(f"  Risk Level:    {risk_level}")
        lines.append(f"  Risk Score:    {risk_score:.3f}  (0.0=safe, 1.0=dangerous)")
        lines.append(f"  Confidence:    {confidence:.3f}  (0.0=low, 1.0=high)")
        lines.append("")

        # File stats
        lines.append(f"  Files Changed: {len(review['files_changed'])}")
        lines.append(f"  Lines Added:   {review['lines_added']}")
        lines.append(f"  Lines Deleted: {review['lines_deleted']}")
        lines.append("")

        # Changed files
        if review["files_changed"]:
            lines.append("  Changed Files:")
            for f in review["files_changed"]:
                lines.append(f"    - {f}")
            lines.append("")

        # Affected modules
        if review["affected_modules"]:
            lines.append(f"  Affected Modules: {', '.join(review['affected_modules'])}")
            lines.append("")

        # Validation impact
        if review["validation_impact"]:
            lines.append("  Validation Checks Affected:")
            for item in review["validation_impact"]:
                lines.append(f"    - {item['description']} ({item['check']})")
            lines.append("")

        # Rollback plan
        rollback = review["rollback_plan"]
        lines.append("  Rollback Plan:")
        lines.append(f"    Type:        {rollback['type']}")
        lines.append(f"    Command:     {rollback['command']}")
        lines.append(f"    Description: {rollback['description']}")
        lines.append("")

        lines.append(sep)
        return "\n".join(lines)

    def compare_patches(self, old_diff: str, new_diff: str) -> dict[str, Any]:
        """
        Compare two patches and show what changed between them.

        Args:
            old_diff: The original git diff.
            new_diff: The updated git diff.

        Returns:
            dict with comparison results:
                files_only_in_old, files_only_in_new, files_in_both,
                old_lines_added, old_lines_deleted, new_lines_added, new_lines_deleted,
                line_delta_added, line_delta_deleted, summary
        """
        old_files = set(_parse_diff_files(old_diff))
        new_files = set(_parse_diff_files(new_diff))
        old_added, old_deleted = _count_diff_lines(old_diff)
        new_added, new_deleted = _count_diff_lines(new_diff)

        only_old = sorted(old_files - new_files)
        only_new = sorted(new_files - old_files)
        both = sorted(old_files & new_files)

        summary_parts: list[str] = []
        if only_new:
            summary_parts.append(f"{len(only_new)} new file{'s' if len(only_new) != 1 else ''} added")
        if only_old:
            summary_parts.append(f"{len(only_old)} file{'s' if len(only_old) != 1 else ''} removed")
        delta_add = new_added - old_added
        delta_del = new_deleted - old_deleted
        if delta_add != 0 or delta_del != 0:
            summary_parts.append(f"line delta: {'+' if delta_add >= 0 else ''}{delta_add}/{'+' if delta_del >= 0 else ''}{delta_del}")
        if not summary_parts:
            summary_parts.append("no changes between patches")

        return {
            "files_only_in_old": only_old,
            "files_only_in_new": only_new,
            "files_in_both": both,
            "old_lines_added": old_added,
            "old_lines_deleted": old_deleted,
            "new_lines_added": new_added,
            "new_lines_deleted": new_deleted,
            "line_delta_added": delta_add,
            "line_delta_deleted": delta_del,
            "summary": "Comparison: " + "; ".join(summary_parts),
        }
