"""
Phase 13, P3: Ontology Drift Detection

Tracks semantic divergence of concepts across subsystems:
- Same concept name, different meanings
- Same meaning, different names
- Lifecycle mismatches
- Conflicting assumptions
- Duplicated abstractions

Principle: Detect drift before it becomes architectural debt.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class DriftType(Enum):
    SEMANTIC_DIVERGENCE = "semantic_divergence"    # Same name, different meaning
    NAMING_DRIFT = "naming_drift"                  # Same meaning, different name
    LIFECYCLE_MISMATCH = "lifecycle_mismatch"      # Incompatible lifecycle assumptions
    CONFLICTING_ASSUMPTION = "conflicting_assumption"  # Contradictory premises
    DUPLICATED_ABSTRACTION = "duplicated_abstraction"  # Same concept, separate implementations
    BOUNDARY_BLEED = "boundary_bleed"              # Concept leaks across boundaries


class DriftSeverity(Enum):
    LOW = "low"            # Cosmetic — naming inconsistency
    MEDIUM = "medium"      # Structural — needs alignment
    HIGH = "high"          # Semantic — causes confusion
    CRITICAL = "critical"  # Behavioral — causes bugs


@dataclass
class DriftFinding:
    """A detected ontology drift."""
    name: str
    drift_type: DriftType
    severity: DriftSeverity
    modules: list[str]
    description: str
    recommendation: str
    canonical_name: str = ""  # What it should be called


@dataclass
class DriftReport:
    """Full ontology drift report."""
    findings: list[DriftFinding] = field(default_factory=list)
    total_modules_scanned: int = 0

    @property
    def critical_findings(self) -> list[DriftFinding]:
        return [f for f in self.findings if f.severity == DriftSeverity.CRITICAL]

    @property
    def high_findings(self) -> list[DriftFinding]:
        return [f for f in self.findings if f.severity == DriftSeverity.HIGH]

    @property
    def by_type(self) -> dict[str, list[DriftFinding]]:
        result: dict[str, list[DriftFinding]] = {}
        for f in self.findings:
            result.setdefault(f.drift_type.value, []).append(f)
        return result


class OntologyDriftDetector:
    """
    Detects ontology drift across runtime subsystems.
    Scans module ASTs for concept definitions and compares semantics.
    """

    # Known drift patterns detected during Phase 12 audit
    KNOWN_DRIFT_PATTERNS: list[dict] = [
        {
            "name": "Priority model fragmentation",
            "drift_type": DriftType.SEMANTIC_DIVERGENCE,
            "severity": DriftSeverity.HIGH,
            "modules": [
                "ergonomics/attention_management",
                "ergonomics/calm_mode",
                "compression/interaction_minimalism",
            ],
            "description": (
                "Three different priority models exist: "
                "AttentionPriority(CRITICAL/HIGH/NORMAL/LOW/SILENT), "
                "InteractionPriority(CRITICAL/IMPORTANT/NORMAL/LOW/SILENT), "
                "CalmLevel(FULL/REDUCED/CALM/SILENT). "
                "SILENT means different things in each."
            ),
            "recommendation": "Unify under CanonicalPriority with explicit mapping",
            "canonical_name": "CanonicalPriority",
        },
        {
            "name": "Event type fragmentation",
            "drift_type": DriftType.DUPLICATED_ABSTRACTION,
            "severity": DriftSeverity.HIGH,
            "modules": [
                "durability/observability",
                "ergonomics/noise_reduction",
                "trust/transparency_contracts",
                "compression/interaction_minimalism",
            ],
            "description": (
                "Four separate event classification systems: "
                "EntryType(6 values), NoiseType(5 values), "
                "EventCategory(17 values), InteractionType(6 values). "
                "No unified event taxonomy."
            ),
            "recommendation": "Create CanonicalEventType with subtype hierarchy",
            "canonical_name": "CanonicalEventType",
        },
        {
            "name": "Explanation depth fragmentation",
            "drift_type": DriftType.SEMANTIC_DIVERGENCE,
            "severity": DriftSeverity.MEDIUM,
            "modules": [
                "durability/explainability_layer",
                "trust/explainability_compression",
                "compression/progressive_disclosure",
            ],
            "description": (
                "Three explanation depth models: "
                "ExplanationField(WHY/SOURCE/CONSTRAINTS/IMPACT/CONFIDENCE/RECOVERY), "
                "ExplanationLevel(SUMMARY/REASONING/FULL_TRACE), "
                "DisclosureLevel(MINIMAL/SUMMARY/DETAILED/FULL/DEBUG). "
                "FULL means different things in each."
            ),
            "recommendation": "Unify under CanonicalExplanationLevel",
            "canonical_name": "CanonicalExplanationLevel",
        },
        {
            "name": "State model split",
            "drift_type": DriftType.BOUNDARY_BLEED,
            "severity": DriftSeverity.MEDIUM,
            "modules": [
                "durability/state_lifecycle",
                "durability/context_gc",
            ],
            "description": (
                "State lifecycle (StateTier) and context types (ContextType) "
                "are separate models with overlapping concerns. "
                "ContextType includes WORKFLOW_STATE and TASK_STATE which "
                "should reference StateTier lifecycle."
            ),
            "recommendation": "Cross-reference ContextType with StateTier for lifecycle management",
            "canonical_name": "CanonicalStateTier",
        },
        {
            "name": "Approval model split",
            "drift_type": DriftType.NAMING_DRIFT,
            "severity": DriftSeverity.LOW,
            "modules": [
                "ergonomics/approval_intelligence",
                "trust/governance_pressure",
                "runtime/approval",
            ],
            "description": (
                "Approval risk and status are defined in approval_intelligence, "
                "but governance_pressure and runtime/approval have their own "
                "approval-related logic without shared types."
            ),
            "recommendation": "Centralize approval types in CanonicalApprovalRisk/Status",
            "canonical_name": "CanonicalApprovalRisk",
        },
        {
            "name": "Visibility model split",
            "drift_type": DriftType.SEMANTIC_DIVERGENCE,
            "severity": DriftSeverity.MEDIUM,
            "modules": [
                "trust/transparency_contracts",
                "trust/visibility_guarantees",
                "compression/interaction_minimalism",
            ],
            "description": (
                "VisibilityAction(SHOW/SUMMARIZE/DELAY/SUPPRESS) vs "
                "GuaranteeLevel(ALWAYS/CRITICAL/STANDARD/BEST_EFFORT) vs "
                "InteractionPriority-based suppression. "
                "Three different visibility control mechanisms."
            ),
            "recommendation": "Unify under CanonicalVisibility with GuaranteeLevel as constraint",
            "canonical_name": "CanonicalVisibility",
        },
    ]

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)

    def detect_drift(self) -> DriftReport:
        """Run full ontology drift detection."""
        report = DriftReport()

        # Load known drift patterns
        for pattern in self.KNOWN_DRIFT_PATTERNS:
            report.findings.append(DriftFinding(
                name=pattern["name"],
                drift_type=pattern["drift_type"],
                severity=pattern["severity"],
                modules=pattern["modules"],
                description=pattern["description"],
                recommendation=pattern["recommendation"],
                canonical_name=pattern["canonical_name"],
            ))

        # Scan for additional drift
        report.findings.extend(self._scan_for_new_drift())
        report.total_modules_scanned = self._count_modules()

        return report

    def _scan_for_new_drift(self) -> list[DriftFinding]:
        """Scan modules for previously unknown drift patterns."""
        findings: list[DriftFinding] = []

        # Find classes with similar names across modules
        class_map: dict[str, list[str]] = {}
        for root, dirs, filenames in os.walk(self.base_path):
            dirs[:] = [
                d for d in dirs
                if d not in ("__pycache__", ".pytest_cache", "venv", "venv_new", ".git")
                and not d.startswith(".")
            ]
            for fn in filenames:
                if not fn.endswith(".py") or fn == "__init__.py":
                    continue
                filepath = Path(root) / fn
                rel_path = str(filepath.relative_to(self.base_path))
                try:
                    source = filepath.read_text(encoding="utf-8")
                    tree = ast.parse(source, filename=rel_path)
                except:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                        class_map.setdefault(node.name, []).append(rel_path)

        # Find classes with same name in different modules
        for class_name, modules in class_map.items():
            if len(modules) > 1 and not class_name.startswith("Test"):
                findings.append(DriftFinding(
                    name=f"Duplicate class: {class_name}",
                    drift_type=DriftType.DUPLICATED_ABSTRACTION,
                    severity=DriftSeverity.MEDIUM,
                    modules=modules,
                    description=f"Class '{class_name}' defined in {len(modules)} modules",
                    recommendation=f"Consolidate '{class_name}' into a single canonical definition",
                    canonical_name=class_name,
                ))

        return findings

    def _count_modules(self) -> int:
        """Count total Python modules scanned."""
        count = 0
        for root, dirs, filenames in os.walk(self.base_path):
            dirs[:] = [
                d for d in dirs
                if d not in ("__pycache__", ".pytest_cache", "venv", "venv_new", ".git")
                and not d.startswith(".")
            ]
            for fn in filenames:
                if fn.endswith(".py") and fn != "__init__.py":
                    count += 1
        return count
