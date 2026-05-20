"""
Phase 19E — Real Tooling Integration.

Unified tooling runtime that connects real engineering tools
to the orchestration system. All tools are governed by
execution_governor — no tool runs without approval.

Tool types:
- test_runner
- lint_runner
- formatter
- git_tool
- repo_search
- dependency_inspector
- build_runner

Principle: TOOLS ARE EXECUTION EXTENSIONS, NOT AUTONOMY.
"""

from .tool_runtime import ToolRuntime, ToolRegistry, Capability, ToolResult
from .execution_governor import ExecutionGovernor, GovernorDecision, GovernorPolicy
from .test_runner import TestRunner, TestRunResult
from .lint_runner import LintRunner, LintResult
from .git_runtime import GitRuntime, GitResult
from .dependency_inspector import DependencyInspector, DependencyReport
from .repo_search import RepoSearch, SearchResult
from .build_runner import BuildRunner, BuildResult
from .runtime_metrics import RuntimeMetrics, MetricSnapshot

__all__ = [
    "ToolRuntime", "ToolRegistry", "Capability", "ToolResult",
    "ExecutionGovernor", "GovernorDecision", "GovernorPolicy",
    "TestRunner", "TestRunResult",
    "LintRunner", "LintResult",
    "GitRuntime", "GitResult",
    "DependencyInspector", "DependencyReport",
    "RepoSearch", "SearchResult",
    "BuildRunner", "BuildResult",
    "RuntimeMetrics", "MetricSnapshot",
]
