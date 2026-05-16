"""
P6 — Explainability Compression (Phase 11)

Layered explanations: compressed by default, expandable without information loss.
Three levels: Operational Summary -> Engineering Reasoning -> Full Trace.

Key principle: every explanation must be losslessly expandable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ExplanationLevel(Enum):
    SUMMARY = "summary"         # 2-3 lines, operational summary
    REASONING = "reasoning"     # Decision logic, key factors
    FULL_TRACE = "full_trace"  # Raw runtime detail


@dataclass
class ExplanationLayer:
    """A single layer of an explanation."""
    level: ExplanationLevel
    content: str
    detail_count: int = 0  # How many raw items this layer represents

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "content": self.content,
            "detail_count": self.detail_count,
        }


@dataclass
class LayeredExplanation:
    """A multi-layer explanation that can be expanded."""
    explanation_id: str
    action_type: str
    action_id: str
    summary: str
    reasoning: str = ""
    full_trace: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    _current_level: ExplanationLevel = ExplanationLevel.SUMMARY

    def get_current(self) -> ExplanationLayer:
        """Get the current explanation layer."""
        if self._current_level == ExplanationLevel.SUMMARY:
            return ExplanationLayer(ExplanationLevel.SUMMARY, self.summary)
        elif self._current_level == ExplanationLevel.REASONING:
            return ExplanationLayer(ExplanationLevel.REASONING, self.reasoning or self.summary)
        else:
            return ExplanationLayer(ExplanationLevel.FULL_TRACE, self.full_trace or self.reasoning or self.summary)

    def expand(self) -> bool:
        """Expand to the next level. Returns False if already at max."""
        if self._current_level == ExplanationLevel.SUMMARY:
            self._current_level = ExplanationLevel.REASONING
            return True
        elif self._current_level == ExplanationLevel.REASONING:
            self._current_level = ExplanationLevel.FULL_TRACE
            return True
        return False

    def collapse(self) -> bool:
        """Collapse to the previous level. Returns False if already at min."""
        if self._current_level == ExplanationLevel.FULL_TRACE:
            self._current_level = ExplanationLevel.REASONING
            return True
        elif self._current_level == ExplanationLevel.REASONING:
            self._current_level = ExplanationLevel.SUMMARY
            return True
        return False

    def set_level(self, level: ExplanationLevel) -> None:
        """Set explanation level directly."""
        self._current_level = level

    def get_level(self) -> ExplanationLevel:
        """Get current explanation level."""
        return self._current_level

    def to_dict(self) -> dict[str, Any]:
        current = self.get_current()
        return {
            "explanation_id": self.explanation_id,
            "action_type": self.action_type,
            "action_id": self.action_id,
            "current_level": self._current_level.value,
            "content": current.content,
            "has_reasoning": bool(self.reasoning),
            "has_full_trace": bool(self.full_trace),
            "can_expand": self._current_level != ExplanationLevel.FULL_TRACE,
            "can_collapse": self._current_level != ExplanationLevel.SUMMARY,
            "metadata": self.metadata,
        }

    def to_full_dict(self) -> dict[str, Any]:
        """Get all layers."""
        return {
            "explanation_id": self.explanation_id,
            "action_type": self.action_type,
            "action_id": self.action_id,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "full_trace": self.full_trace,
            "current_level": self._current_level.value,
            "metadata": self.metadata,
        }


class ExplainabilityCompressor:
    """
    Creates and manages layered explanations.

    Usage:
        compressor = ExplainabilityCompressor()
        exp = compressor.create(
            action_type="file_modify",
            action_id="mod-001",
            summary="Fixed broken import in auth module",
            reasoning="Import 'nonexistent_module' at line 5 caused ImportError. Replaced with 'valid_module'.",
            full_trace="Full trace: scan found error at auth.py:5, symbol resolution failed, ..."
        )
        exp.expand()  # Now shows reasoning
        exp.expand()  # Now shows full trace
        exp.collapse()  # Back to reasoning
    """

    def __init__(self, default_level: ExplanationLevel = ExplanationLevel.SUMMARY) -> None:
        self._explanations: dict[str, LayeredExplanation] = {}
        self._default_level = default_level

    def create(self, action_type: str, action_id: str = "",
               summary: str = "", reasoning: str = "", full_trace: str = "",
               metadata: Optional[dict[str, Any]] = None) -> LayeredExplanation:
        """Create a layered explanation."""
        import uuid
        exp = LayeredExplanation(
            explanation_id=f"exp-{uuid.uuid4().hex[:8]}",
            action_type=action_type,
            action_id=action_id or f"act-{uuid.uuid4().hex[:8]}",
            summary=summary,
            reasoning=reasoning,
            full_trace=full_trace,
            metadata=metadata or {},
            _current_level=self._default_level,
        )
        self._explanations[exp.explanation_id] = exp
        return exp

    def get(self, explanation_id: str) -> Optional[LayeredExplanation]:
        """Get an explanation by ID."""
        return self._explanations.get(explanation_id)

    def get_summary_view(self, explanation_id: str) -> Optional[dict[str, Any]]:
        """Get summary view of an explanation."""
        exp = self._explanations.get(explanation_id)
        if not exp:
            return None
        exp.set_level(ExplanationLevel.SUMMARY)
        return exp.to_dict()

    def get_full_view(self, explanation_id: str) -> Optional[dict[str, Any]]:
        """Get full view of an explanation."""
        exp = self._explanations.get(explanation_id)
        if not exp:
            return None
        return exp.to_full_dict()

    def set_default_level(self, level: ExplanationLevel) -> None:
        """Set default explanation level for new explanations."""
        self._default_level = level

    def get_stats(self) -> dict[str, Any]:
        """Get explainability stats."""
        total = len(self._explanations)
        by_type: dict[str, int] = {}
        by_level: dict[str, int] = {}
        for exp in self._explanations.values():
            t = exp.action_type
            by_type[t] = by_type.get(t, 0) + 1
            l = exp.get_level().value
            by_level[l] = by_level.get(l, 0) + 1
        return {
            "total_explanations": total,
            "by_type": by_type,
            "by_level": by_level,
            "default_level": self._default_level.value,
        }
