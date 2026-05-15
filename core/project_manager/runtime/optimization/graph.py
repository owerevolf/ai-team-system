"""
Graph Optimization — lazy traversal, depth limits, cached paths, partitioning.

Optimizations:
- Lazy graph traversal (only traverse what's needed)
- Depth limits (don't traverse entire graph)
- Cached traversal paths (memoize BFS/DFS results)
- Graph partitioning (split large graphs into subgraphs)
- Incremental graph updates (only update changed portions)
"""

import time
import threading
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, deque

from loguru import logger


class OptimizedDependencyGraph:
    """
    Optimized dependency graph with caching and lazy traversal.

    Features:
    - Cached traversal results with TTL
    - Depth-limited BFS/DFS
    - Reverse dependency index (file → files that import it)
    - Incremental updates (only rebuild affected portions)
    - Traversal statistics
    """

    DEFAULT_MAX_DEPTH = 10
    DEFAULT_CACHE_TTL = 60.0  # 1 minute

    def __init__(
        self,
        dependencies: Dict[str, List[str]],
        max_depth: int = DEFAULT_MAX_DEPTH,
        cache_ttl: float = DEFAULT_CACHE_TTL,
    ):
        self._deps = dependencies
        self._reverse_deps: Dict[str, List[str]] = {}
        self._max_depth = max_depth
        self._cache_ttl = cache_ttl

        # Traversal cache: (file, direction, max_depth) → result
        self._traversal_cache: Dict[str, Tuple[List[str], float]] = {}

        # Statistics
        self._stats = {
            'traversals': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'depth_limited': 0,
        }

        self._build_reverse_index()

    def _build_reverse_index(self) -> None:
        """Build reverse dependency index."""
        self._reverse_deps = {}
        for source, targets in self._deps.items():
            for target in targets:
                if target not in self._reverse_deps:
                    self._reverse_deps[target] = []
                self._reverse_deps[target].append(source)

    # ── TRAVERSAL ──

    def get_dependents(
        self,
        file_path: str,
        max_depth: int = -1,
        use_cache: bool = True,
    ) -> List[str]:
        """
        Get all files that depend on the given file (reverse BFS).

        Args:
            file_path: File to find dependents for
            max_depth: Max traversal depth (-1 = use default)
            use_cache: Whether to use cached results

        Returns:
            List of dependent file paths, sorted by distance
        """
        if max_depth < 0:
            max_depth = self._max_depth

        cache_key = f"dep:{file_path}:{max_depth}"

        # Check cache
        if use_cache:
            cached = self._traversal_cache.get(cache_key)
            if cached and (time.time() - cached[1]) < self._cache_ttl:
                self._stats['cache_hits'] += 1
                return cached[0]

        self._stats['cache_misses'] += 1
        self._stats['traversals'] += 1

        # BFS with depth limit
        result = []
        visited: Set[str] = {file_path}
        queue: deque = deque([(file_path, 0)])

        while queue:
            current, depth = queue.popleft()

            if depth >= max_depth:
                self._stats['depth_limited'] += 1
                continue

            for dependent in self._reverse_deps.get(current, []):
                if dependent not in visited:
                    visited.add(dependent)
                    result.append(dependent)
                    queue.append((dependent, depth + 1))

        # Cache result
        self._traversal_cache[cache_key] = (result, time.time())

        return result

    def get_dependencies(
        self,
        file_path: str,
        max_depth: int = -1,
        use_cache: bool = True,
    ) -> List[str]:
        """
        Get all files that the given file depends on (forward BFS).

        Args:
            file_path: File to find dependencies for
            max_depth: Max traversal depth (-1 = use default)
            use_cache: Whether to use cached results

        Returns:
            List of dependency file paths, sorted by distance
        """
        if max_depth < 0:
            max_depth = self._max_depth

        cache_key = f"rev:{file_path}:{max_depth}"

        if use_cache:
            cached = self._traversal_cache.get(cache_key)
            if cached and (time.time() - cached[1]) < self._cache_ttl:
                self._stats['cache_hits'] += 1
                return cached[0]

        self._stats['cache_misses'] += 1
        self._stats['traversals'] += 1

        result = []
        visited: Set[str] = {file_path}
        queue: deque = deque([(file_path, 0)])

        while queue:
            current, depth = queue.popleft()

            if depth >= max_depth:
                self._stats['depth_limited'] += 1
                continue

            for dep in self._deps.get(current, []):
                if dep not in visited:
                    visited.add(dep)
                    result.append(dep)
                    queue.append((dep, depth + 1))

        self._traversal_cache[cache_key] = (result, time.time())

        return result

    def get_impact_radius(
        self,
        changed_files: List[str],
        max_depth: int = 3,
    ) -> Dict[str, int]:
        """
        Get impact radius for a set of changed files.

        Returns:
            Dict mapping affected file → distance from nearest changed file
        """
        impact: Dict[str, int] = {}

        for changed in changed_files:
            dependents = self.get_dependents(changed, max_depth=max_depth)
            for dep in dependents:
                if dep not in impact:
                    # Calculate actual distance
                    dist = self._get_distance(changed, dep)
                    if dist > 0:
                        impact[dep] = dist

        return impact

    def _get_distance(self, source: str, target: str) -> int:
        """Get shortest distance from source to target via BFS."""
        if source == target:
            return 0

        visited: Set[str] = {source}
        queue: deque = deque([(source, 0)])

        while queue:
            current, depth = queue.popleft()

            if depth >= self._max_depth:
                continue

            for dep in self._deps.get(current, []):
                if dep == target:
                    return depth + 1
                if dep not in visited:
                    visited.add(dep)
                    queue.append((dep, depth + 1))

        return -1  # Not reachable

    # ── INCREMENTAL UPDATES ──

    def update_file(self, file_path: str, new_deps: List[str]) -> None:
        """Update dependencies for a single file and invalidate affected caches."""
        old_deps = self._deps.get(file_path, [])

        # Update forward deps
        self._deps[file_path] = new_deps

        # Update reverse deps
        for old_dep in old_deps:
            if old_dep in self._reverse_deps:
                self._reverse_deps[old_dep] = [
                    f for f in self._reverse_deps[old_dep] if f != file_path
                ]

        for new_dep in new_deps:
            if new_dep not in self._reverse_deps:
                self._reverse_deps[new_dep] = []
            if file_path not in self._reverse_deps[new_dep]:
                self._reverse_deps[new_dep].append(file_path)

        # Invalidate cache entries involving this file
        self._invalidate_cache_for(file_path)

    def remove_file(self, file_path: str) -> None:
        """Remove a file from the graph."""
        # Remove from forward deps
        old_deps = self._deps.pop(file_path, [])

        # Remove from reverse deps
        for dep in old_deps:
            if dep in self._reverse_deps:
                self._reverse_deps[dep] = [
                    f for f in self._reverse_deps[dep] if f != file_path
                ]

        # Remove files that depend on this file
        for dependent in self._reverse_deps.get(file_path, []):
            if dependent in self._deps:
                self._deps[dependent] = [
                    d for d in self._deps[dependent] if d != file_path
                ]

        self._reverse_deps.pop(file_path, None)

        # Invalidate cache
        self._invalidate_cache_for(file_path)

    def _invalidate_cache_for(self, file_path: str) -> None:
        """Invalidate cache entries involving a file."""
        keys_to_remove = [
            k for k in self._traversal_cache
            if file_path in k
        ]
        for k in keys_to_remove:
            del self._traversal_cache[k]

    # ── GRAPH PARTITIONING ──

    def get_connected_components(self) -> List[Set[str]]:
        """
        Find connected components in the dependency graph.

        Returns:
            List of sets, each set containing files in a connected component
        """
        visited: Set[str] = set()
        components: List[Set[str]] = []

        for file_path in self._deps:
            if file_path in visited:
                continue

            component: Set[str] = set()
            queue = deque([file_path])

            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)

                for dep in self._deps.get(current, []):
                    if dep not in visited:
                        queue.append(dep)

                for rev_dep in self._reverse_deps.get(current, []):
                    if rev_dep not in visited:
                        queue.append(rev_dep)

            components.append(component)

        return components

    def get_subgraph(self, file_paths: Set[str], include_deps: bool = True) -> Dict[str, List[str]]:
        """
        Extract a subgraph containing only the specified files.

        Args:
            file_paths: Files to include
            include_deps: Whether to include dependencies of specified files

        Returns:
            Filtered dependency dict
        """
        if include_deps:
            # BFS to find all reachable files
            reachable = set(file_paths)
            queue = deque(file_paths)

            while queue:
                current = queue.popleft()
                for dep in self._deps.get(current, []):
                    if dep not in reachable:
                        reachable.add(dep)
                        queue.append(dep)

            file_paths = reachable

        return {
            f: [d for d in self._deps.get(f, []) if d in file_paths]
            for f in file_paths
            if f in self._deps
        }

    # ── STATS ──

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        total = self._stats['cache_hits'] + self._stats['cache_misses']
        return {
            'total_files': len(self._deps),
            'total_dependencies': sum(len(d) for d in self._deps.values()),
            'reverse_index_size': len(self._reverse_deps),
            'cache_entries': len(self._traversal_cache),
            'traversals': self._stats['traversals'],
            'cache_hit_rate': round(self._stats['cache_hits'] / total, 3) if total > 0 else 0.0,
            'depth_limited': self._stats['depth_limited'],
        }

    def clear_cache(self) -> None:
        """Clear traversal cache."""
        self._traversal_cache.clear()
