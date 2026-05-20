"""
developer_trust.py — Developer Trust Layer.

Purpose: Make runtime predictable.
No "AI magic" — all actions explainable.

Functions:
- explain_why_action_happened()
- explain_why_agent_selected()
- explain_why_patch_generated()
- explain_why_context_loaded()
- explain_why_risk_detected()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TrustExplanation:
    """An explanation of why something happened."""
    action: str = ""
    reason: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: float = 1.0
    alternatives_considered: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    def to_human_text(self) -> str:
        """Generate human-readable explanation."""
        lines = [f"## {self.action}", "", f"**Why:** {self.reason}"]

        if self.evidence:
            lines.extend(["", "**Evidence:**"])
            for e in self.evidence:
                lines.append(f"  - {e}")

        if self.alternatives_considered:
            lines.extend(["", "**Alternatives considered:**"])
            for a in self.alternatives_considered:
                lines.append(f"  - {a}")

        if self.risks:
            lines.extend(["", "**Risks:**"])
            for r in self.risks:
                lines.append(f"  - {r}")

        lines.append(f"\n**Confidence:** {self.confidence:.0%}")

        return "\n".join(lines)


class DeveloperTrust:
    """
    Generates explanations for all runtime actions.
    Goal: no "AI magic" — everything is explainable.
    """

    def __init__(self, memory_runtime=None):
        self._memory = memory_runtime

    def explain_action(self, action: str, context: Dict[str, Any]) -> TrustExplanation:
        """Explain why an action happened."""
        explanation = TrustExplanation(action=action)

        action_lower = action.lower()

        if "patch" in action_lower:
            explanation.reason = "Patch was generated to implement the requested change"
            explanation.evidence = [
                f"Task: {context.get('task_title', 'Unknown')}",
                f"Files affected: {len(context.get('files', []))}",
                f"Risk level: {context.get('risk_level', 'unknown')}",
            ]
            explanation.confidence = context.get("confidence", 0.8)
            explanation.risks = context.get("risks", [])

        elif "agent" in action_lower and "select" in action_lower:
            explanation.reason = "Agent was selected based on task requirements and agent capabilities"
            explanation.evidence = [
                f"Task type: {context.get('task_type', 'Unknown')}",
                f"Selected agent: {context.get('agent_id', 'Unknown')}",
                f"Agent capabilities: {', '.join(context.get('capabilities', []))}",
            ]
            explanation.alternatives_considered = context.get("alternatives", [])
            explanation.confidence = 0.9

        elif "context" in action_lower and "load" in action_lower:
            explanation.reason = "Context was loaded to provide the agent with necessary project knowledge"
            explanation.evidence = [
                f"Files loaded: {len(context.get('files', []))}",
                f"Memory entries: {context.get('memory_entries', 0)}",
                f"Token cost: {context.get('token_cost', 0)}",
            ]
            explanation.confidence = 0.95

        elif "risk" in action_lower:
            explanation.reason = "Risk was detected based on file analysis and memory"
            explanation.evidence = context.get("evidence", [])
            explanation.risks = context.get("risks", [])
            explanation.confidence = context.get("confidence", 0.7)

        elif "approval" in action_lower:
            explanation.reason = "Approval was required based on risk level and governance policy"
            explanation.evidence = [
                f"Risk level: {context.get('risk_level', 'unknown')}",
                f"Policy: {context.get('policy', 'default')}",
            ]
            explanation.confidence = 1.0

        else:
            explanation.reason = "Action was performed as part of the workflow"
            explanation.evidence = [f"Context: {str(context)[:200]}"]
            explanation.confidence = 0.5

        return explanation

    def explain_agent_selection(self, task_type: str, agent_id: str,
                                 capabilities: List[str],
                                 alternatives: Optional[List[str]] = None) -> TrustExplanation:
        """Explain why an agent was selected."""
        return TrustExplanation(
            action=f"Agent selected: {agent_id}",
            reason=f"Agent '{agent_id}' was selected for task type '{task_type}' based on capabilities",
            evidence=[
                f"Task type: {task_type}",
                f"Agent capabilities: {', '.join(capabilities)}",
            ],
            alternatives_considered=alternatives or [],
            confidence=0.9,
        )

    def explain_patch_generation(self, task_title: str, files: List[str],
                                  risk_level: str, confidence: float,
                                  risks: Optional[List[str]] = None) -> TrustExplanation:
        """Explain why a patch was generated."""
        return TrustExplanation(
            action=f"Patch generated for: {task_title}",
            reason="Patch was generated to implement the requested change",
            evidence=[
                f"Task: {task_title}",
                f"Files affected: {len(files)}",
                f"Risk level: {risk_level}",
            ],
            risks=risks or [],
            confidence=confidence,
        )

    def explain_risk_detection(self, file_path: str, risk_type: str,
                                evidence: List[str],
                                confidence: float) -> TrustExplanation:
        """Explain why a risk was detected."""
        return TrustExplanation(
            action=f"Risk detected: {risk_type}",
            reason=f"Risk was detected in '{file_path}' based on analysis",
            evidence=evidence,
            confidence=confidence,
        )

    def get_trust_score(self, session_data: Dict[str, Any]) -> float:
        """
        Calculate a trust score for the current session.
        0.0 = no trust, 1.0 = full trust.
        """
        score = 1.0

        # Reduce for unexplained actions
        unexplained = session_data.get("unexplained_actions", 0)
        total_actions = session_data.get("total_actions", 1)
        if total_actions > 0:
            score -= (unexplained / total_actions) * 0.3

        # Reduce for high-risk actions without approval
        unapproved_risks = session_data.get("unapproved_risks", 0)
        score -= unapproved_risks * 0.2

        # Reduce for failed rollbacks
        failed_rollbacks = session_data.get("failed_rollbacks", 0)
        score -= failed_rollbacks * 0.1

        return max(0.0, min(1.0, score))
