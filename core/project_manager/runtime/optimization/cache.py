"""
Execution Cache System — runtime cache layer with dependency-aware invalidation.

Caches:
- Retrieval results (query → context)
- Validation results (file_hash → issues)
- Symbol lookups (symbol_name → locations)
- Impact analysis (file → affected files)
- Test mappings (file → relevant tests)

Invalidation: incremental and dependency-aware.
When a file changes, only dependent caches are invalidated.
"""

import time
import threading
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class CacheEntry:
    """A single cache entry."""
    key: str
    value: Any
    created_at: float = 0.0
    ttl: float = 300.0  # default 5 min TTL
    hits: int = 0
    dependencies: Set[str] = field(default_factory=set)  # file hashes this depends on

    @property
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return (time.time() - self.created_at) > self.ttl

    def touch(self):
        self.hits += 1


class CacheStats:
    """Cache performance statistics."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.evictions = 0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        total = self.total_requests
        return self.hits / total if total > 0 else 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(self.hit_rate, 3),
            'invalidations': self.invalidations,
            'evictions': self.evictions,
        }


class ExecutionCache:
    """
    Multi-tier execution cache with dependency-aware invalidation.

    Tiers:
    - retrieval: query → context string
    - validation: file_hash → validation issues
    - symbol: symbol_name → [(file, line)]
    - impact: file → affected files list
    - test: file → relevant tests

    Invalidation:
    - When file X changes, invalidate all entries that depend on X
    - TTL-based expiry for stale entries
    - LRU eviction when size limit reached
    """

    DEFAULT_MAX_SIZE = 10000
    DEFAULT_TTL = 300.0  # 5 minutes

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE, default_ttl: float = DEFAULT_TTL):
        self._cache: Dict[str, Dict[str, CacheEntry]] = {
            'retrieval': {},
            'validation': {},
            'symbol': {},
            'impact': {},
            'test': {},
        }
        self._dependency_index: Dict[str, Set[str]] = defaultdict(set)  # file_hash -> cache keys
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._stats: Dict[str, CacheStats] = {tier: CacheStats() for tier in self._cache}
        self._lock = threading.Lock()

    # ── GET / PUT ──

    def get(self, tier: str, key: str) -> Optional[Any]:
        """Get a cached value. Returns None on miss or expiry."""
        with self._lock:
            entries = self._cache.get(tier)
            if not entries:
                self._stats[tier].misses += 1
                return None

            entry = entries.get(key)
            if not entry:
                self._stats[tier].misses += 1
                return None

            if entry.is_expired:
                del entries[key]
                self._stats[tier].evictions += 1
                return None

            entry.touch()
            self._stats[tier].hits += 1
            return entry.value

    def put(
        self,
        tier: str,
        key: str,
        value: Any,
        dependencies: Optional[Set[str]] = None,
        ttl: Optional[float] = None,
    ) -> None:
        """Store a value in cache."""
        with self._lock:
            entries = self._cache.setdefault(tier, {})

            # Evict if at capacity
            if len(entries) >= self._max_size // len(self._cache):
                self._evict_lru(tier)

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl if ttl is not None else self._default_ttl,
                dependencies=dependencies or set(),
            )
            entries[key] = entry

            # Update dependency index
            for dep in (dependencies or set()):
                self._dependency_index[dep].add(f"{tier}:{key}")

    # ── INVALIDATION ──

    def invalidate_file(self, file_hash: str) -> int:
        """
        Invalidate all cache entries that depend on a file.

        Returns number of entries invalidated.
        """
        with self._lock:
            keys = self._dependency_index.get(file_hash, set()).copy()
            count = 0

            for full_key in keys:
                tier, _, key = full_key.partition(':')
                entries = self._cache.get(tier, {})
                if key in entries:
                    del entries[key]
                    count += 1

            self._dependency_index.pop(file_hash, None)

            if count:
                for tier in self._stats:
                    self._stats[tier].invalidations += count

            return count

    def invalidate_tier(self, tier: str) -> int:
        """Invalidate all entries in a tier."""
        with self._lock:
            entries = self._cache.get(tier, {})
            count = len(entries)
            entries.clear()

            # Clean dependency index
            for dep_key in list(self._dependency_index.keys()):
                self._dependency_index[dep_key] = {
                    k for k in self._dependency_index[dep_key]
                    if not k.startswith(f"{tier}:")
                }

            return count

    def invalidate_all(self) -> int:
        """Invalidate all cache entries."""
        with self._lock:
            total = sum(len(e) for e in self._cache.values())
            for tier in self._cache:
                self._cache[tier].clear()
            self._dependency_index.clear()
            return total

    # ── EVICTION ──

    def _evict_lru(self, tier: str) -> None:
        """Evict least recently used entries from a tier."""
        entries = self._cache.get(tier, {})
        if not entries:
            return

        # Remove expired first
        expired = [k for k, e in entries.items() if e.is_expired]
        for k in expired:
            del entries[k]
            self._stats[tier].evictions += 1

        # If still over limit, remove lowest hit count
        if len(entries) >= self._max_size // len(self._cache):
            sorted_entries = sorted(entries.items(), key=lambda x: x[1].hits)
            to_remove = sorted_entries[:max(1, len(sorted_entries) // 4)]
            for k, _ in to_remove:
                del entries[k]
                self._stats[tier].evictions += 1

    # ── STATS ──

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            tier_sizes = {tier: len(entries) for tier, entries in self._cache.items()}
            tier_stats = {tier: stats.summary() for tier, stats in self._stats.items()}

            total_size = sum(tier_sizes.values())
            total_hits = sum(s.hits for s in self._stats.values())
            total_misses = sum(s.misses for s in self._stats.values())
            total = total_hits + total_misses

            return {
                'total_entries': total_size,
                'max_size': self._max_size,
                'hit_rate': round(total_hits / total, 3) if total > 0 else 0.0,
                'tiers': {
                    tier: {
                        'size': tier_sizes.get(tier, 0),
                        'stats': tier_stats.get(tier, {}),
                    }
                    for tier in self._cache
                },
            }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            for stats in self._stats.values():
                stats.hits = 0
                stats.misses = 0
                stats.invalidations = 0
                stats.evictions = 0

    # ── CONVENIENCE METHODS ──

    def get_retrieval(self, query_hash: str) -> Optional[str]:
        return self.get('retrieval', query_hash)

    def put_retrieval(self, query_hash: str, context: str, dependencies: Set[str]) -> None:
        self.put('retrieval', query_hash, context, dependencies)

    def get_validation(self, file_hash: str) -> Optional[List]:
        return self.get('validation', file_hash)

    def put_validation(self, file_hash: str, issues: List) -> None:
        self.put('validation', file_hash, issues, {file_hash})

    def get_symbol(self, symbol_name: str) -> Optional[List]:
        return self.get('symbol', symbol_name)

    def put_symbol(self, symbol_name: str, locations: List, dependencies: Set[str]) -> None:
        self.put('symbol', symbol_name, locations, dependencies)

    def get_impact(self, file_path: str) -> Optional[List]:
        return self.get('impact', file_path)

    def put_impact(self, file_path: str, affected: List, dependencies: Set[str]) -> None:
        self.put('impact', file_path, affected, dependencies)

    def get_test(self, file_path: str) -> Optional[List]:
        return self.get('test', file_path)

    def put_test(self, file_path: str, tests: List, dependencies: Set[str]) -> None:
        self.put('test', file_path, tests, dependencies)
