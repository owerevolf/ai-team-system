"""
P1 — Runtime State Lifecycle Management (Phase 9)

Manages state across four tiers:
  - Ephemeral: minutes/hours (temp reasoning, active prompts, drafts)
  - Session: days/weeks (active tasks, touched files, checkpoints)
  - Operational: months (approvals, successful workflows, resolved failures)
  - Structural: persistent (architecture map, dependency graph, contracts)

Key principle: state must age, not just accumulate.
"""

from __future__ import annotations

import time
import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from pathlib import Path


class StateTier(Enum):
    EPHEMERAL = "ephemeral"       # TTL: minutes/hours
    SESSION = "session"           # TTL: days/weeks
    OPERATIONAL = "operational"   # TTL: months
    STRUCTURAL = "structural"     # TTL: persistent


# Default TTLs in seconds
DEFAULT_TTLS: dict[StateTier, float] = {
    StateTier.EPHEMERAL: 3600,        # 1 hour
    StateTier.SESSION: 604800,        # 7 days
    StateTier.OPERATIONAL: 2592000,   # 30 days
    StateTier.STRUCTURAL: 0,          # never expires
}


@dataclass
class StateEntry:
    """A single state entry with tier and TTL."""
    key: str
    value: Any
    tier: StateTier
    created_at: float = 0.0
    accessed_at: float = 0.0
    ttl_seconds: float = 0.0
    access_count: int = 0
    compressed: bool = False

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        if not self.accessed_at:
            self.accessed_at = self.created_at
        if not self.ttl_seconds:
            self.ttl_seconds = DEFAULT_TTLS.get(self.tier, 0)

    @property
    def is_expired(self) -> bool:
        if self.tier == StateTier.STRUCTURAL:
            return False
        if self.ttl_seconds <= 0:
            return False
        return (time.time() - self.accessed_at) > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def staleness(self) -> float:
        """0.0 = fresh, 1.0 = expired."""
        if self.tier == StateTier.STRUCTURAL:
            return 0.0
        if self.ttl_seconds <= 0:
            return 0.0
        elapsed = time.time() - self.accessed_at
        return min(1.0, elapsed / self.ttl_seconds)

    def touch(self) -> None:
        self.accessed_at = time.time()
        self.access_count += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "tier": self.tier.value,
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "ttl_seconds": self.ttl_seconds,
            "access_count": self.access_count,
            "is_expired": self.is_expired,
            "staleness": round(self.staleness, 3),
            "compressed": self.compressed,
        }


class StateLifecycleManager:
    """
    Manages runtime state with tiered lifecycle.

    Usage:
        mgr = StateLifecycleManager("/path/to/project")
        mgr.put("active_task", task_data, StateTier.SESSION)
        mgr.put("temp_plan", plan_data, StateTier.EPHEMERAL)
        mgr.put("arch_map", arch_data, StateTier.STRUCTURAL)

        # Automatic cleanup of expired entries
        mgr.cleanup()

        # Promote/demote entries as they age
        mgr.promote("active_task", StateTier.OPERATIONAL)
    """

    def __init__(self, project_path: str, persist_dir: Optional[str] = None) -> None:
        self.project_path = project_path
        self._state: dict[str, StateEntry] = {}
        self._persist_dir = persist_dir or os.path.join(project_path, ".ai-team", "state")
        os.makedirs(self._persist_dir, exist_ok=True)
        self._load_persistent()

    def put(self, key: str, value: Any, tier: StateTier, ttl: float = 0) -> StateEntry:
        """Store a state entry."""
        entry = StateEntry(
            key=key,
            value=value,
            tier=tier,
            ttl_seconds=ttl or DEFAULT_TTLS.get(tier, 0),
        )
        self._state[key] = entry
        if tier in (StateTier.OPERATIONAL, StateTier.STRUCTURAL):
            self._persist_entry(entry)
        return entry

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a state entry's value. Returns default if expired."""
        entry = self._state.get(key)
        if entry is None:
            return default
        if entry.is_expired:
            return default
        entry.touch()
        return entry.value

    def get_entry(self, key: str) -> Optional[StateEntry]:
        """Get the full StateEntry (metadata + value)."""
        entry = self._state.get(key)
        if entry and not entry.is_expired:
            entry.touch()
            return entry
        return None

    def remove(self, key: str) -> bool:
        """Remove a state entry."""
        if key in self._state:
            del self._state[key]
            self._remove_persisted(key)
            return True
        return False

    def promote(self, key: str, new_tier: StateTier) -> bool:
        """Promote an entry to a higher-persistence tier."""
        entry = self._state.get(key)
        if not entry:
            return False
        entry.tier = new_tier
        entry.ttl_seconds = DEFAULT_TTLS.get(new_tier, 0)
        entry.touch()
        if new_tier in (StateTier.OPERATIONAL, StateTier.STRUCTURAL):
            self._persist_entry(entry)
        return True

    def demote(self, key: str, new_tier: StateTier) -> bool:
        """Demote an entry to a lower-persistence tier."""
        return self.promote(key, new_tier)

    def cleanup(self) -> dict[str, int]:
        """
        Remove expired entries. Returns counts by tier.
        """
        removed: dict[str, int] = {}
        to_remove = [k for k, v in self._state.items() if v.is_expired]
        for key in to_remove:
            tier = self._state[key].tier.value
            removed[tier] = removed.get(tier, 0) + 1
            del self._state[key]
            self._remove_persisted(key)
        return removed

    def get_tier_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics per tier."""
        stats: dict[str, dict] = {}
        for tier in StateTier:
            entries = [e for e in self._state.values() if e.tier == tier]
            expired = sum(1 for e in entries if e.is_expired)
            total_access = sum(e.access_count for e in entries)
            avg_staleness = (
                sum(e.staleness for e in entries) / len(entries)
                if entries else 0.0
            )
            stats[tier.value] = {
                "total": len(entries),
                "expired": expired,
                "active": len(entries) - expired,
                "total_access_count": total_access,
                "avg_staleness": round(avg_staleness, 3),
            }
        return stats

    def get_all_keys(self, tier: Optional[StateTier] = None, include_expired: bool = False) -> list[str]:
        """Get all state keys, optionally filtered by tier."""
        results = []
        for key, entry in self._state.items():
            if tier and entry.tier != tier:
                continue
            if not include_expired and entry.is_expired:
                continue
            results.append(key)
        return results

    def _persist_entry(self, entry: StateEntry) -> None:
        """Persist an entry to disk."""
        try:
            path = os.path.join(self._persist_dir, f"{entry.key}.json")
            fd, tmp = tempfile.mkstemp(dir=self._persist_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump({"key": entry.key, "value": entry.value, "tier": entry.tier.value}, f)
                os.replace(tmp, path)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        except Exception:
            pass

    def _remove_persisted(self, key: str) -> None:
        """Remove a persisted entry from disk."""
        try:
            path = os.path.join(self._persist_dir, f"{key}.json")
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    def _load_persistent(self) -> None:
        """Load persisted state from disk."""
        if not os.path.isdir(self._persist_dir):
            return
        for fname in os.listdir(self._persist_dir):
            if not fname.endswith(".json"):
                continue
            try:
                path = os.path.join(self._persist_dir, fname)
                with open(path, "r") as f:
                    data = json.load(f)
                tier = StateTier(data.get("tier", "operational"))
                entry = StateEntry(
                    key=data["key"],
                    value=data["value"],
                    tier=tier,
                )
                if not entry.is_expired:
                    self._state[entry.key] = entry
            except Exception:
                continue
