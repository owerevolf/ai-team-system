"""
noise_collapse.py — Runtime Noise Collapse.

Purpose: Make runtime quieter.
Rule: Silence > Noise (if noise doesn't help engineering).

Reduces:
- event spam
- repetitive explanations
- unnecessary telemetry
- duplicate agent chatter
- orchestration verbosity
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from loguru import logger


@dataclass
class NoiseRule:
    """A rule for reducing noise."""
    rule_id: str = ""
    name: str = ""
    description: str = ""
    enabled: bool = True
    suppression_count: int = 0


class NoiseCollapse:
    """
    Reduces runtime noise.
    Silence > Noise (if noise doesn't help engineering).
    """

    DEFAULT_RULES = [
        NoiseRule("dedup_events", "Deduplicate Events",
                  "Suppress duplicate events within 5 seconds"),
        NoiseRule("quiet_telemetry", "Quiet Telemetry",
                  "Reduce telemetry logging to warnings only"),
        NoiseRule("concise_explanations", "Concise Explanations",
                  "Limit explanation length to 200 chars"),
        NoiseRule("suppress_chatter", "Suppress Agent Chatter",
                  "Remove motivational fluff from agent outputs"),
        NoiseRule("quiet_orchestration", "Quiet Orchestration",
                  "Reduce orchestration event verbosity"),
        NoiseRule("batch_notifications", "Batch Notifications",
                  "Batch similar notifications together"),
    ]

    def __init__(self):
        self._rules: Dict[str, NoiseRule] = {}
        for rule in self.DEFAULT_RULES:
            self._rules[rule.rule_id] = rule
        self._suppressed: Dict[str, int] = {}
        self._recent_events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def should_suppress(self, event_type: str, content: str) -> bool:
        """Check if an event should be suppressed."""
        # Check chatter suppression first (simpler)
        if self._rules.get("suppress_chatter", NoiseRule()).enabled:
            content_lower = content.lower()
            for pattern in ["great question", "absolutely", "i'd be happy to help",
                           "certainly", "wonderful", "fantastic"]:
                if pattern in content_lower:
                    self._increment_suppression("suppress_chatter")
                    return True

        # Check dedup
        if self._rules.get("dedup_events", NoiseRule()).enabled:
            for recent in self._recent_events[-10:]:
                if recent.get("type") == event_type and recent.get("content") == content:
                    self._increment_suppression("dedup_events")
                    return True

            # Add to recent
            self._recent_events.append({"type": event_type, "content": content})
            if len(self._recent_events) > 100:
                self._recent_events = self._recent_events[-50:]

        return False

    def collapse_output(self, output: str, max_length: int = 500) -> str:
        """Collapse verbose output to essential information."""
        if len(output) <= max_length:
            return output

        # Truncate at sentence boundary
        truncated = output[:max_length]
        last_period = truncated.rfind(".")
        if last_period > max_length * 0.7:
            truncated = truncated[:last_period + 1]

        return truncated + "\n... [truncated for brevity]"

    def _increment_suppression(self, rule_id: str) -> None:
        """Increment suppression count for a rule."""
        self._suppressed[rule_id] = self._suppressed.get(rule_id, 0) + 1
        if rule_id in self._rules:
            self._rules[rule_id].suppression_count += 1

    def get_noise_report(self) -> Dict[str, Any]:
        """Get noise reduction report."""
        with self._lock:
            suppressed = dict(self._suppressed)

        total_suppressions = sum(suppressed.values())

        return {
            "total_suppressions": total_suppressions,
            "by_rule": suppressed,
            "rules": {
                rid: {
                    "name": r.name,
                    "enabled": r.enabled,
                    "suppressions": r.suppression_count,
                }
                for rid, r in self._rules.items()
            },
        }

    def enable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False
