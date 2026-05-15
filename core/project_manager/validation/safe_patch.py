"""
Safe Patch System — minimal, line-aware, diff-aware modifications.

Principles:
- Minimal edits (change only what's needed)
- Line-aware (preserve surrounding context)
- Diff-aware (detect conflicts before applying)
- Conflict detection (don't apply on stale content)
- Reversible (every patch can be reverted)
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from difflib import unified_diff

from loguru import logger


class PatchType(Enum):
    INSERT = "insert"       # Insert at line
    REPLACE = "replace"     # Replace line range
    DELETE = "delete"       # Delete line range
    APPEND = "append"       # Append to end of file
    PREPEND = "prepend"     # Prepend to start of file


class PatchStatus(Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    REVERTED = "reverted"
    CONFLICT = "conflict"


@dataclass
class Patch:
    """A single file patch."""
    file_path: str
    patch_type: PatchType
    start_line: int = 0      # 1-indexed
    end_line: int = 0        # 1-indexed, inclusive
    old_content: str = ""    # Content to replace/delete (for conflict detection)
    new_content: str = ""    # New content
    description: str = ""
    status: PatchStatus = PatchStatus.PENDING
    error: str = ""


@dataclass
class PatchSet:
    """A collection of patches to apply together."""
    patches: List[Patch] = field(default_factory=list)
    description: str = ""
    snapshot_before: str = ""  # snapshot ID before applying
    snapshot_after: str = ""   # snapshot ID after applying

    @property
    def files_affected(self) -> List[str]:
        return list(set(p.file_path for p in self.patches))

    @property
    def pending_count(self) -> int:
        return sum(1 for p in self.patches if p.status == PatchStatus.PENDING)

    @property
    def applied_count(self) -> int:
        return sum(1 for p in self.patches if p.status == PatchStatus.APPLIED)

    @property
    def failed_count(self) -> int:
        return sum(1 for p in self.patches if p.status == PatchStatus.FAILED)


@dataclass
class PatchResult:
    """Result of applying a patch."""
    patch: Patch
    success: bool
    conflict: bool = False
    error: str = ""
    diff: str = ""


class SafePatchSystem:
    """
    Applies patches safely with conflict detection and rollback.

    Features:
    - Content hash verification (don't apply on stale content)
    - Line-level precision
    - Conflict detection
    - Automatic rollback on failure
    - Diff generation
    """

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()

    def apply_patch_set(
        self,
        patch_set: PatchSet,
        dry_run: bool = False,
    ) -> List[PatchResult]:
        """
        Apply a set of patches atomically.

        If any patch fails, all applied patches are rolled back.

        Args:
            patch_set: Patches to apply
            dry_run: If True, only check without applying

        Returns:
            List of PatchResult for each patch
        """
        results: List[PatchResult] = []
        applied: List[Tuple[str, str]] = []  # (file_path, original_content) for rollback

        try:
            for patch in patch_set.patches:
                if patch.status != PatchStatus.PENDING:
                    continue

                result = self._apply_single_patch(patch, dry_run)
                results.append(result)

                if result.success and not dry_run:
                    # Save original content for rollback
                    full_path = self.project_path / patch.file_path
                    if full_path.exists():
                        original = full_path.read_text(encoding='utf-8')
                        applied.append((patch.file_path, original))
                elif not result.success:
                    # Rollback all applied patches
                    if not dry_run:
                        self._rollback_applied(applied)
                    break

        except Exception as e:
            logger.error(f"Patch set application failed: {e}")
            if not dry_run:
                self._rollback_applied(applied)

        return results

    def _apply_single_patch(self, patch: Patch, dry_run: bool = False) -> PatchResult:
        """Apply a single patch to a file."""
        full_path = self.project_path / patch.file_path

        if not full_path.exists():
            if patch.patch_type in (PatchType.APPEND, PatchType.PREPEND, PatchType.INSERT):
                # Can create new file
                if not dry_run:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(patch.new_content, encoding='utf-8')
                patch.status = PatchStatus.APPLIED
                return PatchResult(patch=patch, success=True)
            else:
                patch.status = PatchStatus.FAILED
                patch.error = f"File not found: {patch.file_path}"
                return PatchResult(patch=patch, success=False, error=patch.error)

        try:
            original_content = full_path.read_text(encoding='utf-8')
            lines = original_content.split('\n')

            # Conflict detection: verify old content matches
            if patch.old_content:
                actual_old = '\n'.join(
                    lines[patch.start_line - 1:patch.end_line]
                    if patch.end_line > 0
                    else lines[patch.start_line - 1:patch.start_line]
                )
                if actual_old.strip() != patch.old_content.strip():
                    patch.status = PatchStatus.CONFLICT
                    patch.error = "Content mismatch — file was modified since patch was created"
                    return PatchResult(
                        patch=patch, success=False, conflict=True, error=patch.error
                    )

            # Apply patch based on type
            new_lines = list(lines)

            if patch.patch_type == PatchType.INSERT:
                insert_lines = patch.new_content.split('\n')
                for i, line in enumerate(insert_lines):
                    new_lines.insert(patch.start_line - 1 + i, line)

            elif patch.patch_type == PatchType.REPLACE:
                insert_lines = patch.new_content.split('\n')
                end = patch.end_line if patch.end_line > 0 else patch.start_line
                new_lines[patch.start_line - 1:end] = insert_lines

            elif patch.patch_type == PatchType.DELETE:
                end = patch.end_line if patch.end_line > 0 else patch.start_line
                del new_lines[patch.start_line - 1:end]

            elif patch.patch_type == PatchType.APPEND:
                new_lines.extend(patch.new_content.split('\n'))

            elif patch.patch_type == PatchType.PREPEND:
                insert_lines = patch.new_content.split('\n')
                new_lines = insert_lines + new_lines

            # Generate diff
            new_content = '\n'.join(new_lines)
            diff = '\n'.join(unified_diff(
                lines, new_lines,
                fromfile=f"a/{patch.file_path}",
                tofile=f"b/{patch.file_path}",
                lineterm='',
            ))

            if not dry_run:
                full_path.write_text(new_content, encoding='utf-8')

            patch.status = PatchStatus.APPLIED
            return PatchResult(patch=patch, success=True, diff=diff)

        except Exception as e:
            patch.status = PatchStatus.FAILED
            patch.error = str(e)
            return PatchResult(patch=patch, success=False, error=str(e))

    def _rollback_applied(self, applied: List[Tuple[str, str]]) -> None:
        """Rollback applied patches."""
        for file_path, original_content in reversed(applied):
            try:
                full_path = self.project_path / file_path
                full_path.write_text(original_content, encoding='utf-8')
                logger.info(f"Rolled back: {file_path}")
            except Exception as e:
                logger.error(f"Rollback failed for {file_path}: {e}")

    def revert_patch_set(self, patch_set: PatchSet) -> List[PatchResult]:
        """Revert a previously applied patch set."""
        results = []

        for patch in reversed(patch_set.patches):
            if patch.status != PatchStatus.APPLIED:
                continue

            full_path = self.project_path / patch.file_path
            if not full_path.exists():
                continue

            try:
                content = full_path.read_text(encoding='utf-8')
                lines = content.split('\n')

                # Reverse the patch
                if patch.patch_type == PatchType.INSERT:
                    # Delete inserted lines
                    end = patch.start_line + len(patch.new_content.split('\n')) - 1
                    del lines[patch.start_line - 1:end]

                elif patch.patch_type == PatchType.REPLACE:
                    # Restore old content
                    old_lines = patch.old_content.split('\n')
                    insert_lines = patch.new_content.split('\n')
                    end = patch.start_line + len(insert_lines) - 1
                    lines[patch.start_line - 1:end] = old_lines

                elif patch.patch_type == PatchType.DELETE:
                    # Restore deleted lines
                    old_lines = patch.old_content.split('\n')
                    for i, line in enumerate(old_lines):
                        lines.insert(patch.start_line - 1 + i, line)

                elif patch.patch_type == PatchType.APPEND:
                    # Remove appended content
                    append_lines = patch.new_content.split('\n')
                    if len(lines) >= len(append_lines):
                        lines = lines[:-len(append_lines)]

                elif patch.patch_type == PatchType.PREPEND:
                    # Remove prepended content
                    prepend_lines = patch.new_content.split('\n')
                    if len(lines) >= len(prepend_lines):
                        lines = lines[len(prepend_lines):]

                full_path.write_text('\n'.join(lines), encoding='utf-8')
                patch.status = PatchStatus.REVERTED
                results.append(PatchResult(patch=patch, success=True))

            except Exception as e:
                results.append(PatchResult(patch=patch, success=False, error=str(e)))

        return results

    def create_patch_from_diff(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        description: str = "",
    ) -> Patch:
        """Create a Patch from old and new content."""
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')

        # Find the differing range
        start = 0
        for i, (old, new) in enumerate(zip(old_lines, new_lines)):
            if old != new:
                start = i + 1
                break

        if start == 0:
            # No differences or all different
            if old_lines == new_lines:
                return Patch(
                    file_path=file_path,
                    patch_type=PatchType.REPLACE,
                    old_content=old_content,
                    new_content=new_content,
                    description=description or "No changes",
                )
            start = 1

        # Find end of diff
        end_old = len(old_lines)
        end_new = len(new_lines)
        while end_old > start and end_new > 0 and old_lines[end_old - 1] == new_lines[end_new - 1]:
            end_old -= 1
            end_new -= 1

        return Patch(
            file_path=file_path,
            patch_type=PatchType.REPLACE,
            start_line=start,
            end_line=end_old,
            old_content='\n'.join(old_lines[start - 1:end_old]),
            new_content='\n'.join(new_lines[start - 1:end_new] if end_new >= start else []),
            description=description,
        )
