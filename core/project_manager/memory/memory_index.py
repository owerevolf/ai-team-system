"""
memory_index.py — Engineering Knowledge Index.

Stores:
- module summaries
- subsystem summaries
- ADR references
- known risks
- important constraints
- hot files
- frequently modified areas
- historical failures
- frozen zones

Search:
- semantic lookup
- dependency-aware lookup
- risk-aware lookup
- architecture-aware lookup
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class MemoryEntry:
    """A single memory index entry."""
    entry_id: str = ""
    category: str = ""  # module, subsystem, adr, risk, constraint, hot_file, failure, frozen_zone
    key: str = ""
    summary: str = ""
    importance: int = 5  # 1-10
    source: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    is_stale: bool = False
    access_count: int = 0


class MemoryIndex:
    """
    Index of engineering knowledge.
    Provides fast lookup of project knowledge.
    """

    def __init__(self):
        self._entries: Dict[str, MemoryEntry] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_tag: Dict[str, List[str]] = {}
        self._by_importance: Dict[int, List[str]] = {}
        self._lock = threading.Lock()

    def add_entry(self, category: str, key: str, summary: str,
                  importance: int = 5, source: str = "",
                  tags: Optional[List[str]] = None,
                  entry_id: str = "") -> MemoryEntry:
        """Add a memory entry."""
        with self._lock:
            import uuid
            eid = entry_id or f"mem-{len(self._entries) + 1}"
            now = datetime.utcnow().isoformat() + "Z"

            entry = MemoryEntry(
                entry_id=eid, category=category, key=key,
                summary=summary, importance=importance,
                source=source, tags=tags or [],
                created_at=now, updated_at=now,
            )

            self._entries[eid] = entry
            self._by_category.setdefault(category, []).append(eid)
            for tag in entry.tags:
                self._by_tag.setdefault(tag, []).append(eid)
            self._by_importance.setdefault(importance, []).append(eid)

            return entry

    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get an entry by ID."""
        entry = self._entries.get(entry_id)
        if entry:
            entry.access_count += 1
        return entry

    def search(self, query: str = "", category: str = "",
               tags: Optional[List[str]] = None,
               min_importance: int = 0,
               limit: int = 20) -> List[MemoryEntry]:
        """Search memory entries."""
        with self._lock:
            candidates = list(self._entries.values())

        # Filter
        if category:
            candidates = [e for e in candidates if e.category == category]
        if tags:
            candidates = [e for e in candidates
                          if any(t in e.tags for t in tags)]
        if min_importance > 0:
            candidates = [e for e in candidates
                          if e.importance >= min_importance]

        # Text search
        if query:
            q = query.lower()
            filtered = []
            for e in candidates:
                if (q in e.key.lower() or
                    q in e.summary.lower() or
                    any(q in t.lower() for t in e.tags)):
                    filtered.append(e)
            candidates = filtered

        # Sort by importance desc, then access count desc
        candidates.sort(key=lambda e: (e.importance, e.access_count), reverse=True)

        return candidates[:limit]

    def semantic_lookup(self, concept: str) -> List[MemoryEntry]:
        """Semantic lookup — find entries related to a concept."""
        return self.search(query=concept)

    def dependency_lookup(self, module: str) -> List[MemoryEntry]:
        """Find entries related to a module's dependencies."""
        return self.search(query=module, tags=["dependency"])

    def risk_lookup(self, area: str = "") -> List[MemoryEntry]:
        """Find risk-related entries."""
        if area:
            return self.search(query=area, category="risk")
        return self.search(category="risk", min_importance=7)

    def architecture_lookup(self, subsystem: str = "") -> List[MemoryEntry]:
        """Find architecture-related entries."""
        if subsystem:
            return self.search(query=subsystem, category="subsystem")
        return self.search(category="subsystem")

    def get_hot_files(self, limit: int = 10) -> List[MemoryEntry]:
        """Get hot files."""
        return self.search(category="hot_file", limit=limit)

    def get_frozen_zones(self) -> List[MemoryEntry]:
        """Get frozen zones."""
        return self.search(category="frozen_zone")

    def get_known_risks(self, limit: int = 20) -> List[MemoryEntry]:
        """Get known risks."""
        return self.search(category="risk", min_importance=5, limit=limit)

    def mark_stale(self, entry_id: str) -> bool:
        """Mark an entry as stale."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry:
                entry.is_stale = True
                return True
            return False

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry."""
        with self._lock:
            entry = self._entries.pop(entry_id, None)
            if entry:
                # Clean up indexes
                if entry.category in self._by_category:
                    self._by_category[entry.category] = [
                        eid for eid in self._by_category[entry.category]
                        if eid != entry_id
                    ]
                for tag in entry.tags:
                    if tag in self._by_tag:
                        self._by_tag[tag] = [
                            eid for eid in self._by_tag[tag]
                            if eid != entry_id
                        ]
                return True
            return False

    def get_entries_by_category(self, category: str) -> List[MemoryEntry]:
        """Get all entries in a category."""
        with self._lock:
            ids = self._by_category.get(category, [])
            return [self._entries[eid] for eid in ids if eid in self._entries]

    def get_all_entries(self) -> List[MemoryEntry]:
        """Get all entries."""
        return list(self._entries.values())

    def build_context_summary(self, max_entries: int = 30) -> str:
        """Build a context summary from the index."""
        entries = self.search(min_importance=7, limit=max_entries)

        if not entries:
            return "No significant project knowledge indexed."

        lines = ["# Project Knowledge Index", ""]

        by_cat: Dict[str, List[MemoryEntry]] = {}
        for e in entries:
            by_cat.setdefault(e.category, []).append(e)

        for cat, cat_entries in by_cat.items():
            lines.append(f"## {cat.upper()}")
            for e in cat_entries:
                lines.append(f"- {e.key}: {e.summary[:100]}")
            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self._lock:
            entries = list(self._entries.values())

        by_category: Dict[str, int] = {}
        for e in entries:
            by_category[e.category] = by_category.get(e.category, 0) + 1

        return {
            "total_entries": len(entries),
            "by_category": by_category,
            "total_tags": len(self._by_tag),
            "stale_entries": sum(1 for e in entries if e.is_stale),
            "high_importance": sum(1 for e in entries if e.importance >= 8),
        }
