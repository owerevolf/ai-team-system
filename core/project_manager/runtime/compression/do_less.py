"""
Phase 12, P10: "Do Less" Runtime Philosophy

The most important subsystem of Phase 12.

After 11 phases, the main danger is over-intervention.
Runtime must learn to:
- not react
- not advise
- not interrupt
- not explain
- not optimize

...when operational value is low.

Principle: Restraint as architecture.
Silence is acceptable. Inaction is a feature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class ActionType(Enum):
    REACT = "react"              # React to an event
    ADVISE = "advise"            # Suggest an action
    INTERRUPT = "interrupt"      # Interrupt the user
    EXPLAIN = "explain"          # Generate explanation
    OPTIMIZE = "optimize"        # Optimize something
    LOG = "log"                  # Log information
    NOTIFY = "notify"            # Send notification
    VALIDATE = "validate"        # Run validation
    RECOVER = "recover"          # Attempt recovery
    ADAPT = "adapt"              # Adapt behavior


class ActionValue(Enum):
    """Estimated operational value of an action."""
    CRITICAL = 0     # Must do — safety, data loss, system integrity
    HIGH = 1         # Should do — significant operational benefit
    MEDIUM = 2       # Could do — moderate benefit
    LOW = 3          # Marginal — minimal benefit
    ZERO = 4         # No value — pure overhead


@dataclass
class ProposedAction:
    """An action that runtime is considering taking."""
    action_type: ActionType
    target: str
    estimated_value: ActionValue
    reason: str = ""
    can_defer: bool = True
    deferred: bool = False
    suppressed: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class RestraintDecision:
    """Result of restraint analysis for a proposed action."""
    action: ProposedAction
    should_execute: bool
    reason: str
    alternative: Optional[str] = None


@dataclass
class DoLessReport:
    """Report of "do less" analysis."""
    total_proposed: int = 0
    total_executed: int = 0
    total_suppressed: int = 0
    total_deferred: int = 0
    decisions: list[RestraintDecision] = field(default_factory=list)
    suppressed_actions: list[ProposedAction] = field(default_factory=list)

    @property
    def restraint_ratio(self) -> float:
        """Ratio of suppressed to total — higher means more restraint."""
        if self.total_proposed == 0:
            return 0.0
        return self.total_suppressed / self.total_proposed


class DoLessRuntime:
    """
    Central restraint engine for the runtime.
    Every proposed action passes through this filter.

    Philosophy:
    - Default: don't act
    - Act only when operational value is clear and significant
    - Prefer silence over noise
    - Prefer inaction over marginal action
    - User's attention is the most expensive resource
    """

    def __init__(
        self,
        min_action_value: ActionValue = ActionValue.HIGH,
        allow_interruptions: bool = False,
        allow_advisory: bool = False,
        max_actions_per_minute: int = 5,
    ) -> None:
        self.min_action_value = min_action_value
        self.allow_interruptions = allow_interruptions
        self.allow_advisory = allow_advisory
        self.max_actions_per_minute = max_actions_per_minute
        self._action_history: list[ProposedAction] = []
        self._suppressed_count: int = 0
        self._deferred_count: int = 0

    def evaluate(self, action: ProposedAction) -> RestraintDecision:
        """
        Evaluate a proposed action and decide whether to execute it.
        This is the central restraint gate.
        """
        # CRITICAL value always passes
        if action.estimated_value == ActionValue.CRITICAL:
            self._action_history.append(action)
            return RestraintDecision(
                action=action,
                should_execute=True,
                reason="CRITICAL operational value — always execute",
            )

        # ZERO value always suppressed
        if action.estimated_value == ActionValue.ZERO:
            action.suppressed = True
            self._suppressed_count += 1
            self._action_history.append(action)
            return RestraintDecision(
                action=action,
                should_execute=False,
                reason="ZERO operational value — suppressed",
                alternative="Log at debug level only",
            )

        # LOW value actions: defer, don't suppress
        if action.estimated_value == ActionValue.LOW:
            action.deferred = True
            self._deferred_count += 1
            self._action_history.append(action)
            return RestraintDecision(
                action=action,
                should_execute=False,
                reason="LOW value — deferred to reduce noise",
                alternative="Include in periodic summary",
            )

        # Check minimum value threshold (MEDIUM and above pass)
        if action.estimated_value.value > self.min_action_value.value:
            action.suppressed = True
            self._suppressed_count += 1
            self._action_history.append(action)
            return RestraintDecision(
                action=action,
                should_execute=False,
                reason=f"Value {action.estimated_value.name} below threshold {self.min_action_value.name}",
                alternative="Defer until value increases or user requests",
            )

        # Never advise unless explicitly allowed
        if action.action_type == ActionType.ADVISE and not self.allow_advisory:
            action.suppressed = True
            self._suppressed_count += 1
            self._action_history.append(action)
            return RestraintDecision(
                action=action,
                should_execute=False,
                reason="Advisory actions disabled by policy",
                alternative="Include in summary only if user requests advice",
            )

        # Never interrupt unless explicitly allowed
        if action.action_type == ActionType.INTERRUPT and not self.allow_interruptions:
            action.suppressed = True
            self._suppressed_count += 1
            self._action_history.append(action)
            return RestraintDecision(
                action=action,
                should_execute=False,
                reason="Interruptions disabled by policy",
                alternative="Queue notification for next natural pause",
            )

        # Rate limiting
        if self._is_rate_limited():
            action.deferred = True
            self._deferred_count += 1
            self._action_history.append(action)
            return RestraintDecision(
                action=action,
                should_execute=False,
                reason="Rate limit exceeded — action deferred",
                alternative="Batch with next action window",
            )

        # LOW value actions: defer, don't suppress
        if action.estimated_value == ActionValue.LOW:
            action.deferred = True
            self._deferred_count += 1
            self._action_history.append(action)
            return RestraintDecision(
                action=action,
                should_execute=False,
                reason="LOW value — deferred to reduce noise",
                alternative="Include in periodic summary",
            )

        # Passed all filters — execute
        self._action_history.append(action)
        return RestraintDecision(
            action=action,
            should_execute=True,
            reason="Passed all restraint filters",
        )

    def _is_rate_limited(self) -> bool:
        """Check if we've exceeded the action rate limit."""
        cutoff = time.time() - 60.0
        recent = sum(1 for a in self._action_history if a.timestamp >= cutoff)
        return recent >= self.max_actions_per_minute

    def get_report(self) -> DoLessReport:
        """Generate report of restraint activity."""
        report = DoLessReport()
        report.total_proposed = len(self._action_history)
        report.total_executed = sum(1 for a in self._action_history if not a.suppressed and not a.deferred)
        report.total_suppressed = sum(1 for a in self._action_history if a.suppressed)
        report.total_deferred = sum(1 for a in self._action_history if a.deferred)
        return report

    def set_restraint_level(
        self,
        min_value: Optional[ActionValue] = None,
        allow_interruptions: Optional[bool] = None,
        allow_advisory: Optional[bool] = None,
    ) -> None:
        """Adjust restraint level."""
        if min_value is not None:
            self.min_action_value = min_value
        if allow_interruptions is not None:
            self.allow_interruptions = allow_interruptions
        if allow_advisory is not None:
            self.allow_advisory = allow_advisory

    @property
    def is_silent(self) -> bool:
        """Check if runtime is in silent mode (no actions executed recently)."""
        cutoff = time.time() - 60.0
        return not any(a.timestamp >= cutoff for a in self._action_history)
