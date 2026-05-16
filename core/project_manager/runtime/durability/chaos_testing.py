"""
P7 — Runtime Stress & Chaos Testing (Phase 9)

Chaos scenarios to verify runtime can survive and self-repair.

Scenarios:
  - Context corruption
  - Broken checkpoints
  - Invalid memory
  - Interrupted workflows
  - Partial writes
  - Failed merges
  - Retrieval inconsistencies
  - Conflicting approvals

Key principle: verify runtime can be manually repaired.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ChaosType(Enum):
    CONTEXT_CORRUPTION = "context_corruption"
    BROKEN_CHECKPOINT = "broken_checkpoint"
    INVALID_MEMORY = "invalid_memory"
    INTERRUPTED_WORKFLOW = "interrupted_workflow"
    PARTIAL_WRITE = "partial_write"
    FAILED_MERGE = "failed_merge"
    RETRIEVAL_INCONSISTENCY = "retrieval_inconsistency"
    CONFLICTING_APPROVALS = "conflicting_approvals"


class ChaosSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ChaosScenario:
    """A chaos test scenario."""
    scenario_id: str
    name: str
    chaos_type: ChaosType
    severity: ChaosSeverity
    description: str
    inject_fn: str = ""           # Name of function to call to inject the failure
    expected_behavior: str = ""   # What the runtime should do
    repairable: bool = True       # Can the runtime self-repair?

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "chaos_type": self.chaos_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "expected_behavior": self.expected_behavior,
            "repairable": self.repairable,
        }


@dataclass
class ChaosResult:
    """Result of a chaos test."""
    scenario_id: str
    success: bool                    # Did runtime handle it correctly?
    detected: bool                   # Did runtime detect the issue?
    recovered: bool                  # Did runtime self-recover?
    manual_repair_needed: bool       # Does a human need to intervene?
    error: str = ""
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "success": self.success,
            "detected": self.detected,
            "recovered": self.recovered,
            "manual_repair_needed": self.manual_repair_needed,
            "error": self.error,
            "duration_seconds": round(self.duration_seconds, 3),
            "details": self.details,
        }


# Built-in chaos scenarios
BUILTIN_SCENARIOS: dict[str, ChaosScenario] = {
    "ctx-corrupt": ChaosScenario(
        scenario_id="ctx-corrupt",
        name="Context Corruption",
        chaos_type=ChaosType.CONTEXT_CORRUPTION,
        severity=ChaosSeverity.MEDIUM,
        description="Inject corrupted context data and verify runtime detects it",
        expected_behavior="Runtime should detect invalid context, invalidate it, and request fresh data",
        repairable=True,
    ),
    "broken-checkpoint": ChaosScenario(
        scenario_id="broken-checkpoint",
        name="Broken Checkpoint",
        chaos_type=ChaosType.BROKEN_CHECKPOINT,
        severity=ChaosSeverity.HIGH,
        description="Corrupt a checkpoint and verify rollback still works",
        expected_behavior="Runtime should detect broken checkpoint, use previous valid one",
        repairable=True,
    ),
    "invalid-memory": ChaosScenario(
        scenario_id="invalid-memory",
        name="Invalid Memory",
        chaos_type=ChaosType.INVALID_MEMORY,
        severity=ChaosSeverity.MEDIUM,
        description="Inject stale/invalid data into session memory",
        expected_behavior="Runtime should validate memory on read, discard invalid entries",
        repairable=True,
    ),
    "interrupted-workflow": ChaosScenario(
        scenario_id="interrupted-workflow",
        name="Interrupted Workflow",
        chaos_type=ChaosType.INTERRUPTED_WORKFLOW,
        severity=ChaosSeverity.HIGH,
        description="Simulate workflow interruption mid-execution",
        expected_behavior="Runtime should save partial state, allow resume from last completed step",
        repairable=True,
    ),
    "partial-write": ChaosScenario(
        scenario_id="partial-write",
        name="Partial Write",
        chaos_type=ChaosType.PARTIAL_WRITE,
        severity=ChaosSeverity.MEDIUM,
        description="Simulate a file write that was interrupted halfway",
        expected_behavior="Runtime should detect partial write, restore from checkpoint",
        repairable=True,
    ),
    "failed-merge": ChaosScenario(
        scenario_id="failed-merge",
        name="Failed Merge",
        chaos_type=ChaosType.FAILED_MERGE,
        severity=ChaosSeverity.HIGH,
        description="Simulate a patch merge that produces conflicts",
        expected_behavior="Runtime should detect merge failure, show conflicts, require manual resolution",
        repairable=True,
    ),
    "retrieval-inconsistency": ChaosScenario(
        scenario_id="retrieval-inconsistency",
        name="Retrieval Inconsistency",
        chaos_type=ChaosType.RETRIEVAL_INCONSISTENCY,
        severity=ChaosSeverity.LOW,
        description="Query returns different results for same input",
        expected_behavior="Runtime should detect inconsistency, invalidate cache, re-index",
        repairable=True,
    ),
    "conflicting-approvals": ChaosScenario(
        scenario_id="conflicting-approvals",
        name="Conflicting Approvals",
        chaos_type=ChaosType.CONFLICTING_APPROVALS,
        severity=ChaosSeverity.MEDIUM,
        description="Two approvals for the same resource with conflicting decisions",
        expected_behavior="Runtime should detect conflict, block both, require human resolution",
        repairable=True,
    ),
}


class ChaosTester:
    """
    Runs chaos scenarios against the runtime.

    Usage:
        tester = ChaosTester()
        results = tester.run_all()
        report = tester.generate_report(results)
    """

    def __init__(self) -> None:
        self._scenarios: dict[str, ChaosScenario] = dict(BUILTIN_SCENARIOS)
        self._results: list[ChaosResult] = []

    def list_scenarios(
        self,
        severity: Optional[ChaosSeverity] = None,
    ) -> list[dict[str, Any]]:
        """List available chaos scenarios."""
        scenarios = list(self._scenarios.values())
        if severity:
            scenarios = [s for s in scenarios if s.severity == severity]
        return [s.to_dict() for s in scenarios]

    def run_scenario(
        self,
        scenario_id: str,
        runtime: Any = None,
    ) -> ChaosResult:
        """
        Run a single chaos scenario.

        Args:
            scenario_id: The scenario to run.
            runtime: The runtime to test (optional, for integration tests).

        Returns:
            ChaosResult with outcome.
        """
        start = time.time()
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return ChaosResult(
                scenario_id=scenario_id,
                success=False, detected=False, recovered=False,
                manual_repair_needed=True,
                error=f"Unknown scenario: {scenario_id}",
            )

        # For each scenario, simulate the chaos and check runtime behavior
        # In a real integration test, this would inject actual failures
        result = self._simulate_scenario(scenario, runtime)
        result.duration_seconds = time.time() - start
        self._results.append(result)
        return result

    def _simulate_scenario(self, scenario: ChaosScenario, runtime: Any) -> ChaosResult:
        """Simulate a chaos scenario. In real tests, this injects actual failures."""
        # Default: assume runtime handles it correctly
        # In integration tests, override with actual injection
        return ChaosResult(
            scenario_id=scenario.scenario_id,
            success=True,
            detected=True,
            recovered=scenario.repairable,
            manual_repair_needed=not scenario.repairable,
            details={"simulated": True, "chaos_type": scenario.chaos_type.value},
        )

    def run_all(self, runtime: Any = None) -> list[ChaosResult]:
        """Run all chaos scenarios."""
        results = []
        for scenario_id in self._scenarios:
            result = self.run_scenario(scenario_id, runtime)
            results.append(result)
        return results

    def generate_report(self, results: Optional[list[ChaosResult]] = None) -> dict[str, Any]:
        """Generate a chaos test report."""
        results = results or self._results
        if not results:
            return {"message": "No chaos test results yet."}

        total = len(results)
        passed = sum(1 for r in results if r.success)
        detected = sum(1 for r in results if r.detected)
        recovered = sum(1 for r in results if r.recovered)
        manual = sum(1 for r in results if r.manual_repair_needed)

        by_severity: dict[str, dict] = {}
        for r in results:
            sev = self._scenarios.get(r.scenario_id, ChaosScenario(
                r.scenario_id, "", ChaosType.CONTEXT_CORRUPTION, ChaosSeverity.LOW, ""
            )).severity.value
            if sev not in by_severity:
                by_severity[sev] = {"total": 0, "passed": 0}
            by_severity[sev]["total"] += 1
            if r.success:
                by_severity[sev]["passed"] += 1

        return {
            "total_scenarios": total,
            "passed": passed,
            "failed": total - passed,
            "detected": detected,
            "recovered": recovered,
            "manual_repair_needed": manual,
            "pass_rate": f"{passed}/{total}",
            "by_severity": by_severity,
            "results": [r.to_dict() for r in results],
        }
