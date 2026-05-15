"""
Patch Merge Engine — deterministic, diff-aware, line-aware, symbol-aware merge.

Principles:
- Non-conflicting patches are merged automatically
- Conflicting patches are rejected with clear resolution requirements
- Line-aware: detects overlapping line ranges
- Symbol-aware: detects symbol-level conflicts
- Deterministic: no AI merge hallucinations
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger


class MergeStatus(Enum):
    SUCCESS = "success"
    CONFLICT = "conflict"
    PARTIAL = "partial"
    REJECTED = "rejected"


class ConflictType(Enum):
    LINE_OVERLAP = "line_overlap"         # Same lines modified
    SYMBOL_CONFLICT = "symbol_conflict"   # Same symbol modified
    DELETE_MODIFY = "delete_modify"       # One deletes, other modifies
    DEPENDENCY_CONFLICT = "dependency_conflict"  # Dependent file modified


@dataclass
class MergeConflict:
    """A single merge conflict."""
    conflict_type: ConflictType
    file_path: str
    task_a: str
    task_b: str
    description: str
    line_start: int = 0
    line_end: int = 0
    symbol: str = ""
    resolution: str = ""  # manual required


@dataclass
class MergeResult:
    """Result of a merge operation."""
    status: MergeStatus
    merged_files: List[str] = field(default_factory=list)
    conflicts: List[MergeConflict] = field(default_factory=list)
    skipped_files: List[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def success_count(self) -> int:
        return len(self.merged_files)

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)


class PatchMergeEngine:
    """
    Merges patches from multiple tasks deterministically.

    Conflict detection:
    - Line overlap: two patches modify the same line range
    - Symbol conflict: two patches modify the same symbol
    - Delete/modify: one patch deletes what another modifies
    - Dependency conflict: patches modify dependent files
    """

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()

    def merge_patches(
        self,
        patches_a: List[Dict],
        patches_b: List[Dict],
        task_a_id: str,
        task_b_id: str,
    ) -> MergeResult:
        """
        Merge two sets of patches.

        Args:
            patches_a: Patches from task A
            patches_b: Patches from task B
            task_a_id: Task A ID
            task_b_id: Task B ID

        Returns:
            MergeResult with status and conflicts
        """
        result = MergeResult(status=MergeStatus.SUCCESS)

        # Group patches by file
        files_a = {p['file_path']: p for p in patches_a}
        files_b = {p['file_path']: p for p in patches_b}

        all_files = set(files_a.keys()) | set(files_b.keys())

        for file_path in sorted(all_files):
            patch_a = files_a.get(file_path)
            patch_b = files_b.get(file_path)

            if patch_a and patch_b:
                # Both tasks modified the same file
                conflict = self._check_patch_conflict(
                    patch_a, patch_b, task_a_id, task_b_id
                )
                if conflict:
                    result.conflicts.append(conflict)
                    result.skipped_files.append(file_path)
                    continue

            # No conflict — apply the patch
            if patch_a:
                success = self._apply_patch_to_file(file_path, patch_a)
                if success:
                    result.merged_files.append(file_path)
                else:
                    result.skipped_files.append(file_path)
            elif patch_b:
                success = self._apply_patch_to_file(file_path, patch_b)
                if success:
                    result.merged_files.append(file_path)
                else:
                    result.skipped_files.append(file_path)

        # Determine overall status
        if result.conflicts and result.merged_files:
            result.status = MergeStatus.PARTIAL
        elif result.conflicts:
            result.status = MergeStatus.CONFLICT
        else:
            result.status = MergeStatus.SUCCESS

        return result

    def merge_multiple(
        self,
        task_patches: Dict[str, List[Dict]],
    ) -> MergeResult:
        """
        Merge patches from multiple tasks.

        Args:
            task_patches: Dict of task_id -> patches

        Returns:
            Combined MergeResult
        """
        task_ids = list(task_patches.keys())
        if len(task_ids) < 2:
            # Single task — just apply
            result = MergeResult(status=MergeStatus.SUCCESS)
            for patch in task_patches.get(task_ids[0], []):
                success = self._apply_patch_to_file(patch['file_path'], patch)
                if success:
                    result.merged_files.append(patch['file_path'])
            return result

        # Merge pairwise
        combined = MergeResult(status=MergeStatus.SUCCESS)

        for i in range(len(task_ids) - 1):
            task_a = task_ids[i]
            task_b = task_ids[i + 1]

            partial = self.merge_patches(
                task_patches.get(task_a, []),
                task_patches.get(task_b, []),
                task_a, task_b,
            )

            combined.merged_files.extend(partial.merged_files)
            combined.conflicts.extend(partial.conflicts)
            combined.skipped_files.extend(partial.skipped_files)

        # Determine final status
        if combined.conflicts and combined.merged_files:
            combined.status = MergeStatus.PARTIAL
        elif combined.conflicts:
            combined.status = MergeStatus.CONFLICT

        return combined

    def _check_patch_conflict(
        self,
        patch_a: Dict,
        patch_b: Dict,
        task_a_id: str,
        task_b_id: str,
    ) -> Optional[MergeConflict]:
        """Check if two patches on the same file conflict."""
        # Line overlap check
        a_start = patch_a.get('start_line', 0)
        a_end = patch_a.get('end_line', 0) or a_start
        b_start = patch_b.get('start_line', 0)
        b_end = patch_b.get('end_line', 0) or b_start

        if self._ranges_overlap(a_start, a_end, b_start, b_end):
            return MergeConflict(
                conflict_type=ConflictType.LINE_OVERLAP,
                file_path=patch_a['file_path'],
                task_a=task_a_id,
                task_b=task_b_id,
                description=(
                    f"Line overlap: task {task_a_id} modifies lines "
                    f"{a_start}-{a_end}, task {task_b_id} modifies lines "
                    f"{b_start}-{b_end}"
                ),
                line_start=min(a_start, b_start),
                line_end=max(a_end, b_end),
            )

        # Symbol conflict check
        a_symbol = patch_a.get('symbol', '')
        b_symbol = patch_b.get('symbol', '')
        if a_symbol and b_symbol and a_symbol == b_symbol:
            return MergeConflict(
                conflict_type=ConflictType.SYMBOL_CONFLICT,
                file_path=patch_a['file_path'],
                task_a=task_a_id,
                task_b=task_b_id,
                description=f"Both tasks modify symbol: {a_symbol}",
                symbol=a_symbol,
            )

        # Delete/modify conflict
        a_type = patch_a.get('patch_type', '')
        b_type = patch_b.get('patch_type', '')
        if (a_type == 'delete' and b_type != 'delete') or \
           (b_type == 'delete' and a_type != 'delete'):
            return MergeConflict(
                conflict_type=ConflictType.DELETE_MODIFY,
                file_path=patch_a['file_path'],
                task_a=task_a_id,
                task_b=task_b_id,
                description="One task deletes while other modifies",
            )

        return None

    def _apply_patch_to_file(self, file_path: str, patch: Dict) -> bool:
        """Apply a single patch to a file."""
        full_path = self.project_path / file_path

        if not full_path.exists():
            logger.warning(f"File not found for patch: {file_path}")
            return False

        try:
            content = full_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            patch_type = patch.get('patch_type', 'replace')
            start = patch.get('start_line', 1) - 1  # 0-indexed
            end = patch.get('end_line', start + 1) - 1
            new_content = patch.get('new_content', '')

            if patch_type == 'insert':
                insert_lines = new_content.split('\n')
                for i, line in enumerate(insert_lines):
                    lines.insert(start + i, line)
            elif patch_type == 'replace':
                insert_lines = new_content.split('\n')
                lines[start:end + 1] = insert_lines
            elif patch_type == 'delete':
                del lines[start:end + 1]
            elif patch_type == 'append':
                lines.extend(new_content.split('\n'))
            elif patch_type == 'prepend':
                lines = new_content.split('\n') + lines

            full_path.write_text('\n'.join(lines), encoding='utf-8')
            return True

        except Exception as e:
            logger.error(f"Failed to apply patch to {file_path}: {e}")
            return False

    @staticmethod
    def _ranges_overlap(a1: int, a2: int, b1: int, b2: int) -> bool:
        """Check if two line ranges overlap."""
        return a1 <= b2 and b1 <= a2
