"""
failure_memory.py — Error Memory.

Runtime must remember errors to avoid repeating them.

Stores:
- repeated failures
- fragile tests
- rollback incidents
- failed migrations
- dangerous files
- regression hotspots
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class FailurePattern:
    """A recognized failure pattern."""
    pattern_id: str = ""
    failure_type: str = ""
    description: str = ""
    signature: str = ""  # unique signature for matching
    occurrences: int = 0
    first_seen: str = ""
    last_seen: str = ""
    files_involved: List[str] = field(default_factory=list)
    resolution: str = ""
    is_resolved: bool = False
    is_regression: bool = False


@dataclass
class FragileTest:
    """A known fragile test."""
    test_path: str = ""
    failure_count: int = 0
    last_failure: str = ""
    reason: str = ""
    is_quarantined: bool = False


@dataclass
class RegressionHotspot:
    """A file/module with frequent regressions."""
    area: str = ""
    regression_count: int = 0
    last_regression: str = ""
    common_causes: List[str] = field(default_factory=list)
    recommended_review: str = ""


class FailureMemory:
    """
    Remembers failures to avoid repeating them.
    """

    def __init__(self):
        self._patterns: Dict[str, FailurePattern] = {}
        self._fragile_tests: Dict[str, FragileTest] = {}
        self._hotspots: Dict[str, RegressionHotspot] = {}
        self._rollback_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record_failure(self, failure_type: str, description: str,
                       files_involved: Optional[List[str]] = None,
                       resolution: str = "") -> FailurePattern:
        """Record a failure, detecting patterns."""
        with self._lock:
            signature = f"{failure_type}:{description}"
            now = datetime.utcnow().isoformat() + "Z"

            existing = self._patterns.get(signature)
            if existing:
                existing.occurrences += 1
                existing.last_seen = now
                if resolution:
                    existing.resolution = resolution
                # Still update hotspots for recurring failures
                for f in (files_involved or []):
                    self._update_hotspot(f, failure_type)
                return existing

            import uuid
            pattern = FailurePattern(
                pattern_id=str(uuid.uuid4())[:8],
                failure_type=failure_type,
                description=description,
                signature=signature,
                occurrences=1,
                first_seen=now,
                last_seen=now,
                files_involved=files_involved or [],
                resolution=resolution,
            )
            self._patterns[signature] = pattern

            # Update hotspots
            for f in (files_involved or []):
                self._update_hotspot(f, failure_type)

            return pattern

    def _update_hotspot(self, area: str, cause: str) -> None:
        """Update a regression hotspot."""
        now = datetime.utcnow().isoformat() + "Z"
        existing = self._hotspots.get(area)
        if existing:
            existing.regression_count += 1
            existing.last_regression = now
            if cause not in existing.common_causes:
                existing.common_causes.append(cause)
        else:
            self._hotspots[area] = RegressionHotspot(
                area=area, regression_count=1,
                last_regression=now,
                common_causes=[cause],
            )

    def record_fragile_test(self, test_path: str, reason: str = "") -> FragileTest:
        """Record a fragile test."""
        with self._lock:
            now = datetime.utcnow().isoformat() + "Z"
            existing = self._fragile_tests.get(test_path)
            if existing:
                existing.failure_count += 1
                existing.last_failure = now
                return existing

            fragile = FragileTest(
                test_path=test_path, failure_count=1,
                last_failure=now, reason=reason,
            )
            self._fragile_tests[test_path] = fragile
            return fragile

    def quarantine_test(self, test_path: str) -> bool:
        """Quarantine a fragile test."""
        with self._lock:
            test = self._fragile_tests.get(test_path)
            if test:
                test.is_quarantined = True
                return True
            return False

    def record_rollback(self, task_id: str, reason: str,
                        files_affected: Optional[List[str]] = None) -> None:
        """Record a rollback incident."""
        with self._lock:
            self._rollback_log.append({
                "task_id": task_id,
                "reason": reason,
                "files_affected": files_affected or [],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            if len(self._rollback_log) > 100:
                self._rollback_log = self._rollback_log[-100:]

    def get_repeated_failures(self, min_occurrences: int = 2) -> List[FailurePattern]:
        """Get failure patterns that have occurred multiple times."""
        return sorted(
            [p for p in self._patterns.values() if p.occurrences >= min_occurrences],
            key=lambda p: p.occurrences, reverse=True,
        )

    def get_fragile_tests(self, include_quarantined: bool = False) -> List[FragileTest]:
        """Get fragile tests."""
        tests = list(self._fragile_tests.values())
        if not include_quarantined:
            tests = [t for t in tests if not t.is_quarantined]
        return sorted(tests, key=lambda t: t.failure_count, reverse=True)

    def get_hotspots(self, min_regressions: int = 2) -> List[RegressionHotspot]:
        """Get regression hotspots."""
        return sorted(
            [h for h in self._hotspots.values() if h.regression_count >= min_regressions],
            key=lambda h: h.regression_count, reverse=True,
        )

    def get_rollback_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent rollback history."""
        return self._rollback_log[-limit:]

    def is_known_failure(self, failure_type: str, description: str) -> Optional[FailurePattern]:
        """Check if a failure is already known."""
        signature = f"{failure_type}:{description}"
        return self._patterns.get(signature)

    def resolve_pattern(self, pattern_id: str, resolution: str) -> bool:
        """Mark a failure pattern as resolved."""
        with self._lock:
            for pattern in self._patterns.values():
                if pattern.pattern_id == pattern_id:
                    pattern.is_resolved = True
                    pattern.resolution = resolution
                    return True
            return False

    def get_failure_context(self) -> str:
        """Get compressed failure context for LLM."""
        lines = ["# Failure Memory", ""]

        repeated = self.get_repeated_failures()
        if repeated:
            lines.append("## Repeated Failures")
            for p in repeated[:5]:
                lines.append(f"- {p.description} (x{p.occurrences})")
                if p.resolution:
                    lines.append(f"  Resolution: {p.resolution}")
            lines.append("")

        hotspots = self.get_hotspots()
        if hotspots:
            lines.append("## Regression Hotspots")
            for h in hotspots[:5]:
                lines.append(f"- {h.area}: {h.regression_count} regressions")
            lines.append("")

        fragile = self.get_fragile_tests()
        if fragile:
            lines.append("## Fragile Tests")
            for t in fragile[:5]:
                lines.append(f"- {t.test_path}: {t.failure_count} failures")
            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_patterns": len(self._patterns),
            "repeated_failures": len(self.get_repeated_failures()),
            "fragile_tests": len(self._fragile_tests),
            "quarantined_tests": sum(1 for t in self._fragile_tests.values() if t.is_quarantined),
            "hotspots": len(self._hotspots),
            "rollbacks": len(self._rollback_log),
        }
