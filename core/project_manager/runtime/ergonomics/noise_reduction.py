"""
P4 — Noise Reduction (Phase 10)

Aggressively suppresses redundant explanations, duplicate telemetry,
and stale alerts. If it doesn't add new information, it's noise.

Key principle: every piece of information must earn its place.
"""

from __future__ import annotations

import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class NoiseType(Enum):
    REDUNDANT_EXPLANATION = "redundant_explanation"
    DUPLICATE_TELEMETRY = "duplicate_telemetry"
    STALE_ALERT = "stale_alert"
    REPEATED_LOG = "repeated_log"
    OVERVERBOSE_TRACE = "oververbose_trace"


@dataclass
class NoiseEvent:
    """A detected noise event."""
    noise_id: str
    noise_type: NoiseType
    source: str
    message: str
    fingerprint: str  # Hash of the normalized message
    count: int = 1
    first_seen: float = 0.0
    last_seen: float = 0.0
    suppressed: bool = False

    def __post_init__(self) -> None:
        if not self.first_seen:
            self.first_seen = time.time()
        if not self.last_seen:
            self.last_seen = self.first_seen

    def to_dict(self) -> dict[str, Any]:
        return {
            "noise_id": self.noise_id,
            "noise_type": self.noise_type.value,
            "source": self.source,
            "message": self.message,
            "fingerprint": self.fingerprint,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "suppressed": self.suppressed,
        }


@dataclass
class NoiseReport:
    """Report of noise reduction activity."""
    total_events: int = 0
    suppressed_count: int = 0
    dedup_count: int = 0
    stale_count: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    top_noise: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_events": self.total_events,
            "suppressed_count": self.suppressed_count,
            "dedup_count": self.dedup_count,
            "stale_count": self.stale_count,
            "by_type": self.by_type,
            "top_noise": self.top_noise,
        }


class NoiseReducer:
    """
    Detects and suppresses noise in runtime output.

    Usage:
        reducer = NoiseReducer()
        result = reducer.process("explanation", "File modified: auth.py")
        if result is None:
            # Suppressed as noise
            pass
    """

    def __init__(
        self,
        dedup_window_seconds: float = 60.0,
        stale_threshold_seconds: float = 300.0,
        max_repeats_before_suppress: int = 3,
        max_fingerprints: int = 500,
    ) -> None:
        self._fingerprints: dict[str, NoiseEvent] = {}
        self._dedup_window = dedup_window_seconds
        self._stale_threshold = stale_threshold_seconds
        self._max_repeats = max_repeats_before_suppress
        self._max_fingerprints = max_fingerprints
        self._total_processed = 0
        self._total_suppressed = 0

    def process(self, source: str, message: str, event_type: str = "generic") -> Optional[str]:
        """
        Process an event. Returns the message if it should be shown,
        or None if it should be suppressed as noise.
        """
        self._total_processed += 1
        fingerprint = self._fingerprint(source, message)
        now = time.time()

        existing = self._fingerprints.get(fingerprint)
        if existing:
            existing.count += 1
            existing.last_seen = now

            # Suppress if repeated too many times within window
            if existing.count >= self._max_repeats:
                if not existing.suppressed:
                    existing.suppressed = True
                self._total_suppressed += 1
                return None

            # Suppress if within dedup window
            if (now - existing.last_seen) < self._dedup_window:
                self._total_suppressed += 1
                return None

            # Allow through but note repetition
            return f"[{existing.count}×] {message}"

        # New event
        noise = NoiseEvent(
            noise_id=f"noise-{fingerprint[:8]}",
            noise_type=self._classify_noise(event_type),
            source=source,
            message=message,
            fingerprint=fingerprint,
            first_seen=now,
            last_seen=now,
        )
        self._fingerprints[fingerprint] = noise
        self._enforce_limit()
        return message

    def process_explanation(self, explanation: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Process an explanation dict. Returns None if redundant.
        Checks for duplicate explanations within the dedup window.
        """
        # Create a fingerprint from the explanation content
        content = f"{explanation.get('action_type', '')}:{explanation.get('why', '')}"
        result = self.process("explanation", content, "explanation")
        if result is None:
            return None
        return explanation

    def process_telemetry(self, telemetry: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Process a telemetry event. Returns None if duplicate."""
        metric = telemetry.get("metric", "")
        value = str(telemetry.get("value", ""))
        result = self.process(f"telemetry:{metric}", value, "telemetry")
        if result is None:
            return None
        return telemetry

    def cleanup_stale(self) -> int:
        """Remove stale fingerprints. Returns count removed."""
        now = time.time()
        stale_keys = [
            k for k, v in self._fingerprints.items()
            if (now - v.last_seen) > self._stale_threshold
        ]
        for k in stale_keys:
            del self._fingerprints[k]
        return len(stale_keys)

    def get_report(self) -> NoiseReport:
        """Get noise reduction report."""
        by_type: dict[str, int] = {}
        for event in self._fingerprints.values():
            t = event.noise_type.value
            by_type[t] = by_type.get(t, 0) + 1

        # Top noise sources by count
        sorted_events = sorted(
            self._fingerprints.values(),
            key=lambda e: e.count,
            reverse=True,
        )
        top_noise = [
            {
                "source": e.source,
                "message": e.message[:100],
                "count": e.count,
                "type": e.noise_type.value,
            }
            for e in sorted_events[:10]
        ]

        return NoiseReport(
            total_events=self._total_processed,
            suppressed_count=self._total_suppressed,
            dedup_count=sum(1 for e in self._fingerprints.values() if e.count > 1),
            stale_count=sum(
                1 for e in self._fingerprints.values()
                if (time.time() - e.last_seen) > self._stale_threshold
            ),
            by_type=by_type,
            top_noise=top_noise,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get noise reducer stats."""
        return {
            "total_processed": self._total_processed,
            "total_suppressed": self._total_suppressed,
            "suppression_rate": (
                round(self._total_suppressed / self._total_processed, 3)
                if self._total_processed > 0 else 0.0
            ),
            "active_fingerprints": len(self._fingerprints),
        }

    def _fingerprint(self, source: str, message: str) -> str:
        """Create a fingerprint for dedup detection."""
        # Normalize: lowercase, strip numbers that might vary
        normalized = f"{source}:{message.lower().strip()}"
        normalized = ''.join(c for c in normalized if not c.isdigit())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def _classify_noise(self, event_type: str) -> NoiseType:
        """Classify the noise type."""
        mapping = {
            "explanation": NoiseType.REDUNDANT_EXPLANATION,
            "telemetry": NoiseType.DUPLICATE_TELEMETRY,
            "alert": NoiseType.STALE_ALERT,
            "log": NoiseType.REPEATED_LOG,
            "trace": NoiseType.OVERVERBOSE_TRACE,
        }
        return mapping.get(event_type, NoiseType.REPEATED_LOG)

    def _enforce_limit(self) -> None:
        """Keep fingerprints under limit."""
        if len(self._fingerprints) <= self._max_fingerprints:
            return
        # Remove oldest
        sorted_items = sorted(
            self._fingerprints.items(),
            key=lambda x: x[1].last_seen,
        )
        to_remove = len(self._fingerprints) - self._max_fingerprints
        for k, _ in sorted_items[:to_remove]:
            del self._fingerprints[k]
