"""
drift_detection.py — Memory Drift Detection.

Problem: Memory starts lying.
Summaries become stale. Architecture changes. Assumptions invalid.

Drift detection must:
1. Detect stale summaries
2. Detect changed architecture
3. Detect invalid assumptions
4. Detect outdated risks
5. Detect dead memory

Example:
  summary says: "Auth uses JWT"
  repo now: migrated to session auth
  → MEMORY DRIFT DETECTED

Without this: runtime becomes hallucination machine.
"""

from __future__ import annotations

import time
import threading
import subprocess
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from enum import Enum

from loguru import logger


class DriftType(Enum):
    STALE_SUMMARY = "stale_summary"
    ARCHITECTURE_CHANGE = "architecture_change"
    INVALID_ASSUMPTION = "invalid_assumption"
    OUTDATED_RISK = "outdated_risk"
    DEAD_MEMORY = "dead_memory"
    SUBSYSTEM_REMOVED = "subsystem_removed"
    DEPENDENCY_CHANGED = "dependency_changed"
    FILE_MOVED = "file_moved"


@dataclass
class DriftReport:
    """A single drift detection report."""
    drift_id: str = ""
    drift_type: str = ""
    memory_key: str = ""
    expected: str = ""
    actual: str = ""
    severity: str = "warning"  # info, warning, critical
    confidence: float = 0.5
    detected_at: str = ""
    auto_fixable: bool = False
    suggestion: str = ""


class DriftDetector:
    """
    Detects when memory diverges from reality.

    Compares stored summaries against actual repo state.
    Flags stale, invalid, or outdated memory entries.
    """

    # How old (seconds) before a summary is considered potentially stale
    STALE_THRESHOLD = 7 * 24 * 3600  # 7 days

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()
        self._drift_reports: List[DriftReport] = []
        self._last_check: float = 0
        self._lock = threading.Lock()

    def check_all(self, memory_data: Dict[str, Any]) -> List[DriftReport]:
        """Run all drift checks against memory data."""
        reports = []

        reports.extend(self.check_stale_summaries(memory_data))
        reports.extend(self.check_architecture_drift(memory_data))
        reports.extend(self.check_dead_memory(memory_data))
        reports.extend(self.check_outdated_risks(memory_data))
        reports.extend(self.check_invalid_assumptions(memory_data))

        with self._lock:
            self._drift_reports.extend(reports)
            self._last_check = time.time()

        if reports:
            logger.info(f"Drift detection: {len(reports)} issues found")
            for r in reports:
                logger.debug(f"  [{r.severity}] {r.drift_type}: {r.memory_key}")

        return reports

    def check_stale_summaries(self, memory_data: Dict[str, Any]) -> List[DriftReport]:
        """Check for summaries that haven't been updated recently."""
        reports = []
        now = time.time()

        subsystems = memory_data.get("subsystems", {})
        for name, sub in subsystems.items():
            last_updated = sub.get("last_updated", "")
            if last_updated:
                try:
                    updated_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    age = now - updated_time.timestamp()
                    if age > self.STALE_THRESHOLD:
                        reports.append(DriftReport(
                            drift_id=f"stale-{name}",
                            drift_type=DriftType.STALE_SUMMARY.value,
                            memory_key=name,
                            expected=f"Updated within {self.STALE_THRESHOLD // 86400} days",
                            actual=f"Last updated {int(age // 86400)} days ago",
                            severity="warning",
                            confidence=0.8,
                            detected_at=datetime.utcnow().isoformat() + "Z",
                            suggestion=f"Re-scan subsystem '{name}' to update summary",
                        ))
                except (ValueError, TypeError):
                    pass

        return reports

    def check_architecture_drift(self, memory_data: Dict[str, Any]) -> List[DriftReport]:
        """Check if architecture has changed from what's stored."""
        reports = []

        subsystems = memory_data.get("subsystems", {})
        for name, sub in subsystems.items():
            key_files = sub.get("key_files", [])
            for file_path in key_files:
                full_path = self._project_root / file_path
                if not full_path.exists():
                    reports.append(DriftReport(
                        drift_id=f"arch-{name}-{file_path}",
                        drift_type=DriftType.ARCHITECTURE_CHANGE.value,
                        memory_key=f"{name}/{file_path}",
                        expected=f"File exists: {file_path}",
                        actual="File not found",
                        severity="critical",
                        confidence=0.95,
                        detected_at=datetime.utcnow().isoformat() + "Z",
                        auto_fixable=True,
                        suggestion=f"Remove {file_path} from {name} subsystem summary",
                    ))

        # Check for new files in known directories
        module_responsibilities = memory_data.get("module_responsibilities", {})
        for module, _resp in module_responsibilities.items():
            module_path = self._project_root / module
            if module_path.is_dir():
                current_files = set(str(f.relative_to(self._project_root))
                                    for f in module_path.rglob("*") if f.is_file())
                stored_files = set(sub.get("key_files", [])
                                   for sub in subsystems.values()
                                   for f in sub.get("key_files", [])
                                   if module in f)
                new_files = current_files - stored_files
                py_new = [f for f in new_files if f.suffix == ".py"]
                if len(py_new) > 5:
                    reports.append(DriftReport(
                        drift_id=f"arch-new-{module}",
                        drift_type=DriftType.ARCHITECTURE_CHANGE.value,
                        memory_key=module,
                        expected=f"Known files in {module}",
                        actual=f"{len(py_new)} new Python files detected",
                        severity="info",
                        confidence=0.6,
                        detected_at=datetime.utcnow().isoformat() + "Z",
                        suggestion=f"Review new files in {module} and update architecture summary",
                    ))

        return reports

    def check_dead_memory(self, memory_data: Dict[str, Any]) -> List[DriftReport]:
        """Check for memory entries that reference deleted/moved things."""
        reports = []

        fragile_areas = memory_data.get("fragile_areas", [])
        for area in fragile_areas:
            area_path = area.get("area", "")
            if area_path:
                full_path = self._project_root / area_path
                if not full_path.exists():
                    reports.append(DriftReport(
                        drift_id=f"dead-{area_path}",
                        drift_type=DriftType.DEAD_MEMORY.value,
                        memory_key=area_path,
                        expected=f"File/module exists: {area_path}",
                        actual="Not found in repo",
                        severity="warning",
                        confidence=0.9,
                        detected_at=datetime.utcnow().isoformat() + "Z",
                        auto_fixable=True,
                        suggestion=f"Remove {area_path} from fragile areas",
                    ))

        frozen_zones = memory_data.get("frozen_zones", [])
        for zone in frozen_zones:
            area_path = zone.get("area", "")
            if area_path:
                full_path = self._project_root / area_path
                if not full_path.exists():
                    reports.append(DriftReport(
                        drift_id=f"dead-frozen-{area_path}",
                        drift_type=DriftType.DEAD_MEMORY.value,
                        memory_key=area_path,
                        expected=f"Frozen zone exists: {area_path}",
                        actual="Not found in repo",
                        severity="info",
                        confidence=0.9,
                        detected_at=datetime.utcnow().isoformat() + "Z",
                        auto_fixable=True,
                        suggestion=f"Remove {area_path} from frozen zones",
                    ))

        return reports

    def check_outdated_risks(self, memory_data: Dict[str, Any]) -> List[DriftReport]:
        """Check if known risks are still relevant."""
        reports = []

        recurring_failures = memory_data.get("recurring_failures", [])
        for failure in recurring_failures:
            files = failure.get("files_involved", [])
            for file_path in files:
                full_path = self._project_root / file_path
                if not full_path.exists():
                    reports.append(DriftReport(
                        drift_id=f"risk-{file_path}",
                        drift_type=DriftType.OUTDATED_RISK.value,
                        memory_key=file_path,
                        expected=f"Risk file exists: {file_path}",
                        actual="File not found",
                        severity="info",
                        confidence=0.7,
                        detected_at=datetime.utcnow().isoformat() + "Z",
                        suggestion=f"Review if risk '{failure.get('type', '')}' is still relevant",
                    ))

        return reports

    def check_invalid_assumptions(self, memory_data: Dict[str, Any]) -> List[DriftReport]:
        """Check if stored assumptions about the codebase are still valid."""
        reports = []

        # Check technology assumptions by looking at imports/dependencies
        subsystems = memory_data.get("subsystems", {})
        for name, sub in subsystems.items():
            purpose = sub.get("role", "").lower()

            # Check JWT assumption
            if "jwt" in purpose:
                has_jwt = self._check_import_usage("jwt")
                if not has_jwt:
                    reports.append(DriftReport(
                        drift_id=f"assume-jwt-{name}",
                        drift_type=DriftType.INVALID_ASSUMPTION.value,
                        memory_key=name,
                        expected="JWT authentication",
                        actual="No JWT imports found in codebase",
                        severity="critical",
                        confidence=0.85,
                        detected_at=datetime.utcnow().isoformat() + "Z",
                        suggestion=f"Update {name} subsystem: JWT no longer used",
                    ))

            # Check database assumptions
            if "database" in purpose or "db" in purpose:
                has_db = (self._check_import_usage("sqlalchemy") or
                          self._check_import_usage("psycopg") or
                          self._check_import_usage("sqlite"))
                if not has_db:
                    reports.append(DriftReport(
                        drift_id=f"assume-db-{name}",
                        drift_type=DriftType.INVALID_ASSUMPTION.value,
                        memory_key=name,
                        expected="Database usage",
                        actual="No database imports found",
                        severity="warning",
                        confidence=0.6,
                        detected_at=datetime.utcnow().isoformat() + "Z",
                        suggestion=f"Verify {name} still uses database",
                    ))

        return reports

    def _check_import_usage(self, module_name: str) -> bool:
        """Check if a module is imported anywhere in the codebase."""
        try:
            result = subprocess.run(
                ["grep", "-r", f"import {module_name}", str(self._project_root),
                 "--include=*.py", "--include=*.js", "--include=*.ts", "-l"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return True  # Assume valid if we can't check

    def get_drift_reports(self, severity: str = "",
                          limit: int = 50) -> List[DriftReport]:
        """Get drift reports, optionally filtered by severity."""
        with self._lock:
            reports = list(self._drift_reports)

        if severity:
            reports = [r for r in reports if r.severity == severity]

        return reports[-limit:]

    def clear_resolved(self, drift_ids: List[str]) -> int:
        """Clear resolved drift reports."""
        with self._lock:
            original_len = len(self._drift_reports)
            self._drift_reports = [
                r for r in self._drift_reports if r.drift_id not in drift_ids
            ]
            return original_len - len(self._drift_reports)

    def get_stats(self) -> Dict[str, Any]:
        """Get drift detection statistics."""
        with self._lock:
            reports = list(self._drift_reports)

        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for r in reports:
            by_type[r.drift_type] = by_type.get(r.drift_type, 0) + 1
            by_severity[r.severity] = by_severity.get(r.severity, 0) + 1

        return {
            "total_reports": len(reports),
            "by_type": by_type,
            "by_severity": by_severity,
            "last_check": self._last_check,
            "auto_fixable": sum(1 for r in reports if r.auto_fixable),
        }


# DriftType enum is defined at the top of the file
