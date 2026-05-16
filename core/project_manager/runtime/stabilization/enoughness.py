"""
Phase 16, P10: "Enoughness" Engine

The most important subsystem of Phase 16.

Runtime must learn to answer: "Is this already enough?"
Not: "Can we add more?" but "Does this improve survivability?"

Principle: Disciplined bounded engineering > capability maximalism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EnoughnessQuestion(Enum):
    IMPROVES_SURVIVABILITY = "improves_survivability"      # Does this help the system survive?
    REDUCES_COMPLEXITY = "reduces_complexity"              # Does this make things simpler?
    REDUCES_FRICTION = "reduces_friction"                  # Does this reduce contributor friction?
    PRESERVES_IDENTITY = "preserves_identity"              # Does this preserve core identity?
    ENABLES_GROWTH = "enables_growth"                      # Does this enable healthy growth?


class EnoughnessVerdict(Enum):
    ENOUGH = "enough"              # System is sufficient in this area
    NEEDS_WORK = "needs_work"      # Gaps exist, work needed
    OVERBUILT = "overbuilt"        # Too much complexity for the value
    UNDERBUILT = "underbuilt"      # Critical gaps remain


@dataclass
class EnoughnessAssessment:
    """Assessment of whether a subsystem is "enough"."""
    area: str
    verdict: EnoughnessVerdict
    score: float                   # 0-1, higher = more "enough"
    reasoning: str
    recommendations: list[str] = field(default_factory=list)


@dataclass
class EnoughnessReport:
    """Full enoughness report."""
    assessments: list[EnoughnessAssessment] = field(default_factory=list)
    overall_verdict: EnoughnessVerdict = EnoughnessVerdict.ENOUGH

    @property
    def overbuilt_areas(self) -> list[EnoughnessAssessment]:
        return [a for a in self.assessments if a.verdict == EnoughnessVerdict.OVERBUILT]

    @property
    def underbuilt_areas(self) -> list[EnoughnessAssessment]:
        return [a for a in self.assessments if a.verdict == EnoughnessVerdict.UNDERBUILT]


class EnoughnessEngine:
    """
    Evaluates whether the system is "enough" — whether further
    expansion is justified or whether consolidation is needed.
    """

    AREA_ASSESSMENTS: dict[str, dict] = {
        "durability": {
            "verdict": EnoughnessVerdict.ENOUGH,
            "score": 0.85,
            "reasoning": "Recovery, state lifecycle, GC, chaos testing are comprehensive. large_repo is only experimental piece.",
            "recommendations": ["Freeze core durability. large_repo can still evolve."],
        },
        "ergonomics": {
            "verdict": EnoughnessVerdict.ENOUGH,
            "score": 0.80,
            "reasoning": "Attention, calm mode, approval intelligence, time protection are solid. intent_centric is experimental.",
            "recommendations": ["Freeze attention and calm mode. intent_centric can still evolve."],
        },
        "trust": {
            "verdict": EnoughnessVerdict.NEEDS_WORK,
            "score": 0.70,
            "reasoning": "Visibility and personality are stable. drift detection and adaptation inspector need more validation.",
            "recommendations": ["Freeze visibility and personality. Collect data on drift detection before freezing."],
        },
        "compression": {
            "verdict": EnoughnessVerdict.ENOUGH,
            "score": 0.85,
            "reasoning": "do_less, interaction minimalism, operational calm are well-designed. progressive disclosure is experimental.",
            "recommendations": ["Freeze do_less and interaction_minimalism."],
        },
        "coherence": {
            "verdict": EnoughnessVerdict.NEEDS_WORK,
            "score": 0.65,
            "reasoning": "Vocabulary is stable. Ontology drift and dependency gravity need more data.",
            "recommendations": ["Freeze vocabulary. Monitor drift detection."],
        },
        "ecosystem": {
            "verdict": EnoughnessVerdict.UNDERBUILT,
            "score": 0.55,
            "reasoning": "Onboarding and plugin governance are solid. Fork drift, ecosystem coherence, succession are experimental.",
            "recommendations": ["Freeze onboarding and plugin governance. Others need more experimentation."],
        },
        "stabilization": {
            "verdict": EnoughnessVerdict.ENOUGH,
            "score": 0.75,
            "reasoning": "Consolidation, freeze zones, hardening, slimming are comprehensive for this phase.",
            "recommendations": ["Execute consolidation plan. Then freeze stabilization itself."],
        },
    }

    def __init__(self) -> None:
        self._areas: dict[str, EnoughnessAssessment] = {}
        self._register_assessments()

    def _register_assessments(self) -> None:
        """Register area assessments."""
        for area, data in self.AREA_ASSESSMENTS.items():
            self._areas[area] = EnoughnessAssessment(
                area=area,
                verdict=data["verdict"],
                score=data["score"],
                reasoning=data["reasoning"],
                recommendations=data.get("recommendations", []),
            )

    def assess(self, area: str) -> Optional[EnoughnessAssessment]:
        """Assess whether an area is "enough"."""
        return self._areas.get(area)

    def generate_report(self) -> EnoughnessReport:
        """Generate full enoughness report."""
        assessments = list(self._areas.values())

        # Determine overall verdict
        verdicts = [a.verdict for a in assessments]
        if EnoughnessVerdict.UNDERBUILT in verdicts:
            overall = EnoughnessVerdict.NEEDS_WORK
        elif EnoughnessVerdict.OVERBUILT in verdicts:
            overall = EnoughnessVerdict.OVERBUILT
        elif all(v == EnoughnessVerdict.ENOUGH for v in verdicts):
            overall = EnoughnessVerdict.ENOUGH
        else:
            overall = EnoughnessVerdict.NEEDS_WORK

        return EnoughnessReport(assessments=assessments, overall_verdict=overall)

    def should_expand(self, area: str, proposal: str) -> tuple[bool, str]:
        """Evaluate whether a proposed expansion is justified."""
        assessment = self._areas.get(area)
        if not assessment:
            return True, f"Area '{area}' not assessed — expansion allowed with normal governance"

        if assessment.verdict == EnoughnessVerdict.OVERBUILT:
            return False, (
                f"Area '{area}' is overbuilt (score: {assessment.score:.0%}). "
                f"Proposal '{proposal}' should be rejected. "
                f"Recommendation: {assessment.recommendations[0] if assessment.recommendations else 'Consolidate first'}"
            )

        if assessment.verdict == EnoughnessVerdict.ENOUGH:
            return False, (
                f"Area '{area}' is sufficient (score: {assessment.score:.0%}). "
                f"Proposal '{proposal}' must demonstrate clear survivability improvement. "
                f"Default: reject unless strong justification."
            )

        if assessment.verdict == EnoughnessVerdict.UNDERBUILT:
            return True, (
                f"Area '{area}' needs work (score: {assessment.score:.0%}). "
                f"Proposal '{proposal}' is allowed if it addresses known gaps."
            )

        return True, f"Area '{area}' needs work — expansion allowed"

    @property
    def total_areas(self) -> int:
        return len(self._areas)
