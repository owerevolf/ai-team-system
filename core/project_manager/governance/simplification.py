"""
P17 — Runtime Simplification Detector.

Detects when the system has become unnecessarily complex:
- Dead features (never used)
- Unused workflows
- Duplicate services
- Stale policies
- Redundant validation chains
- Abandoned modules
"""

import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class DeadItemSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DeadItem:
    """A detected dead/unused item."""
    item_type: str  # feature, workflow, service, policy, validation_chain, module
    name: str
    location: str
    severity: DeadItemSeverity
    message: str
    suggestion: str


class RuntimeSimplificationDetector:
    """
    Detects unnecessary complexity in the platform.
    Suggests simplifications.
    """

    def __init__(self):
        self._usage_counts: Dict[str, int] = defaultdict(int)
        self._last_accessed: Dict[str, float] = {}
        self._registered_items: Dict[str, Dict[str, Any]] = {}

    def register_item(self, item_type: str, name: str, location: str,
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register an item for tracking."""
        key = f"{item_type}:{name}"
        self._registered_items[key] = {
            'type': item_type,
            'name': name,
            'location': location,
            'metadata': metadata or {},
            'registered_at': time.time(),
        }

    def record_usage(self, item_type: str, name: str) -> None:
        """Record that an item was used."""
        key = f"{item_type}:{name}"
        self._usage_counts[key] += 1
        self._last_accessed[key] = time.time()

    def detect_dead_features(self, threshold_days: int = 30) -> List[DeadItem]:
        """Detect features that haven't been used in a while."""
        dead = []
        now = time.time()
        threshold_seconds = threshold_days * 86400

        for key, info in self._registered_items.items():
            last_access = self._last_accessed.get(key, info['registered_at']) or 0.0
            usage = self._usage_counts.get(key, 0)

            if usage == 0 and (now - info['registered_at']) > threshold_seconds:
                dead.append(DeadItem(
                    item_type=info['type'],
                    name=info['name'],
                    location=info['location'],
                    severity=DeadItemSeverity.WARNING,
                    message=f"Item '{info['name']}' never used since registration",
                    suggestion=f"Consider removing {info['location']}"
                ))
            elif usage > 0 and (now - last_access) > threshold_seconds:
                dead.append(DeadItem(
                    item_type=info['type'],
                    name=info['name'],
                    location=info['location'],
                    severity=DeadItemSeverity.INFO,
                    message=f"Item '{info['name']}' not used in {threshold_days} days",
                    suggestion=f"Review if still needed: {info['location']}"
                ))

        return dead

    def detect_duplicate_services(self) -> List[DeadItem]:
        """Detect potentially duplicate services."""
        dead = []
        # Group by type
        by_type: Dict[str, List[Dict]] = defaultdict(list)
        for key, info in self._registered_items.items():
            by_type[info['type']].append(info)

        # Check for items with similar names
        for item_type, items in by_type.items():
            for i, item_a in enumerate(items):
                for item_b in items[i + 1:]:
                    # Simple similarity: shared prefix
                    name_a = item_a['name'].lower()
                    name_b = item_b['name'].lower()
                    if name_a[:4] == name_b[:4] and name_a != name_b:
                        dead.append(DeadItem(
                            item_type=item_type,
                            name=f"{item_a['name']} / {item_b['name']}",
                            location=f"{item_a['location']}, {item_b['location']}",
                            severity=DeadItemSeverity.INFO,
                            message=f"Potentially duplicate: {item_a['name']} and {item_b['name']}",
                            suggestion="Review if these can be consolidated"
                        ))

        return dead

    def detect_stale_policies(self, policy_usage: Dict[str, int],
                              threshold_days: int = 60) -> List[DeadItem]:
        """Detect policies that are never triggered."""
        dead = []
        for key, info in self._registered_items.items():
            if info['type'] == 'policy':
                usage = policy_usage.get(info['name'], 0)
                if usage == 0:
                    dead.append(DeadItem(
                        item_type='policy',
                        name=info['name'],
                        location=info['location'],
                        severity=DeadItemSeverity.INFO,
                        message=f"Policy '{info['name']}' never triggered",
                        suggestion=f"Review if policy is still relevant: {info['location']}"
                    ))
        return dead

    def detect_abandoned_modules(self, project_path: Path,
                                  threshold_days: int = 90) -> List[DeadItem]:
        """Detect modules that haven't been modified in a long time."""
        dead = []
        now = time.time()
        threshold_seconds = threshold_days * 86400

        for f in project_path.rglob("*.py"):
            if "__pycache__" in str(f) or "venv" in str(f) or "test" in str(f):
                continue
            try:
                mtime = f.stat().st_mtime
                if (now - mtime) > threshold_seconds:
                    rel = str(f.relative_to(project_path))
                    dead.append(DeadItem(
                        item_type='module',
                        name=f.name,
                        location=rel,
                        severity=DeadItemSeverity.INFO,
                        message=f"Module not modified in {threshold_days} days",
                        suggestion=f"Review if still needed: {rel}"
                    ))
            except OSError:
                pass

        return dead

    def get_simplification_report(self, project_path: Optional[Path] = None) -> Dict[str, Any]:
        """Get a full simplification report."""
        dead_features = self.detect_dead_features()
        duplicates = self.detect_duplicate_services()
        abandoned = self.detect_abandoned_modules(project_path) if project_path else []

        all_items = dead_features + duplicates + abandoned
        by_severity = defaultdict(list)
        for item in all_items:
            by_severity[item.severity.value].append({
                'type': item.item_type,
                'name': item.name,
                'location': item.location,
                'message': item.message,
                'suggestion': item.suggestion,
            })

        return {
            'total_items_tracked': len(self._registered_items),
            'total_dead_items': len(all_items),
            'by_severity': dict(by_severity),
            'recommendations': list(set(item.suggestion for item in all_items)),
        }
