"""
Phase 12: Compression Engine

Central orchestrator that runs all compression analysis subsystems
and produces a unified compression report.

This is the entry point for the entire Phase 12 compression initiative.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.project_manager.runtime.compression.surface_audit import SurfaceAreaAuditor
from core.project_manager.runtime.compression.dead_system_detection import DeadSystemDetector
from core.project_manager.runtime.compression.architecture_compression import ArchitectureCompressor
from core.project_manager.runtime.compression.do_less import (
    DoLessRuntime, ActionValue,
)


@dataclass
class UnifiedCompressionReport:
    """Unified report from all compression subsystems."""
    timestamp: float = field(default_factory=time.time)
    surface_total_items: int = 0
    surface_compression_candidates: int = 0
    dead_items_detected: int = 0
    dead_safe_to_remove: int = 0
    architecture_findings: int = 0
    architecture_merge_candidates: int = 0
    architecture_lines_saved: int = 0
    overall_restraint_ratio: float = 0.0
    top_recommendations: list[str] = field(default_factory=list)
    modules_analyzed: int = 0
    total_lines_analyzed: int = 0


class CompressionEngine:
    """
    Central compression engine that orchestrates all Phase 12 analysis.

    Usage:
        engine = CompressionEngine("/path/to/project")
        report = engine.run_full_analysis()
        for rec in report.top_recommendations:
            print(rec)
    """

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.surface_auditor = SurfaceAreaAuditor(self.project_root)
        self.dead_detector = DeadSystemDetector(self.project_root)
        self.architecture_compressor = ArchitectureCompressor(
            self.project_root / "core/project_manager/runtime"
        )
        self.do_less = DoLessRuntime(
            min_action_value=ActionValue.HIGH,
            allow_interruptions=False,
            allow_advisory=False,
        )

    def run_full_analysis(self) -> UnifiedCompressionReport:
        """Run complete compression analysis across all subsystems."""
        report = UnifiedCompressionReport()

        # P1: Surface Area Audit
        surface_report = self.surface_auditor.audit()
        report.surface_total_items = surface_report.total_items
        report.surface_compression_candidates = len(surface_report.compression_candidates)

        # P4: Dead System Detection
        dead_report = self.dead_detector.scan()
        report.dead_items_detected = dead_report.total_items
        report.dead_safe_to_remove = len(dead_report.safe_to_remove)

        # P9: Architecture Compression
        arch_plan = self.architecture_compressor.analyze()
        report.architecture_findings = len(arch_plan.findings)
        report.architecture_merge_candidates = len(arch_plan.merge_candidates)
        report.architecture_lines_saved = arch_plan.total_lines_saved

        # P10: Do Less — check restraint
        do_less_report = self.do_less.get_report()
        report.overall_restraint_ratio = do_less_report.restraint_ratio

        # Generate top recommendations
        report.top_recommendations = self._generate_recommendations(
            surface_report, dead_report, arch_plan
        )

        return report

    def _generate_recommendations(
        self,
        surface_report,
        dead_report,
        arch_plan,
    ) -> list[str]:
        """Generate prioritized recommendations."""
        recs: list[str] = []

        # Surface area recommendations
        if surface_report.compression_candidates:
            recs.append(
                f"SURFACE: {len(surface_report.compression_candidates)} items "
                f"are candidates for removal or compression"
            )

        # Dead system recommendations
        if dead_report.safe_to_remove:
            recs.append(
                f"DEAD: {len(dead_report.safe_to_remove)} items are safe to remove"
            )
        if dead_report.needs_review:
            recs.append(
                f"DEAD: {len(dead_report.needs_review)} items need review for potential removal"
            )

        # Architecture recommendations
        if arch_plan.merge_candidates:
            recs.append(
                f"ARCH: {len(arch_plan.merge_candidates)} merge candidates identified"
            )
        if arch_plan.total_lines_saved > 0:
            recs.append(
                f"ARCH: Estimated {arch_plan.total_lines_saved} lines could be saved through consolidation"
            )

        for finding in arch_plan.findings[:5]:
            recs.append(
                f"ARCH [{finding.overlap_type.value}]: {finding.description} "
                f"({finding.recommended_action.value} recommended)"
            )

        if not recs:
            recs.append("No compression opportunities detected — system is lean")

        return recs
