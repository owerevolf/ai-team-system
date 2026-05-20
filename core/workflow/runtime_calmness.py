"""
runtime_calmness.py — Runtime Calmness.

Purpose: Make the system feel calm.
The system should NOT feel like a terminal chaos simulator.

Analyzes:
- UI overload
- event spam
- notification pressure
- cognitive spikes
- interruption patterns
- visual noise
- orchestration anxiety
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class CalmnessEvent:
    """A calmness-related event."""
    event_type: str = ""  # notification, event_spam, cognitive_spike, interruption, visual_noise
    description: str = ""
    intensity: float = 0.0  # 0.0 to 1.0
    timestamp: float = 0.0


@dataclass
class CalmnessReport:
    """Calmness analysis report."""
    calmness_score: float = 10.0  # 0.0 to 10.0, higher = calmer
    interruption_density: float = 0.0  # interruptions per minute
    noise_level: float = 0.0  # 0.0 to 1.0
    cognitive_pressure: float = 0.0  # 0.0 to 1.0
    interaction_stability: float = 1.0  # 0.0 to 1.0
    top_disturbances: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class RuntimeCalmness:
    """
    Monitors and maintains runtime calmness.
    Goal: system should feel calm, not chaotic.
    """

    # Thresholds
    HIGH_INTERRUPTION_THRESHOLD = 5  # per minute
    HIGH_NOISE_THRESHOLD = 0.7
    HIGH_COGNITIVE_PRESSURE_THRESHOLD = 0.6
    LOW_CALMNESS_THRESHOLD = 5.0

    def __init__(self):
        self._events: List[CalmnessEvent] = []
        self._session_start: float = 0.0
        self._lock = threading.Lock()

    def start_session(self) -> None:
        """Start a calmness monitoring session."""
        with self._lock:
            self._events.clear()
            self._session_start = time.time()

    def record_notification(self, description: str = "", intensity: float = 0.3) -> None:
        """Record a notification event."""
        self._add_event("notification", description, intensity)

    def record_event_spam(self, description: str = "", intensity: float = 0.5) -> None:
        """Record event spam."""
        self._add_event("event_spam", description, intensity)

    def record_cognitive_spike(self, description: str = "", intensity: float = 0.7) -> None:
        """Record a cognitive spike (complex information dump)."""
        self._add_event("cognitive_spike", description, intensity)

    def record_interruption(self, description: str = "", intensity: float = 0.6) -> None:
        """Record an interruption."""
        self._add_event("interruption", description, intensity)

    def record_visual_noise(self, description: str = "", intensity: float = 0.4) -> None:
        """Record visual noise."""
        self._add_event("visual_noise", description, intensity)

    def _add_event(self, event_type: str, description: str, intensity: float) -> None:
        """Add a calmness event."""
        event = CalmnessEvent(
            event_type=event_type,
            description=description,
            intensity=intensity,
            timestamp=time.time(),
        )
        with self._lock:
            self._events.append(event)

    def get_report(self) -> CalmnessReport:
        """Generate a calmness report."""
        with self._lock:
            events = list(self._events)

        if not events:
            return CalmnessReport()

        duration = max(1.0, time.time() - self._session_start)

        # Calculate metrics
        high_intensity = [e for e in events if e.intensity > 0.5]
        interruption_count = len([e for e in events if e.event_type == "interruption"])
        interruption_density = interruption_count / (duration / 60)

        noise_level = sum(e.intensity for e in events if e.event_type in ("notification", "event_spam", "visual_noise")) / max(1, len(events))
        cognitive_pressure = sum(e.intensity for e in events if e.event_type == "cognitive_spike") / max(1, len(events))

        # Stability: how consistent is the interaction pattern?
        if len(events) > 1:
            intervals = [events[i+1].timestamp - events[i].timestamp for i in range(len(events)-1)]
            avg_interval = sum(intervals) / len(intervals)
            variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
            interaction_stability = max(0.0, 1.0 - min(1.0, variance / 10))
        else:
            interaction_stability = 1.0

        # Calmness score
        calmness_score = 10.0
        calmness_score -= len(high_intensity) * 0.5
        calmness_score -= interruption_density * 0.3
        calmness_score -= noise_level * 2.0
        calmness_score -= cognitive_pressure * 2.0
        calmness_score = max(0.0, min(10.0, calmness_score))

        # Top disturbances
        disturbance_counts: Dict[str, int] = {}
        for e in events:
            if e.intensity > 0.4:
                disturbance_counts[e.event_type] = disturbance_counts.get(e.event_type, 0) + 1

        top_disturbances = sorted(disturbance_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_disturbances = [f"{k}: {v} occurrences" for k, v in top_disturbances]

        # Recommendations
        recommendations = []
        if calmness_score < self.LOW_CALMNESS_THRESHOLD:
            recommendations.append(f"Low calmness: {calmness_score:.1f}/10 — reduce interruptions")

        if interruption_density > self.HIGH_INTERRUPTION_THRESHOLD:
            recommendations.append(f"High interruption density: {interruption_density:.1f}/min")

        if noise_level > self.HIGH_NOISE_THRESHOLD:
            recommendations.append(f"High noise level: {noise_level:.2f} — reduce notifications")

        if cognitive_pressure > self.HIGH_COGNITIVE_PRESSURE_THRESHOLD:
            recommendations.append(f"High cognitive pressure: {cognitive_pressure:.2f} — simplify outputs")

        return CalmnessReport(
            calmness_score=round(calmness_score, 2),
            interruption_density=round(interruption_density, 2),
            noise_level=round(noise_level, 2),
            cognitive_pressure=round(cognitive_pressure, 2),
            interaction_stability=round(interaction_stability, 2),
            top_disturbances=top_disturbances,
            recommendations=recommendations,
        )

    def is_calm(self) -> bool:
        """Check if the runtime is currently calm."""
        report = self.get_report()
        return report.calmness_score >= self.LOW_CALMNESS_THRESHOLD

    def get_stats(self) -> Dict[str, Any]:
        """Get calmness statistics."""
        with self._lock:
            events = list(self._events)

        by_type: Dict[str, int] = {}
        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1

        return {
            "total_events": len(events),
            "by_type": by_type,
            "session_duration": time.time() - self._session_start if self._session_start > 0 else 0,
        }
