"""
P1 — Workflow Compression (Phase 10)

Collapses the full runtime graph into digestible views.
Instead of showing every trace, checkpoint, and workflow step,
produces compressed summaries at the right granularity.

Key principle: show outcomes, hide machinery.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class CompressionLevel(Enum):
    MINIMAL = "minimal"      # Just status + last action
    STANDARD = "standard"    # Key steps + outcomes
    DETAILED = "detailed"    # Full trace with grouping


@dataclass
class CompressedStep:
    """A single compressed workflow step."""
    step_id: str
    label: str
    status: str  # "done" | "running" | "pending" | "skipped" | "failed"
    duration_ms: float = 0.0
    summary: str = ""
    detail_count: int = 0  # How many raw steps were compressed into this

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "label": self.label,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "summary": self.summary,
            "detail_count": self.detail_count,
        }


@dataclass
class CompressedView:
    """A compressed view of an entire workflow."""
    workflow_id: str
    workflow_type: str
    status: str
    started_at: float
    ended_at: float = 0.0
    steps: list[CompressedStep] = field(default_factory=list)
    total_raw_steps: int = 0
    compression_ratio: float = 0.0
    outcome: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": (self.ended_at - self.started_at) * 1000 if self.ended_at else 0,
            "steps": [s.to_dict() for s in self.steps],
            "total_raw_steps": self.total_raw_steps,
            "compression_ratio": self.compression_ratio,
            "outcome": self.outcome,
            "errors": self.errors,
        }


class WorkflowCompressor:
    """
    Compresses raw workflow traces into human-digestible views.

    Usage:
        compressor = WorkflowCompressor(CompressionLevel.STANDARD)
        view = compressor.compress(raw_steps)
    """

    # Step types that can be grouped together
    GROUPABLE_TYPES = {
        "validation", "indexing", "scanning", "parsing",
        "caching", "logging", "telemetry",
    }

    # Step types that always show individually
    PROMINENT_TYPES = {
        "approval", "recovery", "error", "decision",
        "file_create", "file_modify", "git_commit",
    }

    def __init__(self, level: CompressionLevel = CompressionLevel.STANDARD) -> None:
        self.level = level

    def compress(self, raw_steps: list[dict[str, Any]], workflow_id: str = "", workflow_type: str = "generic") -> CompressedView:
        """Compress a list of raw steps into a digestible view."""
        if not raw_steps:
            return CompressedView(
                workflow_id=workflow_id or "empty",
                workflow_type=workflow_type,
                status="empty",
                started_at=time.time(),
                ended_at=time.time(),
            )

        total_raw = len(raw_steps)

        if self.level == CompressionLevel.DETAILED:
            compressed = self._compress_detailed(raw_steps)
        elif self.level == CompressionLevel.STANDARD:
            compressed = self._compress_standard(raw_steps)
        else:  # MINIMAL
            compressed = self._compress_minimal(raw_steps)

        # Determine overall status
        statuses = [s.status for s in compressed]
        if "failed" in statuses:
            overall_status = "failed"
        elif "running" in statuses:
            overall_status = "running"
        elif all(s == "done" for s in statuses):
            overall_status = "done"
        elif all(s == "skipped" for s in statuses):
            overall_status = "skipped"
        else:
            overall_status = "partial"

        # Collect errors
        errors = []
        for step in raw_steps:
            if step.get("status") == "failed" and step.get("error"):
                errors.append(step["error"])

        # Build outcome summary
        outcome = self._build_outcome(overall_status, compressed, errors)

        started = raw_steps[0].get("timestamp", time.time())
        ended = raw_steps[-1].get("timestamp", time.time())

        ratio = len(compressed) / total_raw if total_raw > 0 else 1.0

        return CompressedView(
            workflow_id=workflow_id or "wf-unknown",
            workflow_type=workflow_type,
            status=overall_status,
            started_at=started if isinstance(started, (int, float)) else time.time(),
            ended_at=ended if isinstance(ended, (int, float)) else time.time(),
            steps=compressed,
            total_raw_steps=total_raw,
            compression_ratio=round(ratio, 2),
            outcome=outcome,
            errors=errors,
        )

    def _compress_minimal(self, raw_steps: list[dict[str, Any]]) -> list[CompressedStep]:
        """Minimal: only show first running/pending step + last done step."""
        result = []
        # Find the current active step
        for step in raw_steps:
            if step.get("status") == "running":
                result.append(CompressedStep(
                    step_id=step.get("id", ""),
                    label=step.get("label", step.get("type", "unknown")),
                    status="running",
                    summary=step.get("summary", ""),
                ))
                break
        # If nothing running, show last completed
        if not result:
            for step in reversed(raw_steps):
                if step.get("status") == "done":
                    result.append(CompressedStep(
                        step_id=step.get("id", ""),
                        label=step.get("label", step.get("type", "unknown")),
                        status="done",
                        summary=step.get("summary", ""),
                    ))
                    break
        return result

    def _compress_standard(self, raw_steps: list[dict[str, Any]]) -> list[CompressedStep]:
        """Standard: group similar steps, keep prominent ones separate."""
        result: list[CompressedStep] = []
        group_buffer: list[dict[str, Any]] = []
        current_group_type = ""

        def flush_group():
            if not group_buffer:
                return
            first = group_buffer[0]
            count = len(group_buffer)
            if count == 1:
                result.append(CompressedStep(
                    step_id=first.get("id", ""),
                    label=first.get("label", first.get("type", "unknown")),
                    status=first.get("status", "done"),
                    summary=first.get("summary", ""),
                ))
            else:
                # Grouped: show count and first item as example
                statuses = [s.get("status", "done") for s in group_buffer]
                group_status = "failed" if "failed" in statuses else statuses[0]
                total_ms = sum(
                    s.get("duration_ms", 0) for s in group_buffer
                )
                result.append(CompressedStep(
                    step_id=f"group-{first.get('type', 'unknown')}",
                    label=f"{first.get('label', first.get('type', 'unknown'))} (×{count})",
                    status=group_status,
                    duration_ms=total_ms,
                    summary=f"{count} items processed",
                    detail_count=count,
                ))
            group_buffer.clear()

        for step in raw_steps:
            step_type = step.get("type", "unknown")
            status = step.get("status", "done")

            # Always show prominent types individually
            if step_type in self.PROMINENT_TYPES or status == "failed":
                flush_group()
                result.append(CompressedStep(
                    step_id=step.get("id", ""),
                    label=step.get("label", step_type),
                    status=status,
                    duration_ms=step.get("duration_ms", 0),
                    summary=step.get("summary", ""),
                ))
                continue

            # Group similar types
            if step_type in self.GROUPABLE_TYPES:
                if step_type != current_group_type:
                    flush_group()
                    current_group_type = step_type
                group_buffer.append(step)
            else:
                flush_group()
                current_group_type = ""
                result.append(CompressedStep(
                    step_id=step.get("id", ""),
                    label=step.get("label", step_type),
                    status=status,
                    duration_ms=step.get("duration_ms", 0),
                    summary=step.get("summary", ""),
                ))

        flush_group()
        return result

    def _compress_detailed(self, raw_steps: list[dict[str, Any]]) -> list[CompressedStep]:
        """Detailed: show all steps but with grouping markers."""
        result = []
        for step in raw_steps:
            result.append(CompressedStep(
                step_id=step.get("id", ""),
                label=step.get("label", step.get("type", "unknown")),
                status=step.get("status", "done"),
                duration_ms=step.get("duration_ms", 0),
                summary=step.get("summary", ""),
            ))
        return result

    def _build_outcome(self, status: str, steps: list[CompressedStep], errors: list[str]) -> str:
        """Build a human-readable outcome summary."""
        if status == "done":
            return f"All {len(steps)} steps completed successfully."
        elif status == "failed":
            return f"Failed with {len(errors)} error(s). Check details."
        elif status == "running":
            running = [s for s in steps if s.status == "running"]
            if running:
                return f"Running: {running[0].label}"
            return "In progress..."
        elif status == "skipped":
            return "All steps skipped."
        elif status == "empty":
            return "No steps to display."
        else:
            done_count = sum(1 for s in steps if s.status == "done")
            return f"Partial: {done_count}/{len(steps)} steps done."
