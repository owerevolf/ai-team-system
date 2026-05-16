"""
P5 — Calm Mode (Phase 10)

Minimal operational mode. Strips runtime down to essentials:
only critical errors, progress, and outcomes. No telemetry,
no traces, no explanations unless asked.

Key principle: the system should be calm by default, verbose on demand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class CalmLevel(Enum):
    FULL = "full"          # All features, all output
    REDUCED = "reduced"    # Standard output, no debug traces
    CALM = "calm"          # Only essentials: progress + errors
    SILENT = "silent"      # Only critical errors


@dataclass
class CalmPolicy:
    """What to show/hide at a given calm level."""
    show_progress: bool = True
    show_errors: bool = True
    show_warnings: bool = True
    show_traces: bool = True
    show_telemetry: bool = True
    show_explanations: bool = True
    show_approvals: bool = True
    show_debug: bool = True
    show_timestamps: bool = True
    show_source_locations: bool = True
    max_detail_items: int = 50
    compress_output: bool = False
    batch_notifications: bool = False

    @classmethod
    def for_level(cls, level: CalmLevel) -> "CalmPolicy":
        if level == CalmLevel.FULL:
            return cls()
        elif level == CalmLevel.REDUCED:
            return cls(
                show_traces=False,
                show_debug=False,
                show_source_locations=False,
                max_detail_items=20,
            )
        elif level == CalmLevel.CALM:
            return cls(
                show_progress=True,
                show_errors=True,
                show_warnings=False,
                show_traces=False,
                show_telemetry=False,
                show_explanations=False,
                show_approvals=True,
                show_debug=False,
                show_timestamps=False,
                show_source_locations=False,
                max_detail_items=5,
                compress_output=True,
                batch_notifications=True,
            )
        else:  # SILENT
            return cls(
                show_progress=False,
                show_errors=True,
                show_warnings=False,
                show_traces=False,
                show_telemetry=False,
                show_explanations=False,
                show_approvals=False,
                show_debug=False,
                show_timestamps=False,
                show_source_locations=False,
                max_detail_items=1,
                compress_output=True,
                batch_notifications=True,
            )


class CalmMode:
    """
    Manages calm mode — minimal operational output.

    Usage:
        calm = CalmMode(CalmLevel.CALM)
        if calm.should_show("traces"):
            display_trace()
        filtered = calm.filter_output(events)
    """

    def __init__(self, level: CalmLevel = CalmLevel.CALM) -> None:
        self._level = level
        self._policy = CalmPolicy.for_level(level)

    @property
    def level(self) -> CalmLevel:
        return self._level

    @level.setter
    def level(self, value: CalmLevel) -> None:
        self._level = value
        self._policy = CalmPolicy.for_level(value)

    def set_level(self, level: CalmLevel) -> None:
        """Change the calm level."""
        self.level = level

    def should_show(self, element: str) -> bool:
        """Check if an output element should be shown at current level."""
        mapping = {
            "progress": self._policy.show_progress,
            "errors": self._policy.show_errors,
            "warnings": self._policy.show_warnings,
            "traces": self._policy.show_traces,
            "telemetry": self._policy.show_telemetry,
            "explanations": self._policy.show_explanations,
            "approvals": self._policy.show_approvals,
            "debug": self._policy.show_debug,
            "timestamps": self._policy.show_timestamps,
            "source_locations": self._policy.show_source_locations,
        }
        return mapping.get(element, True)

    def filter_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter a list of output events based on current calm level."""
        if self._level == CalmLevel.FULL:
            return events

        result = []
        for event in events:
            event_type = event.get("type", "")
            if event_type in ("error", "critical") and self._policy.show_errors:
                result.append(self._strip_event(event))
            elif event_type == "progress" and self._policy.show_progress:
                result.append(self._strip_event(event))
            elif event_type == "warning" and self._policy.show_warnings:
                result.append(self._strip_event(event))
            elif event_type == "approval" and self._policy.show_approvals:
                result.append(self._strip_event(event))
            elif event_type == "success" and self._policy.show_progress:
                result.append(self._strip_event(event))
            # Skip: trace, telemetry, debug, explanation

        # Apply max items limit
        if len(result) > self._policy.max_detail_items:
            result = result[:self._policy.max_detail_items]

        return result

    def filter_explanations(self, explanations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter explanations — in calm mode, only show high-confidence ones."""
        if self._policy.show_explanations:
            return explanations
        # In calm mode, only show explanations for errors or critical actions
        return [
            e for e in explanations
            if e.get("action_type") in ("error", "recovery", "critical")
            or e.get("confidence", 1.0) < 0.5
        ]

    def get_status(self) -> dict[str, Any]:
        """Get current calm mode status."""
        return {
            "level": self._level.value,
            "policy": {
                "show_progress": self._policy.show_progress,
                "show_errors": self._policy.show_errors,
                "show_warnings": self._policy.show_warnings,
                "show_traces": self._policy.show_traces,
                "show_telemetry": self._policy.show_telemetry,
                "show_explanations": self._policy.show_explanations,
                "show_approvals": self._policy.show_approvals,
                "show_debug": self._policy.show_debug,
                "compress_output": self._policy.compress_output,
                "batch_notifications": self._policy.batch_notifications,
                "max_detail_items": self._policy.max_detail_items,
            },
        }

    def _strip_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Remove non-essential fields from an event based on calm level."""
        essential = {
            "type": event.get("type", ""),
            "message": event.get("message", event.get("summary", "")),
        }
        if self._policy.show_timestamps and "timestamp" in event:
            essential["timestamp"] = event["timestamp"]
        if event.get("type") in ("error", "critical"):
            essential["details"] = event.get("details", event.get("error", ""))
        return essential
