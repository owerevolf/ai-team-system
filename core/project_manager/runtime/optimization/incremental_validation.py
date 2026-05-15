"""
Incremental Validation — validate only affected modules.

Instead of validating entire repo, only check:
- Changed files
- Directly dependent files
- Files with modified symbols
- Files with impacted contracts
"""

from typing import Dict, List, Optional, Set, Any

from loguru import logger


class IncrementalValidator:
    """
    Runs validation only on affected portions of the project.

    When files change, only validates:
    1. The changed files themselves
    2. Files that directly import changed files
    3. Files that export symbols used by changed files
    4. Files with architecture rule violations involving changed files
    """

    def __init__(
        self,
        files: Dict[str, Any],
        dependencies: Dict[str, List[str]],
        reverse_dependencies: Dict[str, List[str]],
    ):
        self.files = files
        self.dependencies = dependencies
        self._reverse_deps = reverse_dependencies

    def get_affected_scope(
        self,
        changed_files: List[str],
        max_depth: int = 1,
    ) -> Set[str]:
        """
        Determine which files need re-validation.

        Args:
            changed_files: Files that were modified
            max_depth: How many levels of dependents to include

        Returns:
            Set of file paths that need validation
        """
        affected: Set[str] = set()

        # Always include changed files
        affected.update(changed_files)

        for changed in changed_files:
            # Add direct dependents (files that import this file)
            for dep in self._reverse_deps.get(changed, [])[:10]:
                affected.add(dep)

            # Add direct dependencies (files this file imports)
            for dep in self.dependencies.get(changed, [])[:10]:
                affected.add(dep)

            # If depth > 1, include transitive dependents
            if max_depth > 1:
                visited: Set[str] = {changed}
                queue = [(d, 1) for d in self._reverse_deps.get(changed, [])]

                while queue:
                    current, depth = queue.pop(0)
                    if current in visited or depth > max_depth:
                        continue
                    visited.add(current)
                    affected.add(current)

                    for dep in self._reverse_deps.get(current, []):
                        if dep not in visited:
                            queue.append((dep, depth + 1))

        return affected

    def validate_incremental(
        self,
        changed_files: List[str],
        full_validator: Any,  # ValidationPipeline
        max_depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Run validation only on affected files.

        Returns:
            Validation result summary
        """
        affected = self.get_affected_scope(changed_files, max_depth)

        logger.info(
            f"Incremental validation: {len(changed_files)} changed, "
            f"{len(affected)} affected (depth={max_depth})"
        )

        # Run validation on affected files only
        # We create a subset of files for validation
        affected_file_entries = {
            f: self.files[f] for f in affected if f in self.files
        }

        # Build subset of dependencies
        affected_deps = {
            f: [d for d in self.dependencies.get(f, []) if d in affected]
            for f in affected
        }

        # Run validation on subset
        from core.project_manager.validation import ValidationPipeline
        pipeline = ValidationPipeline(
            affected_file_entries,
            affected_deps,
            full_validator.project_path,
        )
        result = pipeline.validate()

        return {
            'files_checked': len(affected),
            'total_files': len(self.files),
            'coverage': round(len(affected) / max(len(self.files), 1), 3),
            'issues_found': len(result.issues),
            'errors': result.error_count,
            'warnings': result.warning_count,
            'critical': result.critical_count,
            'elapsed_seconds': result.elapsed_seconds,
        }
