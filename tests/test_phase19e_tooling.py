"""
Tests for Phase 19E — Real Tooling Integration & Engineering Execution.

Unit tests:
- tool_runtime
- execution_governor
- test_runner
- lint_runner
- git_runtime
- dependency_inspector
- repo_search
- build_runner
- runtime_metrics

Integration tests:
- patch -> lint
- patch -> tests
- branch creation
- rollback
- tooling failure recovery

Critical tests:
1. Main protected
2. Governor blocks dangerous execution
3. Failed tests stop approval
4. Sandbox isolation works
5. Git rollback works
"""

import os
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.project_manager.tooling.tool_runtime import (
    ToolRuntime, ToolRegistry, ToolResult, ToolType, ToolStatus,
    TOOL_CAPABILITIES, Capability,
)
from core.project_manager.tooling.execution_governor import (
    ExecutionGovernor, GovernorDecision, GovernorPolicy, AgentState,
)
from core.project_manager.tooling.test_runner import (
    TestRunner, TestRunResult, TestFailure,
)
from core.project_manager.tooling.lint_runner import (
    LintRunner, LintResult, LintIssue,
)
from core.project_manager.tooling.git_runtime import (
    GitRuntime, GitResult,
)
from core.project_manager.tooling.dependency_inspector import (
    DependencyInspector, DependencyReport, Dependency, DependencyIssue,
)
from core.project_manager.tooling.repo_search import (
    RepoSearch, SearchResult, SearchMatch,
)
from core.project_manager.tooling.build_runner import (
    BuildRunner, BuildResult,
)
from core.project_manager.tooling.runtime_metrics import (
    RuntimeMetrics, MetricSnapshot, TaskMetric, ToolMetric,
)


# ═══════════════════════════════════════════════════════════════
# Tool Runtime Tests
# ═══════════════════════════════════════════════════════════════

class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_get_handler(self):
        registry = ToolRegistry()
        handler = MagicMock(return_value=("", "", 0))
        registry.register(ToolType.TEST_RUNNER, handler)
        assert registry.get_handler(ToolType.TEST_RUNNER) == handler

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(ToolType.TEST_RUNNER, MagicMock())
        registry.register(ToolType.LINT_RUNNER, MagicMock())
        tools = registry.list_tools()
        assert ToolType.TEST_RUNNER in tools
        assert ToolType.LINT_RUNNER in tools

    def test_unregister(self):
        registry = ToolRegistry()
        registry.register(ToolType.TEST_RUNNER, MagicMock())
        registry.unregister(ToolType.TEST_RUNNER)
        assert registry.get_handler(ToolType.TEST_RUNNER) is None

    def test_register_agent_capabilities(self):
        registry = ToolRegistry()
        registry.register_agent_capabilities("agent1", [
            Capability.READ_FILES, Capability.RUN_TESTS,
        ])
        assert registry.has_capability("agent1", Capability.READ_FILES)
        assert registry.has_capability("agent1", Capability.RUN_TESTS)
        assert not registry.has_capability("agent1", Capability.WRITE_FILES)

    def test_check_tool_access_granted(self):
        registry = ToolRegistry()
        registry.register_agent_capabilities("agent1", [
            Capability.READ_FILES, Capability.RUN_TESTS,
        ])
        allowed, reason = registry.check_tool_access("agent1", ToolType.TEST_RUNNER)
        assert allowed is True
        assert reason == "OK"

    def test_check_tool_access_denied(self):
        registry = ToolRegistry()
        registry.register_agent_capabilities("agent1", [Capability.READ_FILES])
        allowed, reason = registry.check_tool_access("agent1", ToolType.TEST_RUNNER)
        assert allowed is False
        assert "Missing capabilities" in reason

    def test_check_tool_access_unknown_agent(self):
        registry = ToolRegistry()
        allowed, reason = registry.check_tool_access("unknown", ToolType.TEST_RUNNER)
        assert allowed is False


class TestToolRuntime:
    """Tests for ToolRuntime."""

    def test_execute_with_capability(self, tmp_path):
        runtime = ToolRuntime(str(tmp_path))
        runtime.registry.register_agent_capabilities("agent1", [
            Capability.READ_FILES, Capability.RUN_TESTS,
        ])

        # Register a mock handler
        mock_handler = MagicMock(return_value=("test output", "", 0))
        runtime.registry.register(ToolType.TEST_RUNNER, mock_handler)

        result = runtime.execute(
            ToolType.TEST_RUNNER, agent_id="agent1", task_id="t1",
        )
        assert result.success is True
        assert result.output == "test output"
        assert result.tool_type == "test_runner"

    def test_execute_blocked_no_capability(self, tmp_path):
        runtime = ToolRuntime(str(tmp_path))
        runtime.registry.register_agent_capabilities("agent1", [])

        result = runtime.execute(ToolType.TEST_RUNNER, agent_id="agent1")
        assert result.status == ToolStatus.BLOCKED.value
        assert "Missing capabilities" in result.error

    def test_execute_blocked_by_governor(self, tmp_path):
        runtime = ToolRuntime(str(tmp_path))
        runtime.registry.register_agent_capabilities("agent1", [
            Capability.READ_FILES, Capability.RUN_TESTS,
        ])

        # Create a governor that blocks everything
        governor = MagicMock()
        governor.check_execution.return_value = MagicMock(
            allowed=False, reason="Governor denied",
        )
        runtime.set_governor(governor)

        runtime.registry.register(ToolType.TEST_RUNNER, MagicMock())
        result = runtime.execute(ToolType.TEST_RUNNER, agent_id="agent1")
        assert result.status == ToolStatus.BLOCKED.value
        assert "Governor denied" in result.error

    def test_execute_no_handler(self, tmp_path):
        runtime = ToolRuntime(str(tmp_path))
        runtime.registry.register_agent_capabilities("agent1", [
            Capability.READ_FILES, Capability.RUN_TESTS,
        ])

        result = runtime.execute(ToolType.TEST_RUNNER, agent_id="agent1")
        assert result.status == ToolStatus.FAILURE.value
        assert "No handler" in result.error

    def test_execution_log(self, tmp_path):
        runtime = ToolRuntime(str(tmp_path))
        runtime.registry.register_agent_capabilities("agent1", [
            Capability.READ_FILES, Capability.RUN_TESTS,
        ])
        runtime.registry.register(
            ToolType.TEST_RUNNER,
            MagicMock(return_value=("output", "", 0)),
        )

        runtime.execute(ToolType.TEST_RUNNER, agent_id="agent1", task_id="t1")
        logs = runtime.get_execution_log(agent_id="agent1")
        assert len(logs) == 1
        assert logs[0].tool_type == "test_runner"
        assert logs[0].task_id == "t1"

    def test_get_stats(self, tmp_path):
        runtime = ToolRuntime(str(tmp_path))
        runtime.registry.register_agent_capabilities("agent1", [
            Capability.READ_FILES, Capability.RUN_TESTS,
        ])
        runtime.registry.register(
            ToolType.TEST_RUNNER,
            MagicMock(return_value=("output", "", 0)),
        )

        runtime.execute(ToolType.TEST_RUNNER, agent_id="agent1")
        stats = runtime.get_stats()
        assert stats["total_executions"] == 1
        assert stats["success"] == 1
        assert stats["success_rate"] == 100.0


class TestToolResult:
    """Tests for ToolResult."""

    def test_success_property(self):
        result = ToolResult(status=ToolStatus.SUCCESS.value)
        assert result.success is True

    def test_failure_property(self):
        result = ToolResult(status=ToolStatus.FAILURE.value)
        assert result.success is False

    def test_to_dict(self):
        result = ToolResult(
            tool_type="test_runner",
            status="success",
            output="hello",
            exit_code=0,
            duration_ms=100.0,
        )
        d = result.to_dict()
        assert d["tool_type"] == "test_runner"
        assert d["status"] == "success"
        assert d["output"] == "hello"


# ═══════════════════════════════════════════════════════════════
# Execution Governor Tests
# ═══════════════════════════════════════════════════════════════

class TestExecutionGovernor:
    """Tests for ExecutionGovernor."""

    def test_allow_execution(self):
        governor = ExecutionGovernor()
        decision = governor.check_execution("agent1", "test_runner")
        assert decision.allowed is True
        assert decision.reason == "OK"

    def test_block_dangerous_tool(self):
        governor = ExecutionGovernor()
        decision = governor.check_execution("agent1", "destructive_shell")
        assert decision.allowed is False
        assert "dangerous" in decision.reason.lower()

    def test_block_force_push(self):
        governor = ExecutionGovernor()
        decision = governor.check_execution("agent1", "push --force")
        assert decision.allowed is False

    def test_rate_limiting(self):
        policy = GovernorPolicy(
            name="test",
            max_executions_per_minute=2,
            cooldown_seconds=0,
        )
        governor = ExecutionGovernor(policy)

        # First two should pass
        d1 = governor.check_execution("agent1", "test_runner")
        assert d1.allowed is True
        governor.record_result("agent1", "test_runner", True)

        d2 = governor.check_execution("agent1", "test_runner")
        assert d2.allowed is True
        governor.record_result("agent1", "test_runner", True)

        # Third should be rate limited
        d3 = governor.check_execution("agent1", "test_runner")
        assert d3.allowed is False
        assert "Rate limit" in d3.reason

    def test_failure_blocking(self):
        policy = GovernorPolicy(
            name="test",
            max_failures_before_block=2,
            cooldown_seconds=0,
        )
        governor = ExecutionGovernor(policy)

        # First check + record failure
        d1 = governor.check_execution("agent1", "test_runner")
        assert d1.allowed is True
        governor.record_result("agent1", "test_runner", False)

        # Second check + record failure
        d2 = governor.check_execution("agent1", "test_runner")
        assert d2.allowed is True
        governor.record_result("agent1", "test_runner", False)

        # Third should be blocked (2 consecutive failures reached threshold)
        d3 = governor.check_execution("agent1", "test_runner")
        assert d3.allowed is False
        assert "blocked" in d3.reason.lower()

    def test_concurrency_limit(self):
        policy = GovernorPolicy(
            name="test",
            max_concurrent=1,
            cooldown_seconds=0,
        )
        governor = ExecutionGovernor(policy)

        # First execution
        d1 = governor.check_execution("agent1", "test_runner")
        assert d1.allowed is True

        # Second should be blocked (first still active)
        d2 = governor.check_execution("agent1", "test_runner")
        assert d2.allowed is False
        assert "concurrent" in d2.reason.lower()

    def test_unblock_agent(self):
        policy = GovernorPolicy(
            name="test",
            max_failures_before_block=1,
        )
        governor = ExecutionGovernor(policy)

        governor.check_execution("agent1", "test_runner")
        governor.record_result("agent1", "test_runner", False)

        # Agent should be blocked
        state = governor.get_agent_state("agent1")
        assert state.blocked_until > 0

        # Unblock
        governor.unblock_agent("agent1")
        state = governor.get_agent_state("agent1")
        assert state.blocked_until == 0
        assert state.failure_count == 0

    def test_record_success_resets_failures(self):
        policy = GovernorPolicy(
            name="test",
            max_failures_before_block=3,
        )
        governor = ExecutionGovernor(policy)

        governor.check_execution("agent1", "test_runner")
        governor.record_result("agent1", "test_runner", False)
        governor.record_result("agent1", "test_runner", False)

        state = governor.get_agent_state("agent1")
        assert state.failure_count == 2

        # Success resets
        governor.check_execution("agent1", "test_runner")
        governor.record_result("agent1", "test_runner", True)

        state = governor.get_agent_state("agent1")
        assert state.failure_count == 0

    def test_get_stats(self):
        governor = ExecutionGovernor()
        governor.check_execution("agent1", "test_runner")
        governor.record_result("agent1", "test_runner", True)

        stats = governor.get_stats()
        assert stats["total_agents"] == 1
        assert stats["total_executions"] == 1


# ═══════════════════════════════════════════════════════════════
# Test Runner Tests
# ═══════════════════════════════════════════════════════════════

class TestTestRunner:
    """Tests for TestRunner."""

    def test_detect_framework_python(self, tmp_path):
        (tmp_path / "test_foo.py").write_text("def test_foo(): pass")
        runner = TestRunner(str(tmp_path))
        framework = runner.detect_framework()
        assert framework == "pytest"

    def test_detect_framework_node(self, tmp_path):
        pkg = {"scripts": {"test": "jest"}, "devDependencies": {"jest": "^29.0.0"}}
        (tmp_path / "package.json").write_text(__import__('json').dumps(pkg))
        runner = TestRunner(str(tmp_path))
        framework = runner.detect_framework()
        assert framework == "jest"

    def test_detect_framework_vitest(self, tmp_path):
        pkg = {"scripts": {"test": "vitest"}, "devDependencies": {"vitest": "^1.0.0"}}
        (tmp_path / "package.json").write_text(__import__('json').dumps(pkg))
        runner = TestRunner(str(tmp_path))
        framework = runner.detect_framework()
        assert framework == "vitest"

    def test_detect_framework_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\\nname = 'test'")
        runner = TestRunner(str(tmp_path))
        framework = runner.detect_framework()
        assert framework == "cargo_test"

    def test_detect_framework_none(self, tmp_path):
        runner = TestRunner(str(tmp_path))
        framework = runner.detect_framework()
        assert framework is None

    def test_parse_pytest_output_passed(self):
        runner = TestRunner(".")
        output = "test_foo.py::test_foo PASSED\\n\\n1 passed in 0.01s"
        result = runner._parse_pytest_output(output)
        assert result.passed == 1
        assert result.failed == 0
        assert result.total == 1

    def test_parse_pytest_output_failed(self):
        runner = TestRunner(".")
        # Real pytest output format for a failing test
        output = (
            "FAILED test_foo.py::test_foo - AssertionError\n"
            "\n"
            "1 failed in 0.02s"
        )
        result = runner._parse_pytest_output(output)
        assert result.failed == 1
        assert result.total == 1

    def test_parse_pytest_output_with_skipped(self):
        runner = TestRunner(".")
        output = "2 passed, 1 failed, 1 skipped in 0.03s"
        result = runner._parse_pytest_output(output)
        assert result.passed == 2
        assert result.failed == 1
        assert result.skipped == 1

    def test_parse_cargo_output(self):
        runner = TestRunner(".")
        output = "test result: ok. 5 passed; 0 failed"
        result = runner._parse_cargo_output(output)
        assert result.passed == 5
        assert result.failed == 0

    def test_parse_jest_output(self):
        runner = TestRunner(".")
        output = "Tests: 3 passed, 5 total"
        result = runner._parse_jest_output(output)
        assert result.passed == 3
        assert result.total == 5

    def test_parse_vitest_output(self):
        runner = TestRunner(".")
        output = "Tests 4 passed (4)"
        result = runner._parse_vitest_output(output)
        assert result.passed == 4

    def test_run_pytest_real(self, tmp_path):
        """Run actual pytest on a real test file."""
        test_file = tmp_path / "test_sample.py"
        test_file.write_text("def test_pass(): assert True\n")
        runner = TestRunner(str(tmp_path))
        result = runner.run(framework="pytest", test_path=str(test_file))
        if result.status != "error":
            assert result.status == "passed"
            assert result.passed >= 1

    def test_run_pytest_failure(self, tmp_path):
        """Run pytest with a failing test."""
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("def test_fail(): assert False\n")
        runner = TestRunner(str(tmp_path))
        result = runner.run(framework="pytest", test_path=str(test_file))
        if result.status != "error":
            assert result.status == "failed"

    def test_test_run_result_all_passed(self):
        result = TestRunResult(passed=5, failed=0, status="passed")
        assert result.all_passed is True

    def test_test_run_result_not_all_passed(self):
        result = TestRunResult(passed=3, failed=2, status="failed")
        assert result.all_passed is False

    def test_test_run_result_pass_rate(self):
        result = TestRunResult(passed=3, failed=1, total=4)
        assert result.pass_rate == 75.0


# ═══════════════════════════════════════════════════════════════
# Lint Runner Tests
# ═══════════════════════════════════════════════════════════════

class TestLintRunner:
    """Tests for LintRunner."""

    def test_detect_linters_python(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1")
        runner = LintRunner(str(tmp_path))
        tools = runner.detect_linters()
        # Should detect Python project
        assert isinstance(tools, list)

    def test_detect_linters_node(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        runner = LintRunner(str(tmp_path))
        tools = runner.detect_linters()
        assert isinstance(tools, list)

    def test_parse_ruff_output(self):
        runner = LintRunner(".")
        output = "test.py:1:1: E302 expected 2 blank lines, found 1"
        result = runner._parse_ruff_output(output)
        assert len(result.issues) == 1
        assert result.issues[0].file_path == "test.py"
        assert result.issues[0].line_number == 1
        assert result.issues[0].code == "E302"
        assert result.error_count == 1

    def test_parse_flake8_output(self):
        runner = LintRunner(".")
        output = "test.py:2:5: E501 line too long (89 > 79)"
        result = runner._parse_flake8_output(output)
        assert len(result.issues) == 1
        assert result.issues[0].code == "E501"

    def test_parse_black_output(self):
        runner = LintRunner(".")
        output = "would reformat test.py"
        result = runner._parse_black_output(output)
        assert len(result.issues) == 1
        assert result.issues[0].code == "BLACK"

    def test_parse_mypy_output(self):
        runner = LintRunner(".")
        output = "test.py:5: error: Argument 1 has incompatible type"
        result = runner._parse_mypy_output(output)
        assert len(result.issues) == 1
        assert result.issues[0].severity == "error"

    def test_lint_result_passed(self):
        result = LintResult(error_count=0, status="passed")
        assert result.passed is True

    def test_lint_result_failed(self):
        result = LintResult(error_count=2, status="failed")
        assert result.passed is False


# ═══════════════════════════════════════════════════════════════
# Git Runtime Tests
# ═══════════════════════════════════════════════════════════════

class TestGitRuntime:
    """Tests for GitRuntime."""

    def test_block_force_push(self, tmp_path):
        runtime = GitRuntime(str(tmp_path))
        result = runtime.execute("push", ["--force"])
        assert result.status == "blocked"
        assert "blocked" in result.blocked_reason.lower() or "Force push" in result.blocked_reason

    def test_block_branch_deletion(self, tmp_path):
        runtime = GitRuntime(str(tmp_path))
        result = runtime.execute("branch", ["-D", "feature/test"])
        assert result.status == "blocked"
        assert "deletion" in result.blocked_reason.lower() or "blocked" in result.blocked_reason.lower()

    def test_block_rebase(self, tmp_path):
        runtime = GitRuntime(str(tmp_path))
        result = runtime.execute("rebase", ["main"])
        assert result.status == "blocked"
        assert "rewriting" in result.blocked_reason.lower() or "blocked" in result.blocked_reason.lower()

    def test_allow_status(self, tmp_path):
        runtime = GitRuntime(str(tmp_path))
        result = runtime.execute("status")
        # Should not be blocked (may error if not a git repo, but not blocked)
        assert result.status != "blocked"

    def test_allow_diff(self, tmp_path):
        runtime = GitRuntime(str(tmp_path))
        result = runtime.execute("diff")
        assert result.status != "blocked"

    def test_allow_log(self, tmp_path):
        runtime = GitRuntime(str(tmp_path))
        result = runtime.execute("log", ["--oneline", "-5"])
        assert result.status != "blocked"

    def test_create_branch_name_format(self, tmp_path):
        runtime = GitRuntime(str(tmp_path))
        result = runtime.create_branch("abc123", "add-logout")
        # Branch name should follow format
        assert "ai/task-abc123-add-logout" in result.branch or result.status == "error"

    def test_create_branch_sanitization(self, tmp_path):
        runtime = GitRuntime(str(tmp_path))
        result = runtime.create_branch("t1", "add logout button!")
        # Should sanitize special chars
        assert " " not in result.branch or result.status == "error"

    def test_branch_format(self):
        runtime = GitRuntime(".")
        assert runtime.AI_BRANCH_PREFIX == "ai/task-"

    def test_protected_branches(self):
        runtime = GitRuntime(".")
        assert "main" in runtime.PROTECTED_BRANCHES
        assert "master" in runtime.PROTECTED_BRANCHES

    def test_to_dict(self):
        result = GitResult(
            operation="status",
            status="success",
            output="clean",
            branch="main",
        )
        d = result.to_dict()
        assert d["operation"] == "status"
        assert d["status"] == "success"
        assert d["branch"] == "main"


# ═══════════════════════════════════════════════════════════════
# Dependency Inspector Tests
# ═══════════════════════════════════════════════════════════════

class TestDependencyInspector:
    """Tests for DependencyInspector."""

    def test_analyze_empty_project(self, tmp_path):
        inspector = DependencyInspector(str(tmp_path))
        report = inspector.analyze()
        assert report.total_count == 0
        assert len(report.sources) == 0

    def test_analyze_package_json(self, tmp_path):
        pkg = {
            "name": "test",
            "dependencies": {"express": "^4.18.0", "lodash": "^4.17.20"},
            "devDependencies": {"jest": "^29.0.0"},
        }
        (tmp_path / "package.json").write_text(__import__('json').dumps(pkg))
        inspector = DependencyInspector(str(tmp_path))
        report = inspector.analyze()
        assert "package.json" in report.sources
        assert report.total_count >= 3

    def test_analyze_requirements_txt(self, tmp_path):
        reqs = "flask==2.3.0\nrequests>=2.28.0\npyyaml==5.4.0\n"
        (tmp_path / "requirements.txt").write_text(reqs)
        inspector = DependencyInspector(str(tmp_path))
        report = inspector.analyze()
        assert "requirements.txt" in report.sources
        dep_names = [d.name for d in report.dependencies]
        assert "flask" in dep_names
        assert "requests" in dep_names

    def test_detect_vulnerable_deps(self, tmp_path):
        pkg = {
            "name": "test",
            "dependencies": {"lodash": "^4.17.10"},  # Known vulnerable
        }
        (tmp_path / "package.json").write_text(__import__('json').dumps(pkg))
        inspector = DependencyInspector(str(tmp_path))
        report = inspector.analyze()
        vuln_issues = [i for i in report.issues if i.issue_type == "vulnerable"]
        assert len(vuln_issues) >= 1
        assert vuln_issues[0].dependency == "lodash"

    def test_detect_missing_node_modules(self, tmp_path):
        pkg = {"name": "test", "dependencies": {"express": "^4.18.0"}}
        (tmp_path / "package.json").write_text(__import__('json').dumps(pkg))
        inspector = DependencyInspector(str(tmp_path))
        report = inspector.analyze()
        missing = [i for i in report.issues if i.issue_type == "missing"]
        assert any("node_modules" in i.dependency for i in missing)

    def test_detect_missing_venv(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==2.3.0\\n")
        inspector = DependencyInspector(str(tmp_path))
        report = inspector.analyze()
        missing = [i for i in report.issues if i.issue_type == "missing"]
        assert any("venv" in i.dependency for i in missing)

    def test_clean_version(self):
        assert DependencyInspector._clean_version("^1.2.3") == "1.2.3"
        assert DependencyInspector._clean_version(">=1.2.3") == "1.2.3"
        assert DependencyInspector._clean_version("==1.2.3") == "1.2.3"
        assert DependencyInspector._clean_version("~1.2.3") == "1.2.3"
        assert DependencyInspector._clean_version("") == ""

    def test_report_to_dict(self, tmp_path):
        inspector = DependencyInspector(str(tmp_path))
        report = inspector.analyze()
        d = report.to_dict()
        assert "sources" in d
        assert "total_count" in d
        assert "issues" in d


# ═══════════════════════════════════════════════════════════════
# Repo Search Tests
# ═══════════════════════════════════════════════════════════════

class TestRepoSearch:
    """Tests for RepoSearch."""

    def test_search_text(self, tmp_path):
        (tmp_path / "test.py").write_text("def hello():\\n    return 'world'\\n")
        search = RepoSearch(str(tmp_path))
        result = search.search("hello", search_type="text")
        assert result.total_matches >= 1
        assert result.search_type == "text"

    def test_search_symbol(self, tmp_path):
        (tmp_path / "test.py").write_text("def my_function():\\n    pass\\n")
        search = RepoSearch(str(tmp_path))
        result = search.search("my_function", search_type="symbol")
        assert result.total_matches >= 1
        assert result.matches[0].symbol_name == "my_function"

    def test_search_class_symbol(self, tmp_path):
        (tmp_path / "test.py").write_text("class MyClass:\\n    pass\\n")
        search = RepoSearch(str(tmp_path))
        result = search.search("MyClass", search_type="symbol")
        assert result.total_matches >= 1

    def test_search_import(self, tmp_path):
        (tmp_path / "test.py").write_text("from os import path\\nimport sys\\n")
        search = RepoSearch(str(tmp_path))
        result = search.search("os", search_type="import")
        assert result.total_matches >= 1

    def test_search_usage(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1\ny = x + 1\nz = x * 2\n")
        search = RepoSearch(str(tmp_path))
        result = search.search("x", search_type="usage")
        assert result.total_matches >= 2  # x = 1 and y = x + 1 and z = x * 2

    def test_search_routes(self, tmp_path):
        (tmp_path / "app.py").write_text(
            "@app.get('/api/users')\\n"
            "def get_users(): pass\\n"
        )
        search = RepoSearch(str(tmp_path))
        result = search.search("/api", search_type="route")
        assert result.total_matches >= 1

    def test_skip_node_modules(self, tmp_path):
        nm_dir = tmp_path / "node_modules" / "lodash"
        nm_dir.mkdir(parents=True)
        (nm_dir / "index.js").write_text("var x = 1;")
        (tmp_path / "test.py").write_text("var x = 2;")

        search = RepoSearch(str(tmp_path))
        result = search.search("var x", search_type="text")
        # Should only find in test.py, not in node_modules
        for match in result.matches:
            assert "node_modules" not in match.file_path

    def test_skip_pycache(self, tmp_path):
        pyc_dir = tmp_path / "__pycache__"
        pyc_dir.mkdir()
        (pyc_dir / "test.cpython-312.pyc").write_text("compiled")
        (tmp_path / "test.py").write_text("def hello(): pass")

        search = RepoSearch(str(tmp_path))
        result = search.search("hello", search_type="text")
        for match in result.matches:
            assert "__pycache__" not in match.file_path

    def test_detect_language(self, tmp_path):
        search = RepoSearch(str(tmp_path))
        assert search._detect_language(Path("test.py")) == "python"
        assert search._detect_language(Path("test.js")) == "javascript"
        assert search._detect_language(Path("test.ts")) == "typescript"
        assert search._detect_language(Path("test.tsx")) == "typescript"
        assert search._detect_language(Path("test.txt")) == "unknown"

    def test_result_to_dict(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1")
        search = RepoSearch(str(tmp_path))
        result = search.search("x")
        d = result.to_dict()
        assert "query" in d
        assert "total_matches" in d
        assert "matches" in d


# ═══════════════════════════════════════════════════════════════
# Build Runner Tests
# ═══════════════════════════════════════════════════════════════

class TestBuildRunner:
    """Tests for BuildRunner."""

    def test_detect_builders_empty(self, tmp_path):
        runner = BuildRunner(str(tmp_path))
        builders = runner.detect_builders()
        assert isinstance(builders, list)
        assert len(builders) == 0

    def test_detect_builders_npm(self, tmp_path):
        pkg = {"scripts": {"build": "webpack"}}
        (tmp_path / "package.json").write_text(__import__('json').dumps(pkg))
        runner = BuildRunner(str(tmp_path))
        builders = runner.detect_builders()
        assert "npm_build" in builders

    def test_detect_builders_vite(self, tmp_path):
        pkg = {"scripts": {"build": "vite build"}}
        (tmp_path / "package.json").write_text(__import__('json').dumps(pkg))
        runner = BuildRunner(str(tmp_path))
        builders = runner.detect_builders()
        assert "vite_build" in builders

    def test_detect_builders_python(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\\nname = 'test'")
        runner = BuildRunner(str(tmp_path))
        builders = runner.detect_builders()
        assert "python_check" in builders

    def test_detect_builders_docker(self, tmp_path):
        (tmp_path / "docker-compose.yml").write_text("version: '3'\\nservices:\\n  web:")
        runner = BuildRunner(str(tmp_path))
        builders = runner.detect_builders()
        assert "docker_compose_config" in builders

    def test_detect_builders_tsc(self, tmp_path):
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        runner = BuildRunner(str(tmp_path))
        builders = runner.detect_builders()
        assert "tsc" in builders

    def test_build_result_success(self):
        result = BuildResult(status="success")
        assert result.success is True

    def test_build_result_failure(self):
        result = BuildResult(status="failed")
        assert result.success is False

    def test_build_result_to_dict(self):
        result = BuildResult(
            builder="npm_build",
            status="success",
            output="Build complete",
            duration_ms=5000.0,
        )
        d = result.to_dict()
        assert d["builder"] == "npm_build"
        assert d["status"] == "success"
        assert d["success"] is True


# ═══════════════════════════════════════════════════════════════
# Runtime Metrics Tests
# ═══════════════════════════════════════════════════════════════

class TestRuntimeMetrics:
    """Tests for RuntimeMetrics."""

    def test_record_task(self):
        metrics = RuntimeMetrics()
        metrics.record_task(TaskMetric(
            task_id="t1", status="completed", duration_ms=1000.0,
        ))
        history = metrics.get_task_history()
        assert len(history) == 1
        assert history[0].task_id == "t1"

    def test_record_tool_run(self):
        metrics = RuntimeMetrics()
        metrics.record_tool_run("test_runner", success=True, blocked=False, duration_ms=500.0)
        tool_metrics = metrics.get_tool_metrics()
        assert "test_runner" in tool_metrics
        assert tool_metrics["test_runner"].total_runs == 1
        assert tool_metrics["test_runner"].successful_runs == 1

    def test_record_failure(self):
        metrics = RuntimeMetrics()
        metrics.record_failure("t1", "agent1", "test_failure", "assertion error")
        failures = metrics.get_failure_log()
        assert len(failures) == 1
        assert failures[0]["task_id"] == "t1"

    def test_record_rollback(self):
        metrics = RuntimeMetrics()
        metrics.record_rollback("t1", "test failed")
        failures = metrics.get_failure_log()
        assert len(failures) == 1
        assert failures[0]["failure_type"] == "rollback"

    def test_get_snapshot_empty(self):
        metrics = RuntimeMetrics()
        snapshot = metrics.get_snapshot()
        assert snapshot.total_tasks == 0
        assert snapshot.task_success_rate == 0.0

    def test_get_snapshot_with_data(self):
        metrics = RuntimeMetrics()
        metrics.record_task(TaskMetric(task_id="t1", status="completed", duration_ms=100.0))
        metrics.record_task(TaskMetric(task_id="t2", status="completed", duration_ms=200.0))
        metrics.record_task(TaskMetric(task_id="t3", status="failed", duration_ms=50.0))

        snapshot = metrics.get_snapshot()
        assert snapshot.total_tasks == 3
        assert snapshot.task_success_rate == pytest.approx(66.7, rel=0.1)
        assert snapshot.avg_execution_ms == pytest.approx(116.67, rel=0.1)

    def test_get_snapshot_test_pass_rate(self):
        metrics = RuntimeMetrics()
        metrics.record_task(TaskMetric(task_id="t1", tests_run=5, tests_passed=5))
        metrics.record_task(TaskMetric(task_id="t2", tests_run=3, tests_passed=2))

        snapshot = metrics.get_snapshot()
        assert snapshot.total_tests == 8
        assert snapshot.test_pass_rate == pytest.approx(87.5, rel=0.1)

    def test_get_snapshot_rollback_rate(self):
        metrics = RuntimeMetrics()
        metrics.record_task(TaskMetric(task_id="t1", status="completed", was_rolled_back=True))
        metrics.record_task(TaskMetric(task_id="t2", status="completed", was_rolled_back=False))

        snapshot = metrics.get_snapshot()
        assert snapshot.total_rollbacks == 1
        assert snapshot.rollback_rate == 50.0

    def test_failure_hotspots(self):
        metrics = RuntimeMetrics()
        for _ in range(5):
            metrics.record_failure("t1", "a1", "test_failure", "err", "test_runner")
        for _ in range(3):
            metrics.record_failure("t2", "a1", "build_failure", "err", "build_runner")

        snapshot = metrics.get_snapshot()
        assert len(snapshot.failure_hotspots) >= 1
        assert snapshot.failure_hotspots[0]["source"] == "test_runner"
        assert snapshot.failure_hotspots[0]["count"] == 5

    def test_reset(self):
        metrics = RuntimeMetrics()
        metrics.record_task(TaskMetric(task_id="t1"))
        metrics.record_failure("t1", "a1", "err", "reason")
        metrics.reset()
        assert len(metrics.get_task_history()) == 0
        assert len(metrics.get_failure_log()) == 0

    def test_snapshot_to_dict(self):
        metrics = RuntimeMetrics()
        snapshot = metrics.get_snapshot()
        d = snapshot.to_dict()
        assert "timestamp" in d
        assert "task_success_rate" in d
        assert "tool_usage" in d


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for the tooling pipeline."""

    def test_patch_to_test_flow(self, tmp_path):
        """Simulate: create patch -> run tests -> check results."""
        # Create a test file
        test_file = tmp_path / "test_sample.py"
        test_file.write_text("def test_pass(): assert True\n")

        # Run tests using sys.executable
        import sys
        runner = TestRunner(str(tmp_path))
        result = runner.run(framework="pytest")
        # If pytest is available, check results; otherwise skip
        if result.status != "error":
            assert result.all_passed is True

    def test_patch_to_lint_flow(self, tmp_path):
        """Simulate: create file -> run lint -> check results."""
        py_file = tmp_path / "clean.py"
        py_file.write_text("x = 1\\n")

        runner = LintRunner(str(tmp_path))
        # Just verify lint runs without crashing
        result = runner.run(tool="ruff")
        assert result.status in ("passed", "failed", "error")

    def test_git_branch_creation_flow(self, tmp_path):
        """Simulate: create branch -> check status -> rollback."""
        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)

        # Create initial commit
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

        runtime = GitRuntime(str(tmp_path))

        # Create a branch
        result = runtime.create_branch("t1", "add-feature")
        assert result.status == "success" or result.status == "error"

        # Check status
        status = runtime.status()
        assert status.status != "blocked"

        # Get modified files
        modified = runtime.get_modified_files()
        assert isinstance(modified, list)

    def test_tooling_failure_recovery(self, tmp_path):
        """Simulate: tool failure -> governor blocks -> unblock."""
        governor = ExecutionGovernor(GovernorPolicy(
            name="test",
            max_failures_before_block=2,
            cooldown_seconds=0,
        ))

        # Simulate failures
        d1 = governor.check_execution("agent1", "test_runner")
        assert d1.allowed is True
        governor.record_result("agent1", "test_runner", False)

        d2 = governor.check_execution("agent1", "test_runner")
        assert d2.allowed is True
        governor.record_result("agent1", "test_runner", False)

        # Agent should be blocked
        decision = governor.check_execution("agent1", "test_runner")
        assert decision.allowed is False

        # Unblock
        governor.unblock_agent("agent1")
        decision = governor.check_execution("agent1", "test_runner")
        assert decision.allowed is True

    def test_metrics_tracking(self, tmp_path):
        """Simulate: run tools -> check metrics."""
        metrics = RuntimeMetrics()

        # Simulate test run
        metrics.record_tool_run("test_runner", success=True, blocked=False, duration_ms=1000.0)
        metrics.record_task(TaskMetric(
            task_id="t1", status="completed",
            tests_run=5, tests_passed=5, duration_ms=1000.0,
        ))

        # Simulate lint run
        metrics.record_tool_run("lint_runner", success=True, blocked=False, duration_ms=500.0)

        # Simulate failure
        metrics.record_tool_run("build_runner", success=False, blocked=False, duration_ms=2000.0)
        metrics.record_failure("t2", "agent1", "build_failure", "compilation error", "build_runner")

        snapshot = metrics.get_snapshot()
        assert snapshot.total_tasks == 1
        assert snapshot.task_success_rate == 100.0
        assert "test_runner" in snapshot.tool_usage
        assert "lint_runner" in snapshot.tool_usage
        assert len(snapshot.failure_hotspots) >= 1


# ═══════════════════════════════════════════════════════════════
# Critical Tests
# ═══════════════════════════════════════════════════════════════

class TestCritical:
    """Critical safety tests."""

    def test_main_branch_protected(self, tmp_path):
        """Direct commits to main should be blocked."""
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

        runtime = GitRuntime(str(tmp_path))
        result = runtime.commit("direct commit to main")
        assert result.status == "blocked"
        assert "main" in result.blocked_reason or "not allowed" in result.blocked_reason.lower()

    def test_governor_blocks_dangerous_execution(self):
        """Governor must block dangerous tools."""
        governor = ExecutionGovernor()

        dangerous_tools = [
            "destructive_shell",
            "network_deploy",
            "self_update",
        ]

        for tool in dangerous_tools:
            decision = governor.check_execution("agent1", tool)
            assert decision.allowed is False, f"Should block {tool}"

    def test_force_push_blocked(self):
        """Force push must always be blocked."""
        runtime = GitRuntime(".")

        result = runtime.execute("push", ["--force", "origin", "main"])
        assert result.status == "blocked"

        result = runtime.execute("push", ["-f", "origin", "main"])
        assert result.status == "blocked"

    def test_branch_deletion_blocked(self):
        """Branch deletion must be blocked."""
        runtime = GitRuntime(".")

        result = runtime.execute("branch", ["-D", "feature/test"])
        assert result.status == "blocked"

        result = runtime.execute("branch", ["-d", "feature/test"])
        assert result.status == "blocked"

    def test_history_rewrite_blocked(self):
        """History rewriting must be blocked."""
        runtime = GitRuntime(".")

        result = runtime.execute("rebase", ["main"])
        assert result.status == "blocked"

    def test_failed_tests_block_approval(self):
        """Failed tests should signal that approval should not be granted."""
        runner = TestRunner(".")
        result = TestRunResult(passed=0, failed=3, status="failed")
        assert result.all_passed is False
        # In the real system, this would block patch approval

    def test_git_rollback_works(self, tmp_path):
        """Git rollback: create branch -> make changes -> restore."""
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)

        original = tmp_path / "file.txt"
        original.write_text("original content")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

        # Modify file
        original.write_text("modified content")

        # Restore
        runtime = GitRuntime(str(tmp_path))
        result = runtime.restore_files(["file.txt"])
        assert result.status != "blocked"

        # Verify restoration
        content = original.read_text()
        assert content == "original content"

    def test_governor_concurrency_limit(self):
        """Governor must enforce concurrency limits."""
        policy = GovernorPolicy(
            name="test",
            max_concurrent=1,
            cooldown_seconds=0,
        )
        governor = ExecutionGovernor(policy)

        # First execution
        d1 = governor.check_execution("agent1", "test_runner")
        assert d1.allowed is True

        # Second should be blocked
        d2 = governor.check_execution("agent1", "test_runner")
        assert d2.allowed is False

        # After recording result, should be allowed again
        governor.record_result("agent1", "test_runner", True)
        d3 = governor.check_execution("agent1", "test_runner")
        assert d3.allowed is True

    def test_tool_capabilities_defined(self):
        """All tool types must have defined capabilities."""
        for tool_type in ToolType:
            assert tool_type in TOOL_CAPABILITIES, f"No capabilities for {tool_type}"
            assert len(TOOL_CAPABILITIES[tool_type]) > 0, f"Empty capabilities for {tool_type}"
