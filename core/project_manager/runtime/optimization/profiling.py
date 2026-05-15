"""
Execution Profiling & Token Economy — performance budgets and cost tracking.

Tracks:
- Validation latency
- Retrieval latency
- Graph traversal time
- Patch application cost
- Merge time
- Workflow duration
- Token usage per workflow
- Context assembly cost

All deterministic. No AI cost estimation.
"""

import time
import threading
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ProfileEntry:
    """A single profiling measurement."""
    operation: str
    duration_ms: float
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class TokenUsage:
    """Token usage tracking for a workflow."""
    retrieval_tokens: int = 0
    context_tokens: int = 0
    prompt_tokens: int = 0
    response_tokens: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def total_tokens(self) -> int:
        return self.retrieval_tokens + self.context_tokens + self.prompt_tokens + self.response_tokens

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class ExecutionProfiler:
    """
    Profiles execution performance across all PM operations.

    Features:
    - Per-operation timing
    - Performance budgets (warn when exceeded)
    - Historical tracking
    - Hotspot detection
    """

    DEFAULT_BUDGETS = {
        'retrieval': 500.0,      # ms
        'validation': 1000.0,    # ms
        'graph_traversal': 200.0, # ms
        'patch_application': 100.0, # ms
        'merge': 300.0,          # ms
        'impact_analysis': 200.0, # ms
        'context_assembly': 100.0, # ms
        'symbol_lookup': 50.0,   # ms
    }

    def __init__(self, budgets: Optional[Dict[str, float]] = None):
        self._profiles: List[ProfileEntry] = []
        self._budgets = budgets or self.DEFAULT_BUDGETS.copy()
        self._lock = threading.Lock()

    def start(self, operation: str) -> 'ProfileContext':
        """Start profiling an operation. Use as context manager."""
        return ProfileContext(self, operation)

    def record(self, operation: str, duration_ms: float, metadata: Optional[Dict] = None) -> None:
        """Record a profiling measurement."""
        with self._lock:
            entry = ProfileEntry(
                operation=operation,
                duration_ms=duration_ms,
                metadata=metadata or {},
            )
            self._profiles.append(entry)

            # Check budget
            budget = self._budgets.get(operation)
            if budget and duration_ms > budget:
                import logging
                logging.getLogger('profiler').warning(
                    f"Performance budget exceeded: {operation} "
                    f"({duration_ms:.1f}ms > {budget:.1f}ms)"
                )

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get profiling statistics."""
        with self._lock:
            profiles = self._profiles
            if operation:
                profiles = [p for p in profiles if p.operation == operation]

            if not profiles:
                return {'count': 0}

            durations = [p.duration_ms for p in profiles]

            return {
                'count': len(durations),
                'total_ms': round(sum(durations), 2),
                'avg_ms': round(sum(durations) / len(durations), 2),
                'min_ms': round(min(durations), 2),
                'max_ms': round(max(durations), 2),
                'p95_ms': round(sorted(durations)[int(len(durations) * 0.95)], 2) if len(durations) > 1 else durations[0],
                'budget_violations': sum(
                    1 for d in durations
                    if self._budgets.get(operation or '', 0) > 0
                    and d > self._budgets.get(operation or '', float('inf'))
                ),
            }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get stats for all operations."""
        with self._lock:
            operations = set(p.operation for p in self._profiles)

            return {
                'total_measurements': len(self._profiles),
                'operations': {
                    op: self.get_stats(op) for op in operations
                },
                'budgets': self._budgets.copy(),
            }

    def get_hotspots(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get top performance hotspots."""
        with self._lock:
            op_stats: Dict[str, List[float]] = defaultdict(list)
            for p in self._profiles:
                op_stats[p.operation].append(p.duration_ms)

            hotspots = []
            for op, durations in op_stats.items():
                avg = sum(durations) / len(durations)
                budget = self._budgets.get(op, 0)
                hotspots.append({
                    'operation': op,
                    'avg_ms': round(avg, 2),
                    'max_ms': round(max(durations), 2),
                    'count': len(durations),
                    'budget_ms': budget,
                    'over_budget': budget > 0 and avg > budget,
                })

            hotspots.sort(key=lambda x: -x['avg_ms'])
            return hotspots[:top_n]

    def reset(self) -> None:
        """Clear all profiling data."""
        with self._lock:
            self._profiles.clear()


class ProfileContext:
    """Context manager for profiling."""

    def __init__(self, profiler: ExecutionProfiler, operation: str):
        self._profiler = profiler
        self._operation = operation
        self._start = 0.0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, *args):
        duration_ms = (time.time() - self._start) * 1000
        self._profiler.record(self._operation, duration_ms)


class TokenEconomy:
    """
    Tracks and budgets token usage across workflows.

    Features:
    - Per-workflow token tracking
    - Token budgets
    - Cache hit rate tracking
    - Cost optimization suggestions
    """

    DEFAULT_BUDGETS = {
        'retrieval': 4000,      # tokens
        'context': 8000,        # tokens
        'prompt': 2000,         # tokens
        'total_per_workflow': 15000,  # tokens
    }

    def __init__(self, budgets: Optional[Dict[str, int]] = None):
        self._budgets = budgets or self.DEFAULT_BUDGETS.copy()
        self._usage: Dict[str, TokenUsage] = defaultdict(TokenUsage)
        self._lock = threading.Lock()

    def track(self, workflow_id: str, usage: TokenUsage) -> None:
        """Track token usage for a workflow."""
        with self._lock:
            self._usage[workflow_id] = usage

    def record_retrieval(self, workflow_id: str, tokens: int, cache_hit: bool = False) -> None:
        """Record retrieval token usage."""
        with self._lock:
            u = self._usage[workflow_id]
            u.retrieval_tokens += tokens
            if cache_hit:
                u.cache_hits += 1
            else:
                u.cache_misses += 1

    def record_context(self, workflow_id: str, tokens: int) -> None:
        """Record context token usage."""
        with self._lock:
            self._usage[workflow_id].context_tokens += tokens

    def check_budget(self, workflow_id: str) -> Dict[str, Any]:
        """Check if a workflow is within token budget."""
        with self._lock:
            usage = self._usage.get(workflow_id)
            if not usage:
                return {'within_budget': True, 'usage': None}

            total = usage.total_tokens
            budget = self._budgets.get('total_per_workflow', 15000)

            return {
                'within_budget': total <= budget,
                'total_tokens': total,
                'budget': budget,
                'overage': max(0, total - budget),
                'cache_hit_rate': usage.cache_hit_rate,
                'breakdown': {
                    'retrieval': usage.retrieval_tokens,
                    'context': usage.context_tokens,
                    'prompt': usage.prompt_tokens,
                    'response': usage.response_tokens,
                },
            }

    def get_expensive_workflows(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get most expensive workflows by token usage."""
        with self._lock:
            sorted_workflows = sorted(
                self._usage.items(),
                key=lambda x: x[1].total_tokens,
                reverse=True,
            )

            return [
                {
                    'workflow_id': wid,
                    'total_tokens': usage.total_tokens,
                    'cache_hit_rate': round(usage.cache_hit_rate, 3),
                    'breakdown': {
                        'retrieval': usage.retrieval_tokens,
                        'context': usage.context_tokens,
                        'prompt': usage.prompt_tokens,
                        'response': usage.response_tokens,
                    },
                }
                for wid, usage in sorted_workflows[:top_n]
            ]

    def get_stats(self) -> Dict[str, Any]:
        """Get token economy statistics."""
        with self._lock:
            if not self._usage:
                return {'workflows': 0}

            totals = [u.total_tokens for u in self._usage.values()]
            return {
                'workflows': len(self._usage),
                'total_tokens': sum(totals),
                'avg_tokens': round(sum(totals) / len(totals)),
                'max_tokens': max(totals),
                'min_tokens': min(totals),
                'budgets': self._budgets.copy(),
            }
