"""
patch_review_ux.py — Patch Review Experience.

Purpose: Make human approval comfortable, not painful.
Approval should feel calm.

Shows:
- what changed
- why changed
- impact
- risks
- affected files
- test results
- rollback info
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PatchReviewBundle:
    """Complete patch review information."""
    patch_id: str = ""
    summary: str = ""
    reason: str = ""
    risk_level: str = "low"
    risk_score: float = 0.0
    affected_files: List[str] = field(default_factory=list)
    affected_systems: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    test_results: Dict[str, Any] = field(default_factory=dict)
    lint_results: Dict[str, Any] = field(default_factory=dict)
    build_results: Dict[str, Any] = field(default_factory=dict)
    rollback_available: bool = True
    rollback_preview: str = ""
    memory_impacts: List[str] = field(default_factory=list)
    frozen_zone_conflicts: List[str] = field(default_factory=list)
    governance_violations: List[str] = field(default_factory=list)

    def to_review_text(self) -> str:
        """Generate human-readable review text."""
        lines = [
            f"# Patch Review: {self.patch_id}",
            "",
            f"## Summary",
            self.summary,
            "",
            f"## Reason",
            self.reason,
            "",
            f"## Risk: {self.risk_level.upper()} ({self.risk_score:.1f}/10)",
            "",
            f"## Changes",
            f"+{self.lines_added} / -{self.lines_removed} lines",
            f"Files: {len(self.affected_files)}",
        ]

        for f in self.affected_files[:10]:
            lines.append(f"  - {f}")
        if len(self.affected_files) > 10:
            lines.append(f"  ... and {len(self.affected_files) - 10} more")

        if self.affected_systems:
            lines.extend(["", "## Affected Systems"])
            for s in self.affected_systems:
                lines.append(f"  - {s}")

        if self.test_results:
            lines.extend(["", "## Test Results"])
            passed = self.test_results.get("passed", 0)
            failed = self.test_results.get("failed", 0)
            lines.append(f"  Passed: {passed}, Failed: {failed}")

        if self.lint_results:
            lines.extend(["", "## Lint Results"])
            errors = self.lint_results.get("error_count", 0)
            warnings = self.lint_results.get("warning_count", 0)
            lines.append(f"  Errors: {errors}, Warnings: {warnings}")

        if self.frozen_zone_conflicts:
            lines.extend(["", "## ⚠️ Frozen Zone Conflicts"])
            for c in self.frozen_zone_conflicts:
                lines.append(f"  - {c}")

        if self.governance_violations:
            lines.extend(["", "## ⚠️ Governance Violations"])
            for v in self.governance_violations:
                lines.append(f"  - {v}")

        if self.rollback_available:
            lines.extend(["", "## Rollback", "Available ✓"])

        if self.memory_impacts:
            lines.extend(["", "## Memory Impacts"])
            for m in self.memory_impacts:
                lines.append(f"  - {m}")

        return "\n".join(lines)


class PatchReviewUX:
    """
    Generates patch review bundles for human approval.
    Makes approval calm and informative.
    """

    def __init__(self, memory_runtime=None, tool_runtime=None):
        self._memory = memory_runtime
        self._tools = tool_runtime

    def generate_review(self, patch_data: Dict[str, Any]) -> PatchReviewBundle:
        """Generate a complete patch review bundle."""
        bundle = PatchReviewBundle(
            patch_id=patch_data.get("patch_id", ""),
            summary=patch_data.get("summary", ""),
            reason=patch_data.get("reason", ""),
            risk_level=patch_data.get("risk_level", "low"),
            risk_score=patch_data.get("risk_score", 0.0),
            affected_files=patch_data.get("files", []),
            lines_added=patch_data.get("lines_added", 0),
            lines_removed=patch_data.get("lines_removed", 0),
        )

        # Detect affected systems
        bundle.affected_systems = self._detect_affected_systems(bundle.affected_files)

        # Check frozen zones
        if self._memory:
            bundle.frozen_zone_conflicts = self._check_frozen_zones(bundle.affected_files)
            bundle.governance_violations = self._check_governance(bundle)

        # Generate rollback preview
        bundle.rollback_preview = self._generate_rollback_preview(patch_data)

        # Memory impacts
        if self._memory:
            bundle.memory_impacts = self._detect_memory_impacts(bundle.affected_files)

        return bundle

    def _detect_affected_systems(self, files: List[str]) -> List[str]:
        """Detect which subsystems are affected by file changes."""
        systems = set()
        for f in files:
            parts = f.split("/")
            if parts:
                systems.add(parts[0])
        return list(systems)

    def _check_frozen_zones(self, files: List[str]) -> List[str]:
        """Check if any files are in frozen zones."""
        conflicts = []
        if not self._memory:
            return conflicts
        for f in files:
            frozen, reason = self._memory.semantic_memory.is_frozen(f)
            if frozen:
                conflicts.append(f"{f}: {reason}")
        return conflicts

    def _check_governance(self, bundle: PatchReviewBundle) -> List[str]:
        """Check governance violations."""
        violations = []
        if not self._memory:
            return violations

        # Check risk level
        if bundle.risk_level == "critical":
            violations.append("Critical risk level — requires explicit human approval")

        # Check frozen zone conflicts
        if bundle.frozen_zone_conflicts:
            violations.append(f"Frozen zone conflicts: {len(bundle.frozen_zone_conflicts)} files")

        return violations

    def _generate_rollback_preview(self, patch_data: Dict[str, Any]) -> str:
        """Generate a preview of the rollback."""
        files = patch_data.get("files", [])
        if not files:
            return "No files to rollback"
        return f"Rollback will restore {len(files)} files to previous state"

    def _detect_memory_impacts(self, files: List[str]) -> List[str]:
        """Detect impacts on memory/runtime."""
        impacts = []
        if not self._memory:
            return impacts

        for f in files:
            # Check if file is in any subsystem
            subsystems = self._memory.semantic_memory.get_all_subsystems()
            for name, sub in subsystems.items():
                if f in sub.key_files:
                    impacts.append(f"Key file for {name} subsystem modified")

        return impacts

    def generate_summary(self, patch_data: Dict[str, Any]) -> str:
        """Generate a one-line patch summary."""
        summary = patch_data.get("summary", "Unknown change")
        files = patch_data.get("files", [])
        risk = patch_data.get("risk_level", "low")

        return f"[{risk.upper()}] {summary} ({len(files)} files)"
