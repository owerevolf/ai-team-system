"""
memory_governor.py — Memory Growth Control.

Memory can also degrade. The governor must:
1. Detect memory bloat
2. Merge duplicate summaries
3. Archive stale memory
4. Remove dead knowledge
5. Prevent contradiction growth
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger


@dataclass
class GovernorAction:
    """A governor action on memory."""
    action: str = ""  # merge, archive, remove, compress
    target: str = ""
    reason: str = ""
    timestamp: str = ""
    items_affected: int = 0


class MemoryGovernor:
    """
    Controls memory growth and quality.
    Prevents memory from becoming a liability.
    """

    # Thresholds
    MAX_SUBSYSTEMS = 50
    MAX_FAILURES = 500
    MAX_FRAGILE_AREAS = 100
    MAX_FROZEN_ZONES = 50
    MAX_HISTORY_ITEMS = 200
    STALE_AGE_DAYS = 30
    DUPLICATE_SIMILARITY_THRESHOLD = 0.8

    def __init__(self):
        self._actions: List[GovernorAction] = []
        self._lock = threading.Lock()
        self._last_run = 0.0

    def govern(self, memory_data: Dict[str, Any]) -> List[GovernorAction]:
        """
        Run all governance checks on memory data.
        Returns list of actions taken.
        """
        actions = []

        with self._lock:
            actions.extend(self._check_bloat(memory_data))
            actions.extend(self._check_duplicates(memory_data))
            actions.extend(self._check_stale(memory_data))
            actions.extend(self._check_contradictions(memory_data))
            actions.extend(self._check_dead_references(memory_data))

            self._actions.extend(actions)
            self._last_run = time.time()

        if actions:
            logger.info(f"Memory governor: {len(actions)} actions taken")
            for a in actions:
                logger.debug(f"  {a.action}: {a.target} ({a.reason})")

        return actions

    def _check_bloat(self, memory_data: Dict[str, Any]) -> List[GovernorAction]:
        """Check for memory bloat."""
        actions = []

        subsystems = memory_data.get("subsystems", {})
        if len(subsystems) > self.MAX_SUBSYSTEMS:
            actions.append(GovernorAction(
                action="compress",
                target="subsystems",
                reason=f"Too many subsystems: {len(subsystems)} > {self.MAX_SUBSYSTEMS}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                items_affected=len(subsystems) - self.MAX_SUBSYSTEMS,
            ))

        failures = memory_data.get("failures", {})
        if len(failures) > self.MAX_FAILURES:
            actions.append(GovernorAction(
                action="archive",
                target="failures",
                reason=f"Too many failure records: {len(failures)} > {self.MAX_FAILURES}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                items_affected=len(failures) - self.MAX_FAILURES,
            ))

        fragile = memory_data.get("fragile_areas", [])
        if len(fragile) > self.MAX_FRAGILE_AREAS:
            actions.append(GovernorAction(
                action="compress",
                target="fragile_areas",
                reason=f"Too many fragile areas: {len(fragile)} > {self.MAX_FRAGILE_AREAS}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                items_affected=len(fragile) - self.MAX_FRAGILE_AREAS,
            ))

        return actions

    def _check_duplicates(self, memory_data: Dict[str, Any]) -> List[GovernorAction]:
        """Check for duplicate or near-duplicate entries."""
        actions = []

        # Check for duplicate fragile areas
        fragile = memory_data.get("fragile_areas", [])
        seen_areas: Set[str] = set()
        duplicates = []
        for area in fragile:
            area_name = area.get("area", "")
            if area_name in seen_areas:
                duplicates.append(area_name)
            seen_areas.add(area_name)

        if duplicates:
            actions.append(GovernorAction(
                action="merge",
                target="fragile_areas",
                reason=f"Duplicate fragile areas: {', '.join(duplicates[:5])}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                items_affected=len(duplicates),
            ))

        # Check for duplicate failures
        failures = memory_data.get("failures", {})
        seen_signatures: Set[str] = set()
        dup_failures = []
        for fid, f in failures.items():
            sig = f.get("signature", f"{f.get('failure_type', '')}:{f.get('description', '')}")
            if sig in seen_signatures:
                dup_failures.append(fid)
            seen_signatures.add(sig)

        if dup_failures:
            actions.append(GovernorAction(
                action="merge",
                target="failures",
                reason=f"Duplicate failure records: {len(dup_failures)}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                items_affected=len(dup_failures),
            ))

        return actions

    def _check_stale(self, memory_data: Dict[str, Any]) -> List[GovernorAction]:
        """Check for stale memory entries."""
        actions = []
        now = time.time()
        stale_threshold = self.STALE_AGE_DAYS * 86400

        # Check stale subsystems
        subsystems = memory_data.get("subsystems", {})
        stale_subs = []
        for name, sub in subsystems.items():
            last_updated = sub.get("last_updated", "")
            if last_updated:
                try:
                    updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    age = now - updated.timestamp()
                    if age > stale_threshold:
                        stale_subs.append(name)
                except (ValueError, TypeError):
                    pass

        if stale_subs:
            actions.append(GovernorAction(
                action="archive",
                target="subsystems",
                reason=f"Stale subsystems: {', '.join(stale_subs[:5])}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                items_affected=len(stale_subs),
            ))

        return actions

    def _check_contradictions(self, memory_data: Dict[str, Any]) -> List[GovernorAction]:
        """Check for contradictory memory entries."""
        actions = []

        # Check for contradictions between frozen zones and active tasks
        frozen = memory_data.get("frozen_zones", [])
        active_files = memory_data.get("active_files", [])

        for zone in frozen:
            zone_area = zone.get("area", "")
            for f in active_files:
                if zone_area in f or f in zone_area:
                    actions.append(GovernorAction(
                        action="remove",
                        target=f"active_file:{f}",
                        reason=f"Active file {f} is in frozen zone {zone_area}",
                        timestamp=datetime.utcnow().isoformat() + "Z",
                    ))

        return actions

    def _check_dead_references(self, memory_data: Dict[str, Any]) -> List[GovernorAction]:
        """Check for references to deleted/moved things."""
        actions = []

        # Check for failure records referencing non-existent files
        failures = memory_data.get("failures", {})
        dead_refs = []
        for fid, f in failures.items():
            files = f.get("files_involved", [])
            # We can't check file existence here without project_root
            # But we can check for obviously invalid paths
            for fpath in files:
                if not fpath or fpath.strip() == "":
                    dead_refs.append(fid)
                    break

        if dead_refs:
            actions.append(GovernorAction(
                action="remove",
                target="failures",
                reason=f"Failure records with empty file references: {len(dead_refs)}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                items_affected=len(dead_refs),
            ))

        return actions

    def get_actions(self, limit: int = 50) -> List[GovernorAction]:
        """Get recent governor actions."""
        return self._actions[-limit:]

    def clear_actions(self) -> None:
        """Clear action history."""
        with self._lock:
            self._actions.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get governor statistics."""
        with self._lock:
            actions = list(self._actions)

        by_action: Dict[str, int] = {}
        for a in actions:
            by_action[a.action] = by_action.get(a.action, 0) + 1

        return {
            "total_actions": len(actions),
            "by_action": by_action,
            "last_run": self._last_run,
        }
