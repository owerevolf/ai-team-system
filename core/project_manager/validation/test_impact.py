"""
Test Impact Analysis — find relevant tests for changed files.

Deterministic. Uses dependency graph + naming conventions.
Never runs full test suite when only specific files changed.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from core.project_manager.models import FileEntry
from loguru import logger


class TestImpactAnalyzer:
    """
    Determines which tests to run based on file changes.

    Strategies:
    1. Direct: test file imports the changed file
    2. Transitive: test file imports something that depends on changed file
    3. Naming: test file name matches changed file name
    4. Convention: tests/ directory mirrors source structure
    """

    def __init__(
        self,
        files: Dict[str, FileEntry],
        dependencies: Dict[str, List[str]],
        reverse_dependencies: Optional[Dict[str, List[str]]] = None,
    ):
        self.files = files
        self.dependencies = dependencies
        self._reverse_deps = reverse_dependencies or self._build_reverse_deps()

    def _build_reverse_deps(self) -> Dict[str, List[str]]:
        """Build reverse dependency map (file -> files that import it)."""
        reverse: Dict[str, List[str]] = defaultdict(list)
        for source, targets in self.dependencies.items():
            for target in targets:
                reverse[target].append(source)
        return dict(reverse)

    def find_relevant_tests(
        self,
        changed_files: List[str],
        max_depth: int = 2,
    ) -> List[Dict]:
        """
        Find tests relevant to the given file changes.

        Args:
            changed_files: List of changed file paths
            max_depth: How many levels of transitive deps to follow

        Returns:
            List of test file info dicts with relevance scores
        """
        test_scores: Dict[str, float] = defaultdict(float)
        reasons: Dict[str, List[str]] = defaultdict(list)

        for changed_file in changed_files:
            # Strategy 1: Direct dependency
            direct_dependents = self._reverse_deps.get(changed_file, [])
            for dep in direct_dependents:
                if self._is_test_file(dep):
                    test_scores[dep] += 10.0
                    reasons[dep].append(f"direct import of {changed_file}")

            # Strategy 2: Transitive dependency (BFS)
            if max_depth > 0:
                visited: Set[str] = {changed_file}
                queue: List[Tuple[str, int]] = [(changed_file, 0)]

                while queue:
                    current, depth = queue.pop(0)
                    if depth >= max_depth:
                        continue

                    for dep in self._reverse_deps.get(current, []):
                        if dep not in visited:
                            visited.add(dep)
                            if self._is_test_file(dep):
                                score = 5.0 / (depth + 1)
                                test_scores[dep] += score
                                reasons[dep].append(
                                    f"transitive (depth {depth + 1}) from {changed_file}"
                                )
                            else:
                                queue.append((dep, depth + 1))

            # Strategy 3: Naming convention
            test_name_match = self._find_test_by_name(changed_file)
            if test_name_match:
                for test_file in test_name_match:
                    if test_file not in test_scores:
                        test_scores[test_file] += 3.0
                        reasons[test_file].append(f"name match for {changed_file}")

            # Strategy 4: Directory convention
            dir_tests = self._find_tests_in_same_dir(changed_file)
            for test_file in dir_tests:
                if test_file not in test_scores:
                    test_scores[test_file] += 1.0
                    reasons[test_file].append(f"same directory as {changed_file}")

        # Build result
        results = []
        for test_file, score in sorted(test_scores.items(), key=lambda x: -x[1]):
            entry = self.files.get(test_file)
            results.append({
                'test_file': test_file,
                'relevance_score': round(score, 1),
                'reasons': reasons[test_file],
                'language': entry.language if entry else 'unknown',
                'symbols_count': len(entry.symbols) if entry else 0,
            })

        return results

    def get_test_recommendations(
        self,
        changed_files: List[str],
        max_tests: int = 20,
    ) -> Dict:
        """
        Get test execution recommendations.

        Returns:
            Dict with test lists by priority
        """
        relevant = self.find_relevant_tests(changed_files)

        # Categorize by relevance
        high = [t for t in relevant if t['relevance_score'] >= 8.0]
        medium = [t for t in relevant if 3.0 <= t['relevance_score'] < 8.0]
        low = [t for t in relevant if t['relevance_score'] < 3.0]

        # Always include if we have very few
        if len(high) < 3:
            high.extend(medium[:3 - len(high)])
            medium = medium[3 - len(high):]

        return {
            'must_run': [t['test_file'] for t in high[:max_tests]],
            'should_run': [t['test_file'] for t in medium[:max_tests // 2]],
            'could_run': [t['test_file'] for t in low[:max_tests // 4]],
            'total_relevant': len(relevant),
            'changed_files': changed_files,
            'details': relevant[:max_tests],
        }

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file."""
        name = Path(file_path).name
        path = file_path.lower()

        if name.startswith('test_') or name.endswith('_test.py'):
            return True
        if 'test' in path or 'tests' in path:
            return True
        if name == 'conftest.py':
            return True

        return False

    def _find_test_by_name(self, source_file: str) -> List[str]:
        """Find test files that match the source file name."""
        results = []
        base_name = Path(source_file).stem  # e.g., "app" from "app.py"

        # Common test naming patterns
        patterns = [
            f"test_{base_name}",
            f"{base_name}_test",
            f"tests/test_{base_name}",
            f"tests/{base_name}_test",
        ]

        for rel_path in self.files:
            path_stem = Path(rel_path).stem
            for pattern in patterns:
                if path_stem == pattern or rel_path.endswith(pattern + '.py'):
                    if self._is_test_file(rel_path):
                        results.append(rel_path)

        return list(set(results))

    def _find_tests_in_same_dir(self, source_file: str) -> List[str]:
        """Find test files in the same directory as the source file."""
        results = []
        source_dir = str(Path(source_file).parent)

        for rel_path in self.files:
            if self._is_test_file(rel_path):
                file_dir = str(Path(rel_path).parent)
                if file_dir == source_dir:
                    results.append(rel_path)

        return results

    def get_all_test_files(self) -> List[str]:
        """Get all test files in the project."""
        return [f for f in self.files if self._is_test_file(f)]

    def get_test_coverage_map(self) -> Dict[str, List[str]]:
        """
        Build a map of source files to their test files.
        Useful for understanding test coverage.
        """
        coverage: Dict[str, List[str]] = defaultdict(list)
        test_files = self.get_all_test_files()

        for test_file in test_files:
            # Check what this test imports
            deps = self.dependencies.get(test_file, [])
            for dep in deps:
                if not self._is_test_file(dep):
                    coverage[dep].append(test_file)

        return dict(coverage)
