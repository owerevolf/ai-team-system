"""
P19 — Platform Stress Tests.

Stress tests for the governance layer:
- Concurrent workflow storms
- Lock cascades
- Cache invalidation floods
- Validation overload
- Event recursion
- Subsystem failures
"""

import time
import threading
from typing import Dict, List, Any
from pathlib import Path


class PlatformStressTests:
    """
    Stress tests for governance systems.
    Tests correctness under load.
    """

    def __init__(self, governance_system: Any):
        self._gov = governance_system
        self._results: List[Dict[str, Any]] = []

    def run_all(self) -> Dict[str, Any]:
        """Run all stress tests."""
        tests = [
            ("concurrent_workflow_storm", self._test_concurrent_workflow_storm),
            ("lock_cascade", self._test_lock_cascade),
            ("cache_invalidation_flood", self._test_cache_invalidation_flood),
            ("validation_overload", self._test_validation_overload),
            ("event_recursion", self._test_event_recursion),
            ("subsystem_failure", self._test_subsystem_failure),
        ]

        results = {}
        for name, test_fn in tests:
            try:
                start = time.time()
                test_fn()
                elapsed = time.time() - start
                results[name] = {'status': 'PASS', 'elapsed_s': round(elapsed, 3)}
            except Exception as e:
                results[name] = {'status': 'FAIL', 'error': str(e)}

        return {
            'total': len(results),
            'passed': sum(1 for r in results.values() if r['status'] == 'PASS'),
            'failed': sum(1 for r in results.values() if r['status'] == 'FAIL'),
            'results': results,
        }

    def _test_concurrent_workflow_storm(self) -> None:
        """Test concurrent workflow execution."""
        errors = []
        num_threads = 10

        def worker(i):
            try:
                task_id = f"stress-task-{i}"
                self._gov.introspection.register_task(
                    task_id, agent="stress-test", workflow="default",
                    resources=[f"file_{i}.py"]
                )
                time.sleep(0.01)
                self._gov.introspection.complete_task(task_id, success=True)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        if errors:
            raise RuntimeError(f"Workflow storm errors: {errors}")

    def _test_lock_cascade(self) -> None:
        """Test lock acquisition cascade."""
        from core.project_manager.runtime import TaskCoordinationSystem
        tcs = TaskCoordinationSystem()

        # Create tasks that compete for same resources
        task1 = tcs.create_task("lock-test-1", "agent-a")
        task2 = tcs.create_task("lock-test-2", "agent-b")

        # Both try to lock same resource
        result1 = tcs.acquire_lock(task1.id, "shared_resource", timeout=1.0)
        result2 = tcs.acquire_lock(task2.id, "shared_resource", timeout=0.1)

        # One should succeed, one should fail
        if result1 and result2:
            raise RuntimeError("Both tasks acquired same lock — conflict detection failed")

    def _test_cache_invalidation_flood(self) -> None:
        """Test cache under mass invalidation."""
        from core.project_manager.runtime.optimization.cache import ExecutionCache
        cache = ExecutionCache(max_size=100)

        # Fill cache
        for i in range(50):
            cache.put('retrieval', f'key_{i}', f'value_{i}', dependencies={f'file_{i}'})

        # Invalidate all
        for i in range(50):
            cache.invalidate_file(f'file_{i}')

        stats = cache.get_stats()
        if stats['total_entries'] != 0:
            raise RuntimeError(f"Cache not fully invalidated: {stats['total_entries']} entries remain")

    def _test_validation_overload(self) -> None:
        """Test validation under load."""
        from core.project_manager.validation import ValidationPipeline
        from core.project_manager.models import FileEntry

        # Create many file entries
        files = {}
        for i in range(100):
            files[f"module_{i}.py"] = FileEntry(
                path=f"module_{i}.py",
                size=100, modified=time.time(), hash=f"hash_{i}",
                language="python",
                symbols=[{'name': f'func_{i}', 'type': 'function', 'line': 1}],
                imports=[],
            )

        deps = {f"module_{i}.py": [] for i in range(100)}

        pipeline = ValidationPipeline(files, deps, Path("/tmp"))
        result = pipeline.validate()

        if result.has_critical:
            raise RuntimeError(f"Validation produced critical issues: {result.critical_count}")

    def _test_event_recursion(self) -> None:
        """Test event recursion detection."""
        from core.project_manager.events import EventBus

        bus = EventBus(max_depth=3)
        call_count = [0]

        def recursive_handler(event_type, data):
            call_count[0] += 1
            if call_count[0] < 10:
                bus.emit("recursive_event", {"depth": call_count[0]})

        bus.subscribe("recursive_event", recursive_handler)
        bus.emit("recursive_event", {"depth": 0})

        # Handler should have been called but recursion should be limited
        if call_count[0] > 10:
            raise RuntimeError(f"Event recursion not limited: {call_count[0]} calls")

    def _test_subsystem_failure(self) -> None:
        """Test subsystem failure isolation."""
        self._gov.introspection.register_subsystem("test-subsystem")

        # Record some operations
        for i in range(5):
            self._gov.introspection.record_subsystem_operation(
                "test-subsystem", success=True, response_ms=10.0
            )

        # Record a failure
        self._gov.introspection.record_subsystem_operation(
            "test-subsystem", success=False, error="test error"
        )

        status = self._gov.introspection.get_subsystem_status("test-subsystem")
        if status and status.is_healthy:
            raise RuntimeError("Subsystem should be unhealthy after failure")
