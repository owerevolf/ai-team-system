"""
Patch Engine — the core of controlled execution.

NO direct file writes. ONLY patches.
Every change goes through: generate → validate → review → approve → apply.
"""

from __future__ import annotations

import difflib
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PatchStatus(Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class RiskLevel(Enum):
    LOW = "low"        # comments, docs, formatting
    MEDIUM = "medium"  # feature logic, refactors
    HIGH = "high"      # architecture, auth, database
    CRITICAL = "critical"  # security, core infrastructure


@dataclass
class FilePatch:
    """A patch for a single file."""
    file_path: str = ""
    original_content: str = ""
    new_content: str = ""
    diff: str = ""
    lines_added: int = 0
    lines_removed: int = 0
    is_new_file: bool = False
    is_deletion: bool = False


@dataclass
class Patch:
    """
    The main unit of change.

    No raw file edits. Only patches.
    """
    patch_id: str = ""
    task_id: str = ""
    plan_id: str = ""
    created_by: str = ""  # agent_id
    summary: str = ""
    status: str = PatchStatus.DRAFT.value
    risk_level: str = RiskLevel.MEDIUM.value
    created_at: str = ""
    applied_at: str = ""

    # Files
    files: List[FilePatch] = field(default_factory=list)

    # Validation
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)

    # Review
    approved: bool = False
    approved_by: str = ""
    review_comments: str = ""

    # Rollback
    rollback_patch_id: str = ""
    can_rollback: bool = True

    def __post_init__(self):
        if not self.patch_id:
            self.patch_id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_lines_added(self) -> int:
        return sum(f.lines_added for f in self.files)

    @property
    def total_lines_removed(self) -> int:
        return sum(f.lines_removed for f in self.files)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "task_id": self.task_id,
            "summary": self.summary,
            "status": self.status,
            "risk_level": self.risk_level,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "total_files": self.total_files,
            "total_lines_added": self.total_lines_added,
            "total_lines_removed": self.total_lines_removed,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "approved": self.approved,
            "can_rollback": self.can_rollback,
            "files": [
                {
                    "file_path": f.file_path,
                    "lines_added": f.lines_added,
                    "lines_removed": f.lines_removed,
                    "is_new_file": f.is_new_file,
                    "diff": f.diff,
                }
                for f in self.files
            ],
        }


class PatchEngine:
    """
    Generates, validates, applies, and rolls back patches.

    This is the ONLY way to modify files in the system.
    No direct writes. Ever.
    """

    def __init__(self, project_root: str = "."):
        self._project_root = project_root
        self._patches: Dict[str, Patch] = {}
        self._applied_patches: List[str] = []

    def generate_patch(self, task_id: str, file_changes: Dict[str, str],
                       created_by: str = "", summary: str = "",
                       plan_id: str = "") -> Patch:
        """
        Generate a patch from file changes.

        Args:
            task_id: the task this patch belongs to
            file_changes: dict of {file_path: new_content}
            created_by: agent that created the patch
            summary: human-readable summary
            plan_id: execution plan ID

        Returns:
            Patch object with diffs
        """
        patch = Patch(
            task_id=task_id,
            plan_id=plan_id,
            created_by=created_by,
            summary=summary or f"Patch for task {task_id}",
        )

        for file_path, new_content in file_changes.items():
            original = self._read_file(file_path)
            diff = self._compute_diff(file_path, original, new_content)

            file_patch = FilePatch(
                file_path=file_path,
                original_content=original,
                new_content=new_content,
                diff=diff,
                lines_added=max(0, new_content.count('\n') - original.count('\n')),
                lines_removed=max(0, original.count('\n') - new_content.count('\n')),
                is_new_file=(original == "" and new_content != ""),
                is_deletion=(original != "" and new_content == ""),
            )
            patch.files.append(file_patch)

        # Assess risk
        patch.risk_level = self._assess_risk(patch).value

        self._patches[patch.patch_id] = patch
        return patch

    def validate_patch(self, patch: Patch,
                       forbidden_files: Optional[List[str]] = None,
                       max_files: int = 10,
                       max_lines: int = 500) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a patch before it can be approved.

        Returns: (passed, errors, warnings)
        """
        errors = []
        warnings = []
        forbidden_files = forbidden_files or []

        # Check file count
        if patch.total_files > max_files:
            errors.append(f"Too many files: {patch.total_files} > {max_files}")

        # Check line count
        total_changes = patch.total_lines_added + patch.total_lines_removed
        if total_changes > max_lines:
            errors.append(f"Too many line changes: {total_changes} > {max_lines}")

        # Check forbidden files
        for f in patch.files:
            if f.file_path in forbidden_files:
                errors.append(f"Forbidden file: {f.file_path}")

        # Check for dangerous patterns
        dangerous_patterns = [
            "rm -rf", "os.remove(", "shutil.rmtree",
            "DROP TABLE", "DELETE FROM", "exec(", "eval(",
            "subprocess.call", "os.system",
        ]
        for f in patch.files:
            for pattern in dangerous_patterns:
                if pattern in f.new_content:
                    errors.append(f"Dangerous pattern '{pattern}' in {f.file_path}")

        # Check for syntax errors (basic)
        for f in patch.files:
            if f.file_path.endswith('.py') and not f.is_deletion:
                try:
                    compile(f.new_content, f.file_path, 'exec')
                except SyntaxError as e:
                    errors.append(f"Syntax error in {f.file_path}: {e}")

        # Warnings
        for f in patch.files:
            if f.is_deletion:
                warnings.append(f"File will be deleted: {f.file_path}")
            if f.is_new_file:
                warnings.append(f"New file: {f.file_path}")

        # Check for large files
        for f in patch.files:
            if len(f.new_content) > 50000:
                warnings.append(f"Large file: {f.file_path} ({len(f.new_content)} chars)")

        passed = len(errors) == 0
        patch.validation_passed = passed
        patch.validation_errors = errors
        patch.validation_warnings = warnings

        if passed:
            patch.status = PatchStatus.VALIDATED.value

        return passed, errors, warnings

    def apply_patch(self, patch: Patch) -> bool:
        """
        Apply an approved patch to the filesystem.

        Returns True if all files were applied successfully.
        """
        if not patch.validation_passed:
            return False
        if not patch.approved:
            return False

        all_applied = True
        for f in patch.files:
            try:
                if f.is_deletion:
                    import os
                    path = os.path.join(self._project_root, f.file_path)
                    if os.path.exists(path):
                        os.remove(path)
                else:
                    import os
                    path = os.path.join(self._project_root, f.file_path)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as fh:
                        fh.write(f.new_content)
            except Exception as e:
                patch.validation_errors.append(f"Failed to apply {f.file_path}: {e}")
                all_applied = False

        if all_applied:
            patch.status = PatchStatus.APPLIED.value
            patch.applied_at = datetime.utcnow().isoformat() + "Z"
            self._applied_patches.append(patch.patch_id)

            # Generate rollback patch
            rollback = self._generate_rollback(patch)
            patch.rollback_patch_id = rollback.patch_id

        return all_applied

    def rollback_patch(self, patch_id: str) -> Optional[Patch]:
        """Roll back an applied patch."""
        patch = self._patches.get(patch_id)
        if not patch or patch.status != PatchStatus.APPLIED.value:
            return None

        rollback = self._generate_rollback(patch)
        success = self.apply_patch(rollback)

        if success:
            patch.status = PatchStatus.ROLLED_BACK.value

        return rollback

    def _generate_rollback(self, patch: Patch) -> Patch:
        """Generate a rollback patch that reverses the original."""
        rollback = Patch(
            task_id=patch.task_id,
            plan_id=patch.plan_id,
            created_by="system",
            summary=f"Rollback of patch {patch.patch_id}",
            risk_level=RiskLevel.HIGH.value,
        )

        for f in patch.files:
            if f.is_new_file:
                # Rollback = delete the new file
                rollback.files.append(FilePatch(
                    file_path=f.file_path,
                    original_content=f.new_content,
                    new_content="",
                    is_deletion=True,
                ))
            elif f.is_deletion:
                # Rollback = restore the deleted file
                rollback.files.append(FilePatch(
                    file_path=f.file_path,
                    original_content="",
                    new_content=f.original_content,
                    is_new_file=True,
                ))
            else:
                # Rollback = restore original content
                rollback.files.append(FilePatch(
                    file_path=f.file_path,
                    original_content=f.new_content,
                    new_content=f.original_content,
                    diff=self._compute_diff(f.file_path, f.new_content, f.original_content),
                ))

        rollback.status = PatchStatus.VALIDATED.value
        rollback.validation_passed = True
        rollback.approved = True
        self._patches[rollback.patch_id] = rollback
        return rollback

    def _compute_diff(self, file_path: str, original: str,
                      new: str) -> str:
        """Compute unified diff between original and new content."""
        original_lines = original.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original_lines, new_lines,
            fromfile=f"a/{file_path}", tofile=f"b/{file_path}",
        )
        return "".join(diff)

    def _read_file(self, file_path: str) -> str:
        """Read a file from the project root."""
        import os
        full_path = os.path.join(self._project_root, file_path)
        if not os.path.exists(full_path):
            return ""
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (IOError, UnicodeDecodeError):
            return ""

    def _assess_risk(self, patch: Patch) -> RiskLevel:
        """Assess the risk level of a patch."""
        # Critical: security-related files
        critical_patterns = ["auth", "security", "password", "secret", "token",
                            "crypto", "ssl", "tls"]
        # High: architecture, database, config
        high_patterns = ["config", "migration", "schema", "model", "router",
                        "middleware", "database"]
        # Low: docs, comments, formatting
        low_patterns = ["README", "CHANGELOG", "LICENSE", ".md", "test_",
                        "comment", "format"]

        max_risk = RiskLevel.LOW

        for f in patch.files:
            path_lower = f.file_path.lower()
            if any(p in path_lower for p in critical_patterns):
                return RiskLevel.CRITICAL
            if any(p in path_lower for p in high_patterns):
                max_risk = RiskLevel.HIGH
            elif any(p in path_lower for p in low_patterns):
                pass  # stays at current level

        # Large patches are at least MEDIUM
        if patch.total_files > 5 or patch.total_lines_added > 200:
            if max_risk.value == "low":
                max_risk = RiskLevel.MEDIUM

        return max_risk

    def get_patch(self, patch_id: str) -> Optional[Patch]:
        return self._patches.get(patch_id)

    def list_patches(self, status: str = "") -> List[Patch]:
        patches = list(self._patches.values())
        if status:
            patches = [p for p in patches if p.status == status]
        return patches
