"""
P6 — Engineering Memory System.

Structured engineering memory — NOT LLM hallucinations.
Stores facts about the project engineering history.

Memory types:
- Architectural decisions (why we chose X)
- Recurring failures (what keeps breaking)
- Successful fixes (what worked)
- Unstable modules (what's fragile)
- Risky workflows (what needs care)
- Historical regressions (what broke before)
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class MemoryType(Enum):
    ARCH_DECISION = "architectural_decision"
    RECURRING_FAILURE = "recurring_failure"
    SUCCESSFUL_FIX = "successful_fix"
    UNSTABLE_MODULE = "unstable_module"
    RISKY_WORKFLOW = "risky_workflow"
    HISTORICAL_REGRESSION = "historical_regression"
    DOMAIN_RULE = "domain_rule"


@dataclass
class MemoryEntry:
    """A single structured memory entry."""
    id: str
    memory_type: MemoryType
    title: str
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    source: str = ""  # what created this memory
    confidence: float = 1.0  # 0.0 to 1.0
    created_at: float = 0.0
    updated_at: float = 0.0
    access_count: int = 0
    last_accessed: float = 0.0
    is_stale: bool = False


class EngineeringMemorySystem:
    """
    Structured engineering memory.
    Only facts. No AI hallucinations.
    """

    def __init__(self):
        self._memories: Dict[str, MemoryEntry] = {}
        self._by_type: Dict[MemoryType, List[str]] = defaultdict(list)
        self._by_tag: Dict[str, List[str]] = defaultdict(list)
        self._by_module: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()
        self._max_memories = 100000

    def add_memory(self, memory_type: MemoryType, title: str, content: str,
                   context: Dict[str, Any] = None, tags: List[str] = None,
                   source: str = "", confidence: float = 1.0,
                   module: str = "") -> MemoryEntry:
        """Add a memory entry."""
        import uuid
        entry = MemoryEntry(
            id=str(uuid.uuid4())[:8],
            memory_type=memory_type,
            title=title,
            content=content,
            context=context or {},
            tags=tags or [],
            source=source,
            confidence=confidence,
            created_at=time.time(),
            updated_at=time.time(),
        )

        with self._lock:
            self._memories[entry.id] = entry
            self._by_type[memory_type].append(entry.id)
            for tag in entry.tags:
                self._by_tag[tag].append(entry.id)
            if module:
                self._by_module[module].append(entry.id)

            if len(self._memories) > self._max_memories:
                self._evict_oldest()

        return entry

    def recall(self, memory_id: str) -> Optional[MemoryEntry]:
        """Recall a memory by ID."""
        entry = self._memories.get(memory_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
        return entry

    def search(self, query: str = "", memory_type: MemoryType = None,
               tags: List[str] = None, module: str = "",
               min_confidence: float = 0.0,
               limit: int = 20) -> List[MemoryEntry]:
        """Search memories by criteria."""
        results = []

        # Start with type filter if provided
        if memory_type:
            ids = set(self._by_type.get(memory_type, []))
            candidates = [self._memories[mid] for mid in ids if mid in self._memories]
        elif module:
            ids = set(self._by_module.get(module, []))
            candidates = [self._memories[mid] for mid in ids if mid in self._memories]
        elif tags:
            ids = set()
            for tag in tags:
                ids.update(self._by_tag.get(tag, []))
            candidates = [self._memories[mid] for mid in ids if mid in self._memories]
        else:
            candidates = list(self._memories.values())

        # Apply filters
        for entry in candidates:
            if entry.confidence < min_confidence:
                continue
            if entry.is_stale:
                continue
            if query and query.lower() not in entry.title.lower() and query.lower() not in entry.content.lower():
                continue
            results.append(entry)

        # Sort by relevance (confidence * recency * access_count)
        now = time.time()
        results.sort(key=lambda e: (
            e.confidence * 0.4 +
            (1.0 / (1.0 + (now - e.updated_at) / 86400)) * 0.3 +
            min(e.access_count / 10.0, 1.0) * 0.3
        ), reverse=True)

        return results[:limit]

    def get_module_memories(self, module: str) -> List[MemoryEntry]:
        """Get all memories related to a module."""
        ids = self._by_module.get(module, [])
        return [self._memories[mid] for mid in ids if mid in self._memories]

    def get_unstable_modules(self) -> List[Dict[str, Any]]:
        """Get modules marked as unstable."""
        results = []
        for mid in self._by_type.get(MemoryType.UNSTABLE_MODULE, []):
            entry = self._memories.get(mid)
            if entry:
                results.append({
                    'module': entry.context.get('module', entry.title),
                    'reason': entry.content,
                    'since': entry.created_at,
                    'incidents': entry.context.get('incident_count', 1),
                })
        return results

    def get_recurring_failures(self) -> List[Dict[str, Any]]:
        """Get recurring failure patterns."""
        results = []
        for mid in self._by_type.get(MemoryType.RECURRING_FAILURE, []):
            entry = self._memories.get(mid)
            if entry:
                results.append({
                    'pattern': entry.title,
                    'description': entry.content,
                    'occurrences': entry.context.get('count', 1),
                    'last_seen': entry.updated_at,
                })
        return results

    def mark_stale(self, memory_id: str) -> bool:
        """Mark a memory as stale."""
        entry = self._memories.get(memory_id)
        if entry:
            entry.is_stale = True
            entry.updated_at = time.time()
            return True
        return False

    def update_memory(self, memory_id: str, content: str = None,
                      context: Dict[str, Any] = None,
                      confidence: float = None) -> bool:
        """Update a memory entry."""
        entry = self._memories.get(memory_id)
        if not entry:
            return False
        if content is not None:
            entry.content = content
        if context is not None:
            entry.context.update(context)
        if confidence is not None:
            entry.confidence = confidence
        entry.updated_at = time.time()
        return True

    def _evict_oldest(self) -> None:
        """Evict oldest, least accessed memories."""
        if len(self._memories) <= self._max_memories * 0.9:
            return
        # Remove bottom 10% by (access_count, last_accessed)
        sorted_entries = sorted(
            self._memories.values(),
            key=lambda e: (e.access_count, e.last_accessed or e.created_at)
        )
        to_remove = sorted_entries[:max(1, len(sorted_entries) // 10)]
        for entry in to_remove:
            del self._memories[entry.id]

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        by_type = defaultdict(int)
        for entry in self._memories.values():
            by_type[entry.memory_type.value] += 1

        return {
            'total_memories': len(self._memories),
            'by_type': dict(by_type),
            'total_tags': len(self._by_tag),
            'total_modules': len(self._by_module),
            'stale_count': sum(1 for e in self._memories.values() if e.is_stale),
        }
