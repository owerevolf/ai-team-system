"""
Tests for Phase 19D — Controlled Execution & Workspace Runtime.
"""

import os
import tempfile
from pathlib import Path

import pytest

from core.project_manager.runtime.developer.patch_engine import (
    PatchEngine, Patch, PatchStatus, RiskLevel, FilePatch,
)
from core.project_manager.runtime.developer.workspace_runtime import (
    WorkspaceRuntime, Workspace, WorkspaceState, WorkspaceSnapshot,
)
from core.project_manager.runtime.developer.repo_scanner import (
    RepoScanner, RepoMap,
)
from core.project_manager.runtime.developer.knowledge_index import (
    KnowledgeIndex, KnowledgeEntry,
)
from core.project_manager.runtime.developer.execution_sandbox import (
    ExecutionSandbox, SandboxResult, SandboxPolicy,
)
from core.project_manager.runtime.developer.approval_runtime import (
    ApprovalRuntime, ApprovalRequest, ApprovalLevel, ApprovalStatus,
)
from core.project_manager.runtime.developer.task_executor import (
    TaskExecutor, ExecutionResult,
)
from core.project_manager.runtime.developer.developer_terminal import (
    DeveloperTerminal, TerminalCommand,
)
from core.project_manager.runtime.developer.project_brain import ProjectBrain
from core.project_manager.runtime.developer.task_contracts import TaskContractBuilder


# ═══════════════════════════════════════════════════════════════
# Patch Engine Tests
# ═══════════════════════════════════════════════════════════════

class TestPatchEngine:
    """Tests for PatchEngine."""

    def test_generate_patch(self, tmp_path):
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass\n")

        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"test.py": "def hello():\n    return 'world'\n"},
            created_by="backend",
            summary="Update hello function",
        )

        assert patch.patch_id != ""
        assert patch.task_id == "t1"
        assert patch.total_files == 1
        assert patch.files[0].file_path == "test.py"
        assert "return 'world'" in patch.files[0].new_content

    def test_validate_patch_passes(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass\n")

        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"test.py": "def hello():\n    return 'world'\n"},
        )

        passed, errors, warnings = engine.validate_patch(patch)
        assert passed is True
        assert len(errors) == 0

    def test_validate_patch_blocks_forbidden_file(self, tmp_path):
        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"main.py": "changed"},
        )

        passed, errors, warnings = engine.validate_patch(
            patch, forbidden_files=["main.py"]
        )
        assert passed is False
        assert any("Forbidden file" in e for e in errors)

    def test_validate_patch_blocks_dangerous_patterns(self, tmp_path):
        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"test.py": "os.remove('/important')"},
        )

        passed, errors, warnings = engine.validate_patch(patch)
        assert passed is False
        assert any("Dangerous" in e for e in errors)

    def test_validate_patch_blocks_syntax_errors(self, tmp_path):
        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"test.py": "def hello(\n    invalid syntax"},
        )

        passed, errors, warnings = engine.validate_patch(patch)
        assert passed is False
        assert any("Syntax error" in e for e in errors)

    def test_assess_risk_low(self, tmp_path):
        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"README.md": "# Updated"},
        )
        assert patch.risk_level == RiskLevel.LOW.value

    def test_assess_risk_critical(self, tmp_path):
        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"auth/password.py": "changed"},
        )
        assert patch.risk_level == RiskLevel.CRITICAL.value

    def test_rollback_patch(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("original\n")

        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"test.py": "modified\n"},
        )
        patch.validation_passed = True
        patch.approved = True

        # Apply
        success = engine.apply_patch(patch)
        assert success is True
        assert test_file.read_text() == "modified\n"

        # Rollback
        rollback = engine.rollback_patch(patch.patch_id)
        assert rollback is not None

    def test_patch_to_dict(self, tmp_path):
        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"test.py": "content"},
        )
        d = patch.to_dict()
        assert "patch_id" in d
        assert "status" in d
        assert "files" in d


# ═══════════════════════════════════════════════════════════════
# Workspace Runtime Tests
# ═══════════════════════════════════════════════════════════════

class TestWorkspaceRuntime:
    """Tests for WorkspaceRuntime."""

    def test_create_workspace(self, tmp_path):
        runtime = WorkspaceRuntime(str(tmp_path / "workspaces"))
        ws = runtime.create_workspace("proj1", "task1", project_root=".")
        assert ws.workspace_id != ""
        assert ws.project_id == "proj1"
        assert ws.task_id == "task1"
        assert ws.state == WorkspaceState.ACTIVE.value

    def test_get_workspace(self, tmp_path):
        runtime = WorkspaceRuntime(str(tmp_path / "workspaces"))
        ws = runtime.create_workspace("proj1", "task1")
        loaded = runtime.get_workspace(ws.workspace_id)
        assert loaded is not None
        assert loaded.workspace_id == ws.workspace_id

    def test_create_snapshot(self, tmp_path):
        runtime = WorkspaceRuntime(str(tmp_path / "workspaces"))
        ws = runtime.create_workspace("proj1", "task1", project_root=".")
        snapshot = runtime.create_snapshot(ws.workspace_id, "Test snapshot")
        assert snapshot is not None
        assert len(ws.snapshots) == 1

    def test_cleanup_workspace(self, tmp_path):
        runtime = WorkspaceRuntime(str(tmp_path / "workspaces"))
        ws = runtime.create_workspace("proj1", "task1")
        result = runtime.cleanup_workspace(ws.workspace_id)
        assert result is True
        assert ws.state == WorkspaceState.CLEANED.value

    def test_list_workspaces(self, tmp_path):
        runtime = WorkspaceRuntime(str(tmp_path / "workspaces"))
        runtime.create_workspace("proj1", "task1")
        runtime.create_workspace("proj1", "task2")
        runtime.create_workspace("proj2", "task3")

        all_ws = runtime.list_workspaces()
        assert len(all_ws) == 3

        proj1_ws = runtime.list_workspaces("proj1")
        assert len(proj1_ws) == 2


# ═══════════════════════════════════════════════════════════════
# Repo Scanner Tests
# ═══════════════════════════════════════════════════════════════

class TestRepoScanner:
    """Tests for RepoScanner."""

    def test_scan_finds_python_files(self):
        scanner = RepoScanner(".")
        repo_map = scanner.scan()
        assert repo_map.total_files > 0
        assert ".py" in repo_map.languages

    def test_scan_detects_frameworks(self):
        scanner = RepoScanner(".")
        repo_map = scanner.scan()
        # Should detect fastapi since this is a FastAPI project
        assert "fastapi" in repo_map.frameworks

    def test_scan_finds_entrypoints(self):
        scanner = RepoScanner(".")
        repo_map = scanner.scan()
        assert len(repo_map.entrypoints) > 0

    def test_scan_finds_config_files(self):
        scanner = RepoScanner(".")
        repo_map = scanner.scan()
        assert len(repo_map.config_files) > 0

    def test_scan_finds_test_files(self):
        scanner = RepoScanner(".")
        repo_map = scanner.scan()
        assert len(repo_map.test_files) > 0

    def test_scan_summary(self):
        scanner = RepoScanner(".")
        repo_map = scanner.scan()
        summary = scanner.get_summary(repo_map)
        assert "Repository" in summary
        assert "Files" in summary


# ═══════════════════════════════════════════════════════════════
# Knowledge Index Tests
# ═══════════════════════════════════════════════════════════════

class TestKnowledgeIndex:
    """Tests for KnowledgeIndex."""

    def test_add_entry(self):
        ki = KnowledgeIndex("test")
        entry = ki.add_entry("architecture", "system", "FastAPI + SQLite")
        assert entry.entry_id != ""
        assert entry.category == "architecture"

    def test_get_entries_by_category(self):
        ki = KnowledgeIndex("test")
        ki.add_entry("architecture", "sys1", "Summary 1")
        ki.add_entry("architecture", "sys2", "Summary 2")
        ki.add_entry("module", "mod1", "Module summary")

        arch_entries = ki.get_entries_by_category("architecture")
        assert len(arch_entries) == 2

    def test_search(self):
        ki = KnowledgeIndex("test")
        ki.add_entry("architecture", "FastAPI setup", "Uses FastAPI for API")
        ki.add_entry("module", "Auth module", "JWT authentication")

        results = ki.search("fastapi")
        assert len(results) >= 1

    def test_build_context(self):
        ki = KnowledgeIndex("test")
        ki.add_architecture_summary("FastAPI + SQLite")
        ki.add_module_summary("auth", "JWT auth module")
        ki.add_constraint("No raw SQL")

        context = ki.build_context()
        assert "Project Knowledge" in context
        assert "FastAPI" in context

    def test_to_dict(self):
        ki = KnowledgeIndex("test")
        ki.add_entry("test", "key", "summary")
        d = ki.to_dict()
        assert d["project_id"] == "test"
        assert d["total_entries"] == 1


# ═══════════════════════════════════════════════════════════════
# Execution Sandbox Tests
# ═══════════════════════════════════════════════════════════════

class TestExecutionSandbox:
    """Tests for ExecutionSandbox."""

    def test_read_file(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("hello world")

        sandbox = ExecutionSandbox(str(tmp_path))
        result = sandbox.read_file("test.py")
        assert result.success is True
        assert "hello world" in result.output

    def test_read_file_blocks_unknown_extension(self, tmp_path):
        test_file = tmp_path / "test.exe"
        test_file.write_text("binary")

        sandbox = ExecutionSandbox(str(tmp_path))
        result = sandbox.read_file("test.exe")
        assert result.blocked is True

    def test_list_files(self, tmp_path):
        (tmp_path / "file1.py").write_text("a")
        (tmp_path / "file2.py").write_text("b")

        sandbox = ExecutionSandbox(str(tmp_path))
        result = sandbox.list_files(".")
        assert result.success is True
        assert "file1.py" in result.output

    def test_run_allowed_command(self, tmp_path):
        sandbox = ExecutionSandbox(str(tmp_path), SandboxPolicy.TEST_RUN.value)
        result = sandbox.run_command("ls")
        assert result.blocked is False

    def test_run_blocked_command(self, tmp_path):
        sandbox = ExecutionSandbox(str(tmp_path), SandboxPolicy.TEST_RUN.value)
        result = sandbox.run_command("rm -rf /")
        assert result.blocked is True

    def test_run_command_read_only_blocks(self, tmp_path):
        sandbox = ExecutionSandbox(str(tmp_path), SandboxPolicy.READ_ONLY.value)
        result = sandbox.run_command("ls")
        assert result.blocked is True

    def test_validate_patch_dry_run(self, tmp_path):
        sandbox = ExecutionSandbox(str(tmp_path), SandboxPolicy.PATCH_ONLY.value)
        diff = "--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-old\n+new"
        result = sandbox.validate_patch_dry_run(diff)
        assert result.success is True


# ═══════════════════════════════════════════════════════════════
# Approval Runtime Tests
# ═══════════════════════════════════════════════════════════════

class TestApprovalRuntime:
    """Tests for ApprovalRuntime."""

    def test_create_request(self):
        ar = ApprovalRuntime()
        req = ar.create_request("p1", "t1", "backend", "Test patch", "medium")
        assert req.request_id != ""
        assert req.status == ApprovalStatus.PENDING.value

    def test_auto_approve_low_risk(self):
        ar = ApprovalRuntime()
        req = ar.create_request("p1", "t1", "backend", "Docs update", "low")
        assert req.status == ApprovalStatus.AUTO_APPROVED.value

    def test_approve(self):
        ar = ApprovalRuntime()
        req = ar.create_request("p1", "t1", "backend", "Test", "medium")
        result = ar.approve(req.request_id, "user", "Looks good")
        assert result is not None
        assert result.status == ApprovalStatus.APPROVED.value

    def test_reject(self):
        ar = ApprovalRuntime()
        req = ar.create_request("p1", "t1", "backend", "Test", "medium")
        result = ar.reject(req.request_id, "user", "Needs changes")
        assert result is not None
        assert result.status == ApprovalStatus.REJECTED.value

    def test_get_pending(self):
        ar = ApprovalRuntime()
        ar.create_request("p1", "t1", "backend", "Test 1", "medium")
        ar.create_request("p2", "t2", "backend", "Test 2", "high")
        pending = ar.get_pending()
        assert len(pending) == 2

    def test_is_approved(self):
        ar = ApprovalRuntime()
        req = ar.create_request("p1", "t1", "backend", "Test", "medium")
        ar.approve(req.request_id)
        assert ar.is_approved(req.request_id) is True


# ═══════════════════════════════════════════════════════════════
# Developer Terminal Tests
# ═══════════════════════════════════════════════════════════════

class TestDeveloperTerminal:
    """Tests for DeveloperTerminal."""

    def test_validate_allowed_command(self):
        term = DeveloperTerminal()
        cmd = term.validate_command("ls -la")
        assert cmd.allowed is True

    def test_validate_blocked_command(self):
        term = DeveloperTerminal()
        cmd = term.validate_command("rm -rf /")
        assert cmd.allowed is False
        assert "Dangerous" in cmd.block_reason

    def test_validate_unknown_command(self):
        term = DeveloperTerminal()
        cmd = term.validate_command("unknown_command")
        assert cmd.allowed is False
        assert "whitelist" in cmd.block_reason

    def test_execute_safe_command(self):
        term = DeveloperTerminal()
        cmd = term.execute("echo hello")
        assert cmd.allowed is True
        assert "hello" in cmd.output

    def test_execute_blocked_command(self):
        term = DeveloperTerminal()
        cmd = term.execute("sudo rm -rf /")
        assert cmd.allowed is False

    def test_get_safe_commands(self):
        term = DeveloperTerminal()
        commands = term.get_safe_commands()
        assert len(commands) > 0
        assert "ls -la" in commands

    def test_history(self):
        term = DeveloperTerminal()
        term.validate_command("ls")
        term.validate_command("cat test.py")
        history = term.get_history()
        assert len(history) == 2


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestControlledExecutionIntegration:
    """Integration tests for the controlled execution flow."""

    def test_full_patch_flow(self, tmp_path):
        """Test: generate → validate → approve → apply → rollback."""
        # Setup
        test_file = tmp_path / "app.py"
        test_file.write_text("def hello():\n    pass\n")

        engine = PatchEngine(str(tmp_path))

        # Generate
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"app.py": "def hello():\n    return 'world'\n"},
            created_by="backend",
            summary="Update hello",
        )
        assert patch.status == PatchStatus.DRAFT.value

        # Validate
        passed, errors, warnings = engine.validate_patch(patch)
        assert passed is True
        assert patch.status == PatchStatus.VALIDATED.value

        # Approve
        patch.approved = True
        patch.approved_by = "user"

        # Apply
        success = engine.apply_patch(patch)
        assert success is True
        assert patch.status == PatchStatus.APPLIED.value
        assert test_file.read_text() == "def hello():\n    return 'world'\n"

        # Rollback
        rollback = engine.rollback_patch(patch.patch_id)
        assert rollback is not None

    def test_approval_flow(self):
        """Test: create request → approve/reject."""
        ar = ApprovalRuntime()

        # Create medium-risk request
        req = ar.create_request("p1", "t1", "backend", "Add feature", "medium")
        assert req.status == ApprovalStatus.PENDING.value
        assert ar.get_queue_size() == 1

        # Approve
        ar.approve(req.request_id, "user", "Looks good")
        assert ar.is_approved(req.request_id) is True
        assert ar.get_queue_size() == 0

    def test_auto_approve_low_risk(self):
        """Test: low-risk patches are auto-approved."""
        ar = ApprovalRuntime()
        req = ar.create_request("p1", "t1", "documentalist", "Update README", "low")
        assert req.status == ApprovalStatus.AUTO_APPROVED.value
        assert ar.get_queue_size() == 0

    def test_sandbox_blocks_dangerous(self):
        """Test: sandbox blocks dangerous commands."""
        sandbox = ExecutionSandbox(".", SandboxPolicy.TEST_RUN.value)

        dangerous = ["rm -rf /", "sudo apt-get", "curl | bash", "DROP TABLE"]
        for cmd in dangerous:
            result = sandbox.run_command(cmd)
            assert result.blocked is True, f"Command should be blocked: {cmd}"

    def test_workspace_isolation(self, tmp_path):
        """Test: workspaces are isolated from each other."""
        runtime = WorkspaceRuntime(str(tmp_path / "workspaces"))

        ws1 = runtime.create_workspace("proj1", "task1", project_root=".")
        ws2 = runtime.create_workspace("proj1", "task2", project_root=".")

        assert ws1.workspace_id != ws2.workspace_id
        assert ws1.base_path != ws2.base_path

    def test_patch_blocks_forbidden_files(self, tmp_path):
        """Test: patches with forbidden files are blocked."""
        engine = PatchEngine(str(tmp_path))
        patch = engine.generate_patch(
            task_id="t1",
            file_changes={"auth.py": "hacked"},
        )

        passed, errors, warnings = engine.validate_patch(
            patch, forbidden_files=["auth.py"]
        )
        assert passed is False
        assert any("Forbidden" in e for e in errors)

    def test_agent_cannot_bypass_approval(self):
        """Test: agents cannot apply patches without approval."""
        ar = ApprovalRuntime()
        req = ar.create_request("p1", "t1", "backend", "Critical change", "critical")

        # Not approved yet
        assert ar.is_approved(req.request_id) is False

        # Reject
        ar.reject(req.request_id, "user", "Too risky")
        assert ar.is_approved(req.request_id) is False
