"""
P16 — Trust Calibration System.

Trust scoring for workflows and decisions.
Low-trust workflows → stricter approval.
High-trust workflows → streamlined execution.

Trust factors:
- Workflow success history
- Rollback frequency
- Patch quality
- Validation stability
- Retrieval accuracy
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TrustLevel(Enum):
    UNTRUSTED = "untrusted"    # new or frequently failing
    LOW = "low"                # some failures
    MEDIUM = "medium"          # mixed results
    HIGH = "high"              # mostly successful
    VERIFIED = "verified"      # consistently reliable


@dataclass
class TrustScore:
    """Trust score for a workflow or component."""
    target_id: str
    target_type: str  # "workflow", "agent", "retrieval", "patch"
    level: TrustLevel = TrustLevel.MEDIUM
    score: float = 0.5  # 0.0 to 1.0
    total_attempts: int = 0
    successes: int = 0
    failures: int = 0
    rollbacks: int = 0
    last_updated: float = 0.0
    history: List[Dict[str, Any]] = field(default_factory=list)


class TrustCalibrationSystem:
    """
    Calibrates trust based on actual performance.
    Low trust → stricter approval. High trust → streamlined.
    """

    # Score thresholds for trust levels
    THRESHOLDS = {
        TrustLevel.VERIFIED: 0.9,
        TrustLevel.HIGH: 0.75,
        TrustLevel.MEDIUM: 0.5,
        TrustLevel.LOW: 0.25,
        TrustLevel.UNTRUSTED: 0.0,
    }

    def __init__(self):
        self._scores: Dict[str, TrustScore] = {}
        self._lock = threading.Lock()

    def register_target(self, target_id: str, target_type: str) -> TrustScore:
        """Register a target for trust tracking."""
        score = TrustScore(
            target_id=target_id,
            target_type=target_type,
            last_updated=time.time(),
        )
        self._scores[target_id] = score
        return score

    def record_success(self, target_id: str, details: Dict[str, Any] = None) -> None:
        """Record a successful operation."""
        score = self._scores.get(target_id)
        if not score:
            return
        score.total_attempts += 1
        score.successes += 1
        score.history.append({
            'timestamp': time.time(),
            'result': 'success',
            'details': details or {},
        })
        self._recalculate(score)

    def record_failure(self, target_id: str, details: Dict[str, Any] = None) -> None:
        """Record a failed operation."""
        score = self._scores.get(target_id)
        if not score:
            return
        score.total_attempts += 1
        score.failures += 1
        score.history.append({
            'timestamp': time.time(),
            'result': 'failure',
            'details': details or {},
        })
        self._recalculate(score)

    def record_rollback(self, target_id: str, reason: str = "") -> None:
        """Record a rollback."""
        score = self._scores.get(target_id)
        if not score:
            return
        score.rollbacks += 1
        score.history.append({
            'timestamp': time.time(),
            'result': 'rollback',
            'reason': reason,
        })
        self._recalculate(score)

    def _recalculate(self, score: TrustScore) -> None:
        """Recalculate trust score."""
        if score.total_attempts == 0:
            score.score = 0.5
            score.level = TrustLevel.MEDIUM
            return

        # Base: success rate
        success_rate = score.successes / score.total_attempts

        # Penalty for rollbacks
        rollback_penalty = min(0.3, score.rollbacks * 0.1)

        # Bonus for volume (more attempts = more data = more reliable)
        volume_bonus = min(0.1, score.total_attempts * 0.01)

        # Recency weighting — recent results matter more
        if score.history:
            recent = score.history[-10:]
            recent_success = sum(1 for h in recent if h['result'] == 'success')
            recent_rate = recent_success / len(recent)
            # Blend overall and recent
            blended = success_rate * 0.4 + recent_rate * 0.6
        else:
            blended = success_rate

        final_score = max(0.0, min(1.0, blended - rollback_penalty + volume_bonus))
        score.score = round(final_score, 3)

        # Determine level
        for level, threshold in sorted(self.THRESHOLDS.items(), key=lambda x: -x[1]):
            if final_score >= threshold:
                score.level = level
                break

        score.last_updated = time.time()

    def get_trust(self, target_id: str) -> Optional[TrustScore]:
        """Get trust score for a target."""
        return self._scores.get(target_id)

    def get_trust_level(self, target_id: str) -> TrustLevel:
        """Get trust level for a target."""
        score = self._scores.get(target_id)
        return score.level if score else TrustLevel.MEDIUM

    def should_streamline(self, target_id: str) -> bool:
        """Check if a target should get streamlined execution (high trust)."""
        score = self._scores.get(target_id)
        if not score:
            return False
        return score.level in (TrustLevel.HIGH, TrustLevel.VERIFIED)

    def should_stricten(self, target_id: str) -> bool:
        """Check if a target should get stricter approval (low trust)."""
        score = self._scores.get(target_id)
        if not score:
            return True  # unknown = strict
        return score.level in (TrustLevel.UNTRUSTED, TrustLevel.LOW)

    def get_all_scores(self) -> Dict[str, TrustScore]:
        """Get all trust scores."""
        return dict(self._scores)

    def get_stats(self) -> Dict[str, Any]:
        """Get trust calibration statistics."""
        by_level = {}
        for score in self._scores.values():
            level = score.level.value
            by_level[level] = by_level.get(level, 0) + 1

        return {
            'total_targets': len(self._scores),
            'by_level': by_level,
            'avg_score': round(
                sum(s.score for s in self._scores.values()) / len(self._scores), 3
            ) if self._scores else 0,
        }
