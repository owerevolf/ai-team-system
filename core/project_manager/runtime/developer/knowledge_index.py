"""
Knowledge Index — context compression system.

LLM does NOT read the entire repo.
Only compressed scoped context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeEntry:
    """A single piece of knowledge about the project."""
    entry_id: str = ""
    category: str = ""  # architecture, module, symbol, adr, constraint, history
    key: str = ""
    summary: str = ""
    importance: int = 5  # 1-10, higher = more important
    source: str = ""  # file, decision, scan
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeIndex:
    """
    Compressed knowledge about the project.

    Stores:
    - architecture summaries
    - symbol summaries
    - module summaries
    - hot files
    - recent changes
    - ADR summaries
    - important constraints
    - execution history
    """

    def __init__(self, project_id: str = ""):
        self.project_id = project_id
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._created_at = datetime.utcnow().isoformat() + "Z"

    def add_entry(self, category: str, key: str, summary: str,
                  importance: int = 5, source: str = "",
                  metadata: Optional[Dict] = None) -> KnowledgeEntry:
        """Add a knowledge entry."""
        entry = KnowledgeEntry(
            entry_id=f"k{len(self._entries) + 1}",
            category=category,
            key=key,
            summary=summary,
            importance=importance,
            source=source,
            created_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
            metadata=metadata or {},
        )
        self._entries[entry.entry_id] = entry
        return entry

    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self._entries.get(entry_id)

    def get_entries_by_category(self, category: str) -> List[KnowledgeEntry]:
        return [e for e in self._entries.values() if e.category == category]

    def get_entries_by_importance(self, min_importance: int = 7) -> List[KnowledgeEntry]:
        return [e for e in self._entries.values()
                if e.importance >= min_importance]

    def search(self, query: str) -> List[KnowledgeEntry]:
        """Simple keyword search."""
        q = query.lower()
        results = []
        for entry in self._entries.values():
            if (q in entry.key.lower() or
                q in entry.summary.lower() or
                q in entry.category.lower()):
                results.append(entry)
        results.sort(key=lambda e: e.importance, reverse=True)
        return results

    def build_context(self, max_entries: int = 20,
                      categories: Optional[List[str]] = None) -> str:
        """
        Build compressed context for LLM consumption.

        Only includes the most important entries.
        """
        entries = list(self._entries.values())

        if categories:
            entries = [e for e in entries if e.category in categories]

        # Sort by importance
        entries.sort(key=lambda e: e.importance, reverse=True)
        entries = entries[:max_entries]

        if not entries:
            return "No project knowledge available."

        lines = ["# Project Knowledge (Compressed)", ""]

        # Group by category
        by_cat: Dict[str, List[KnowledgeEntry]] = {}
        for e in entries:
            by_cat.setdefault(e.category, []).append(e)

        for cat, cat_entries in by_cat.items():
            lines.append(f"## {cat.upper()}")
            for e in cat_entries:
                lines.append(f"- {e.key}: {e.summary}")
            lines.append("")

        return "\n".join(lines)

    def add_architecture_summary(self, summary: str) -> KnowledgeEntry:
        return self.add_entry("architecture", "system_architecture",
                              summary, importance=10, source="scan")

    def add_module_summary(self, module_name: str, summary: str) -> KnowledgeEntry:
        return self.add_entry("module", module_name, summary,
                              importance=7, source="scan")

    def add_adr(self, title: str, decision: str) -> KnowledgeEntry:
        return self.add_entry("adr", title, decision,
                              importance=9, source="decision")

    def add_constraint(self, rule: str) -> KnowledgeEntry:
        return self.add_entry("constraint", rule, rule,
                              importance=8, source="constraint")

    def add_hot_file(self, file_path: str, reason: str) -> KnowledgeEntry:
        return self.add_entry("hot_file", file_path, reason,
                              importance=6, source="analysis")

    def add_execution_history(self, task: str, outcome: str) -> KnowledgeEntry:
        return self.add_entry("history", task, outcome,
                              importance=5, source="execution")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "total_entries": len(self._entries),
            "created_at": self._created_at,
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "category": e.category,
                    "key": e.key,
                    "summary": e.summary,
                    "importance": e.importance,
                }
                for e in self._entries.values()
            ],
        }
