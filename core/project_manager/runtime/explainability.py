"""
P10 — Execution Explainability.

The system must explain WHY it made each decision.
Explainability = trust infrastructure.

Explains:
- Why a workflow was chosen
- Why a retrieval set was selected
- Why a patch is considered safe
- Why validation failed
- Why risk is elevated
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ExplainabilityTopic(Enum):
    WORKFLOW_CHOICE = "workflow_choice"
    RETRIEVAL_SET = "retrieval_set"
    PATCH_SAFETY = "patch_safety"
    VALIDATION_RESULT = "validation_result"
    RISK_ASSESSMENT = "risk_assessment"
    APPROVAL_DECISION = "approval_decision"
    MERGE_DECISION = "merge_decision"
    BRANCH_CHOICE = "branch_choice"


@dataclass
class Explanation:
    """A single explanation."""
    topic: ExplainabilityTopic
    decision: str  # what was decided
    reason: str  # why
    evidence: List[str] = field(default_factory=list)  # supporting facts
    confidence: float = 1.0
    alternatives: List[str] = field(default_factory=list)  # what else was considered
    timestamp: float = 0.0


class ExecutionExplainability:
    """
    Generates explanations for runtime decisions.
    Every decision must be traceable and explainable.
    """

    def __init__(self):
        self._explanations: List[Explanation] = []

    def explain_workflow_choice(self, workflow: str, task_type: str,
                                 risk_level: str,
                                 available: List[str]) -> Explanation:
        """Explain why a workflow was chosen."""
        evidence = [
            f"Task type: {task_type}",
            f"Risk level: {risk_level}",
            f"Available workflows: {', '.join(available)}",
        ]

        reason = f"Selected '{workflow}' based on task type '{task_type}'"
        if risk_level in ("high", "critical"):
            reason += f" with elevated risk controls ({risk_level})"

        alternatives = [w for w in available if w != workflow]

        exp = Explanation(
            topic=ExplainabilityTopic.WORKFLOW_CHOICE,
            decision=workflow,
            reason=reason,
            evidence=evidence,
            confidence=0.9,
            alternatives=alternatives,
            timestamp=time.time(),
        )
        self._explanations.append(exp)
        return exp

    def explain_retrieval_set(self, query: str, files_selected: List[str],
                               total_candidates: int,
                               scoring_details: Dict[str, float] = None) -> Explanation:
        """Explain why specific files were retrieved."""
        evidence = [
            f"Query: {query}",
            f"Candidates: {total_candidates}",
            f"Selected: {len(files_selected)} files",
        ]
        if scoring_details:
            top_scored = sorted(scoring_details.items(), key=lambda x: -x[1])[:5]
            for fname, score in top_scored:
                evidence.append(f"  {fname}: score={score:.1f}")

        reason = f"Selected {len(files_selected)} from {total_candidates} candidates"
        if files_selected:
            reason += " based on relevance scoring"

        exp = Explanation(
            topic=ExplainabilityTopic.RETRIEVAL_SET,
            decision=", ".join(files_selected[:5]),
            reason=reason,
            evidence=evidence,
            confidence=0.85,
            timestamp=time.time(),
        )
        self._explanations.append(exp)
        return exp

    def explain_patch_safety(self, file_path: str, is_safe: bool,
                              risk_score: float,
                              checks_passed: List[str],
                              checks_failed: List[str]) -> Explanation:
        """Explain why a patch is considered safe or unsafe."""
        evidence = [
            f"File: {file_path}",
            f"Risk score: {risk_score:.2f}",
            f"Checks passed: {len(checks_passed)}",
            f"Checks failed: {len(checks_failed)}",
        ]
        for check in checks_passed[:5]:
            evidence.append(f"  ✓ {check}")
        for check in checks_failed[:5]:
            evidence.append(f"  ✗ {check}")

        if is_safe:
            reason = f"Patch is safe (risk={risk_score:.2f})"
            if checks_passed:
                reason += f" — passed {len(checks_passed)} safety checks"
        else:
            reason = f"Patch is unsafe (risk={risk_score:.2f})"
            if checks_failed:
                reason += f" — failed: {', '.join(checks_failed[:3])}"

        exp = Explanation(
            topic=ExplainabilityTopic.PATCH_SAFETY,
            decision="safe" if is_safe else "unsafe",
            reason=reason,
            evidence=evidence,
            confidence=0.8 if is_safe else 0.9,
            timestamp=time.time(),
        )
        self._explanations.append(exp)
        return exp

    def explain_validation_result(self, result: Any) -> Explanation:
        """Explain validation results."""
        summary = result.summary() if hasattr(result, 'summary') else {}

        evidence = [
            f"Files checked: {summary.get('files_checked', 'N/A')}",
            f"Symbols checked: {summary.get('symbols_checked', 'N/A')}",
            f"Critical: {summary.get('critical', 0)}",
            f"Errors: {summary.get('errors', 0)}",
            f"Warnings: {summary.get('warnings', 0)}",
        ]

        has_errors = summary.get('has_errors', False)
        if has_errors:
            reason = f"Validation failed with {summary.get('errors', 0)} errors"
            if summary.get('critical', 0) > 0:
                reason += f" ({summary['critical']} critical)"
        else:
            reason = "Validation passed"
            if summary.get('warnings', 0) > 0:
                reason += f" with {summary['warnings']} warnings"

        exp = Explanation(
            topic=ExplainabilityTopic.VALIDATION_RESULT,
            decision="passed" if not has_errors else "failed",
            reason=reason,
            evidence=evidence,
            confidence=0.95,
            timestamp=time.time(),
        )
        self._explanations.append(exp)
        return exp

    def explain_risk_assessment(self, risk_level: str, risk_score: float,
                                 factors: Dict[str, float]) -> Explanation:
        """Explain why risk is at a certain level."""
        evidence = [f"Overall risk score: {risk_score:.2f}"]
        for factor, value in sorted(factors.items(), key=lambda x: -x[1]):
            evidence.append(f"  {factor}: {value:.2f}")

        reason = f"Risk level: {risk_level} (score={risk_score:.2f})"
        top_factors = sorted(factors.items(), key=lambda x: -x[1])[:3]
        if top_factors:
            reason += f" — primary factors: {', '.join(f[0] for f in top_factors)}"

        exp = Explanation(
            topic=ExplainabilityTopic.RISK_ASSESSMENT,
            decision=risk_level,
            reason=reason,
            evidence=evidence,
            confidence=0.85,
            timestamp=time.time(),
        )
        self._explanations.append(exp)
        return exp

    def get_explanations(self, topic: ExplainabilityTopic = None,
                         limit: int = 50) -> List[Explanation]:
        """Get explanations, optionally filtered by topic."""
        explanations = self._explanations
        if topic:
            explanations = [e for e in explanations if e.topic == topic]
        return explanations[-limit:]

    def format_explanation(self, exp: Explanation) -> str:
        """Format an explanation for human reading."""
        lines = [
            f"## {exp.topic.value.replace('_', ' ').title()}",
            "",
            f"Decision: {exp.decision}",
            f"Reason: {exp.reason}",
            f"Confidence: {exp.confidence:.0%}",
            "",
        ]
        if exp.evidence:
            lines.append("Evidence:")
            for e in exp.evidence:
                lines.append(f"  - {e}")
            lines.append("")
        if exp.alternatives:
            lines.append(f"Alternatives considered: {', '.join(exp.alternatives)}")
            lines.append("")
        return "\n".join(lines)
