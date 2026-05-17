"""
Tests for all Phase 8 workspace modules.

Covers:
  - project_importer (P1)
  - project_understanding (P8)
  - project_sandbox (P16)
  - repo_repair (P3)
  - session_memory (P11)
  - task_traceability (P9)
  - patch_review (P10)
  - user_modes (P13/P17/P18)
  - project_health (P2)
"""

import json
import os
import tempfile
import shutil
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ===========================================================================
# Helpers
# ===========================================================================

@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_python_project(tmp_dir):
    """Create a minimal Python project for testing."""
    root = Path(tmp_dir) / "sample_project"
    root.mkdir()
    (root / "main.py").write_text("import os\nimport sys\n\ndef main():\n    print('hello')\n\nif __name__ == '__main__':\n    main()\n")
    (root / "requirements.txt").write_text("requests>=2.28\nflask>=2.0\n")
    (root / "README.md").write_text("# Sample Project\n")
    src = root / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "utils.py").write_text("def helper():\n    return True\n")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_utils.py").write_text("from src.utils import helper\ndef test_helper():\n    assert helper()\n")
    return str(root)


@pytest.fixture
def sample_js_project(tmp_dir):
    """Create a minimal JS project for testing."""
    root = Path(tmp_dir) / "js_project"
    root.mkdir()
    (root / "package.json").write_text(json.dumps({
        "name": "test-app",
        "version": "1.0.0",
        "dependencies": {"express": "^4.18"},
        "devDependencies": {}
    }))
    (root / "index.js").write_text("const app = require('express')();\napp.listen(3000);\n")
    return str(root)


@pytest.fixture
def git_repo(tmp_dir):
    """Create a temporary git repository."""
    root = Path(tmp_dir) / "git_repo"
    root.mkdir()
    os.system(f"cd {root} && git init -q && git config user.email 'test@test.com' && git config user.name 'Test' && echo 'hello' > file.txt && git add -A && git commit -q -m 'init'")
    return str(root)


# ===========================================================================
# P1 — Project Importer
# ===========================================================================

class TestProjectImporter:
    def setup_method(self):
        from core.project_manager.workspace.project_importer import ProjectImporter
        self.Importer = ProjectImporter

    def test_detect_local_path(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        assert imp.detect_source_type(tmp_dir) == "local"

    def test_detect_github_url(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        assert imp.detect_source_type("https://github.com/owner/repo") == "github"

    def test_detect_github_short(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        assert imp.detect_source_type("github:owner/repo") == "github"

    def test_detect_zip(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        assert imp.detect_source_type("/path/to/archive.zip") == "zip"

    def test_detect_unknown(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        assert imp.detect_source_type("not_a_real_source") == "unknown"

    def test_import_local_folder(self, tmp_dir, sample_python_project):
        imp = self.Importer(projects_dir=tmp_dir)
        result = imp.import_project(sample_python_project, project_name="imported")
        assert result["errors"] == []
        assert result["project_path"] is not None
        assert result["source_type"] == "local"
        assert result["file_count"] > 0
        assert result["import_time"] >= 0

    def test_import_local_nonexistent(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        result = imp.import_project("/nonexistent/path/xyz")
        assert len(result["errors"]) > 0

    def test_import_local_duplicate_name(self, tmp_dir, sample_python_project):
        imp = self.Importer(projects_dir=tmp_dir)
        imp.import_project(sample_python_project, project_name="dup")
        result = imp.import_project(sample_python_project, project_name="dup")
        assert any("already exists" in e for e in result["errors"])

    def test_import_zip(self, tmp_dir, sample_python_project):
        # Create a zip from the sample project
        zip_path = os.path.join(tmp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for root, dirs, files in os.walk(sample_python_project):
                for f in files:
                    fp = os.path.join(root, f)
                    arcname = os.path.relpath(fp, sample_python_project)
                    zf.write(fp, arcname)

        imp = self.Importer(projects_dir=tmp_dir)
        result = imp.import_project(zip_path, project_name="from_zip")
        assert result["errors"] == []
        assert result["project_path"] is not None
        assert result["source_type"] == "zip"
        assert result["file_count"] > 0

    def test_import_zip_not_found(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        result = imp.import_project("/nonexistent/archive.zip")
        assert len(result["errors"]) > 0

    def test_extract_zip_slip_protection(self, tmp_dir):
        zip_path = os.path.join(tmp_dir, "slip.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../etc/passwd", "malicious")

        imp = self.Importer(projects_dir=tmp_dir)
        result = imp.extract_zip(zip_path, os.path.join(tmp_dir, "extracted"))
        assert any("Zip slip" in e for e in result["errors"])

    def test_validate_imported_project(self, tmp_dir, sample_python_project):
        imp = self.Importer(projects_dir=tmp_dir)
        result = imp.validate_imported_project(sample_python_project)
        assert result["valid"] is True
        assert result["file_count"] > 0
        assert result["broken_symlinks"] == []

    def test_validate_nonexistent(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        result = imp.validate_imported_project("/nonexistent")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_empty_dir(self, tmp_dir):
        empty = os.path.join(tmp_dir, "empty")
        os.makedirs(empty)
        imp = self.Importer(projects_dir=tmp_dir)
        result = imp.validate_imported_project(empty)
        assert result["valid"] is False

    def test_resolve_github_url(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        url = imp._resolve_github_url("github:owner/repo")
        assert url == "https://github.com/owner/repo.git"

    def test_resolve_github_url_from_full(self, tmp_dir):
        imp = self.Importer(projects_dir=tmp_dir)
        url = imp._resolve_github_url("https://github.com/owner/repo")
        assert url == "https://github.com/owner/repo.git"

    def test_count_files(self, tmp_dir, sample_python_project):
        imp = self.Importer(projects_dir=tmp_dir)
        count = imp._count_files(Path(sample_python_project))
        assert count > 0


# ===========================================================================
# P8 — Project Understanding
# ===========================================================================

class TestProjectUnderstanding:
    def test_analyze_python_project(self, sample_python_project):
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding
        pu = ProjectUnderstanding()
        snap = pu.analyze(sample_python_project)
        assert snap.language == "python"
        assert "requirements.txt" in snap.manifest_files
        assert snap.project_type != "unknown"

    def test_analyze_js_project(self, sample_js_project):
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding
        pu = ProjectUnderstanding()
        snap = pu.analyze(sample_js_project)
        assert snap.language == "javascript"
        assert "package.json" in snap.manifest_files

    def test_analyze_nonexistent(self):
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding
        pu = ProjectUnderstanding()
        snap = pu.analyze("/nonexistent/path")
        assert snap.language == ""
        assert snap.root_files == []

    def test_get_summary(self, sample_python_project):
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding
        pu = ProjectUnderstanding()
        snap = pu.analyze(sample_python_project)
        summary = pu.get_summary(snap)
        assert "language" in summary
        assert "frameworks" in summary
        assert "build_system" in summary
        assert "entry_points" in summary
        assert summary["language"] == "python"

    def test_detect_root_files(self, sample_python_project):
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding
        pu = ProjectUnderstanding()
        snap = pu.analyze(sample_python_project)
        assert "main.py" in snap.root_files
        assert "requirements.txt" in snap.root_files

    def test_detect_root_dirs(self, sample_python_project):
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding
        pu = ProjectUnderstanding()
        snap = pu.analyze(sample_python_project)
        assert "src" in snap.root_directories
        assert "tests" in snap.root_directories

    def test_detect_test_system(self, sample_python_project):
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding
        pu = ProjectUnderstanding()
        snap = pu.analyze(sample_python_project)
        assert "tests" in snap.test_directories

    def test_detect_entry_points(self, sample_python_project):
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding
        pu = ProjectUnderstanding()
        snap = pu.analyze(sample_python_project)
        assert "main.py" in snap.entry_points


# ===========================================================================
# P16 — Project Sandbox
# ===========================================================================

class TestProjectSandbox:
    def test_init_creates_dir(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        path = os.path.join(tmp_dir, "new_project")
        ProjectSandbox(path)
        assert os.path.isdir(path)

    def test_protected_zones_default(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        zones = sb.get_protected_zones()
        assert ".git" in zones
        assert "node_modules" in zones
        assert "venv" in zones

    def test_is_file_protected_git(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        assert sb.is_file_protected(".git/config") is True

    def test_is_file_protected_node_modules(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        assert sb.is_file_protected("node_modules/foo/index.js") is True

    def test_is_file_protected_normal(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        assert sb.is_file_protected("src/main.py") is False

    def test_safe_write_allowed(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        result = sb.safe_write("src/main.py", "print('hello')")
        assert result["success"] is True
        assert result["error"] is None
        assert os.path.isfile(os.path.join(tmp_dir, "src/main.py"))

    def test_safe_write_protected(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        result = sb.safe_write(".git/config", "malicious")
        assert result["success"] is False
        assert "protected zone" in result["error"]

    def test_safe_write_creates_dirs(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        result = sb.safe_write("deep/nested/path/file.py", "x = 1")
        assert result["success"] is True

    def test_checkpoint_and_rollback(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        # Write initial file
        sb.safe_write("file.txt", "version1")
        # Create checkpoint
        hash1 = sb.create_checkpoint("v1")
        assert hash1 and len(hash1) == 40

        # Modify file
        sb.safe_write("file.txt", "version2")
        assert "version2" in Path(tmp_dir, "file.txt").read_text()

        # Rollback
        ok = sb.rollback(hash1)
        assert ok is True
        assert "version1" in Path(tmp_dir, "file.txt").read_text()

    def test_create_temp_branch(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        sb.safe_write("init.txt", "init")
        sb.create_checkpoint("init")
        branch = sb.create_temp_branch("test")
        assert branch.startswith("test-")

    def test_list_checkpoints(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        sb.safe_write("a.txt", "a")
        sb.create_checkpoint("first")
        sb.safe_write("b.txt", "b")
        sb.create_checkpoint("second")
        checkpoints = sb.list_checkpoints()
        assert len(checkpoints) >= 2

    def test_get_diff_since_checkpoint(self, tmp_dir):
        from core.project_manager.workspace.project_sandbox import ProjectSandbox
        sb = ProjectSandbox(tmp_dir)
        sb.safe_write("file.txt", "original")
        h = sb.create_checkpoint("orig")
        sb.safe_write("file.txt", "modified")
        diff = sb.get_diff_since_checkpoint(h)
        assert "modified" in diff or "original" in diff


# ===========================================================================
# P3 — Repo Repair
# ===========================================================================

class TestRepoRepair:
    def test_init_valid(self, sample_python_project):
        from core.project_manager.workspace.repo_repair import RepoRepair
        rr = RepoRepair(sample_python_project)
        assert rr.project_path.exists()

    def test_init_invalid(self, tmp_dir):
        from core.project_manager.workspace.repo_repair import RepoRepair
        with pytest.raises(ValueError):
            RepoRepair("/nonexistent/path/xyz")

    def test_find_broken_imports_none(self, sample_python_project):
        from core.project_manager.workspace.repo_repair import RepoRepair
        rr = RepoRepair(sample_python_project)
        broken = rr.find_broken_imports()
        # os, sys, src.utils should all resolve
        assert isinstance(broken, list)

    def test_find_broken_imports_with_broken(self, tmp_dir):
        from core.project_manager.workspace.repo_repair import RepoRepair
        root = Path(tmp_dir) / "broken_proj"
        root.mkdir()
        (root / "app.py").write_text("import nonexistent_module_xyz\n")
        rr = RepoRepair(str(root))
        broken = rr.find_broken_imports()
        assert len(broken) > 0
        assert any("nonexistent_module_xyz" in b.get("import_name", "") for b in broken)

    def test_find_circular_dependencies_none(self, sample_python_project):
        from core.project_manager.workspace.repo_repair import RepoRepair
        rr = RepoRepair(sample_python_project)
        cycles = rr.find_circular_dependencies()
        assert isinstance(cycles, list)

    def test_find_circular_dependencies_with_cycle(self, tmp_dir):
        from core.project_manager.workspace.repo_repair import RepoRepair
        root = Path(tmp_dir) / "cycle_proj"
        root.mkdir()
        (root / "a.py").write_text("from b import foo\n")
        (root / "b.py").write_text("from a import bar\n")
        rr = RepoRepair(str(root))
        cycles = rr.find_circular_dependencies()
        assert len(cycles) > 0

    def test_find_deprecated_patterns_none(self, sample_python_project):
        from core.project_manager.workspace.repo_repair import RepoRepair
        rr = RepoRepair(sample_python_project)
        deprecated = rr.find_deprecated_patterns()
        assert isinstance(deprecated, list)

    def test_find_deprecated_patterns_found(self, tmp_dir):
        from core.project_manager.workspace.repo_repair import RepoRepair
        root = Path(tmp_dir) / "old_proj"
        root.mkdir()
        (root / "legacy.py").write_text("x = basestring('test')\ny = xrange(10)\n")
        rr = RepoRepair(str(root))
        deprecated = rr.find_deprecated_patterns()
        assert len(deprecated) > 0

    def test_analyze_repair_goal_imports(self, sample_python_project):
        from core.project_manager.workspace.repo_repair import RepoRepair
        rr = RepoRepair(sample_python_project)
        plan = rr.analyze_repair_goal("fix broken imports")
        assert "goal" in plan
        assert "steps" in plan
        assert "estimated_risk" in plan
        assert "requires_approval" in plan

    def test_analyze_repair_goal_dependencies(self, sample_python_project):
        from core.project_manager.workspace.repo_repair import RepoRepair
        rr = RepoRepair(sample_python_project)
        plan = rr.analyze_repair_goal("fix missing dependencies")
        assert plan["goal"] == "fix missing dependencies"
        assert isinstance(plan["steps"], list)

    def test_analyze_repair_goal_circular(self, tmp_dir):
        from core.project_manager.workspace.repo_repair import RepoRepair
        root = Path(tmp_dir) / "cycle_proj2"
        root.mkdir()
        (root / "a.py").write_text("from b import foo\n")
        (root / "b.py").write_text("from a import bar\n")
        rr = RepoRepair(str(root))
        plan = rr.analyze_repair_goal("fix circular dependencies")
        assert plan["estimated_risk"] == "high"
        assert plan["requires_approval"] is True

    def test_analyze_repair_goal_empty(self, sample_python_project):
        from core.project_manager.workspace.repo_repair import RepoRepair
        rr = RepoRepair(sample_python_project)
        plan = rr.analyze_repair_goal("почини зависимости")
        assert isinstance(plan["steps"], list)

    def test_python_files_excludes_venv(self, tmp_dir):
        from core.project_manager.workspace.repo_repair import RepoRepair
        root = Path(tmp_dir) / "proj_with_venv"
        root.mkdir()
        (root / "app.py").write_text("x = 1\n")
        venv = root / "venv"
        venv.mkdir()
        (venv / "fake.py").write_text("should be ignored\n")
        rr = RepoRepair(str(root))
        files = rr._python_files()
        basenames = [f.name for f in files]
        assert "app.py" in basenames
        assert "fake.py" not in basenames


# ===========================================================================
# P11 — Session Memory
# ===========================================================================

class TestSessionMemory:
    def test_init_creates_dir(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        SessionMemory(tmp_dir)
        assert os.path.isdir(os.path.join(tmp_dir, ".ai-team"))
        assert os.path.isfile(os.path.join(tmp_dir, ".ai-team", "session.json"))

    def test_start_session(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        session = sm.start_session("testuser")
        assert session["user"] == "testuser"
        assert session["status"] == "active"
        assert "id" in session

    def test_get_session(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.start_session("testuser")
        session = sm.get_session()
        assert session is not None
        assert session["user"] == "testuser"

    def test_get_session_none(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        assert sm.get_session() is None

    def test_end_session(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.start_session("testuser")
        ended = sm.end_session()
        assert ended["status"] == "ended"
        assert ended["end_time"] is not None

    def test_add_and_get_tasks(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.add_task({"id": "T1", "title": "Task 1", "status": "pending"})
        sm.add_task({"id": "T2", "title": "Task 2", "status": "running"})
        tasks = sm.get_tasks()
        assert len(tasks) == 2

    def test_get_tasks_by_status(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.add_task({"id": "T1", "title": "Task 1", "status": "pending"})
        sm.add_task({"id": "T2", "title": "Task 2", "status": "running"})
        pending = sm.get_tasks(status="pending")
        assert len(pending) == 1
        assert pending[0]["id"] == "T1"

    def test_update_task(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.add_task({"id": "T1", "title": "Task 1", "status": "pending"})
        updated = sm.update_task("T1", status="running")
        assert updated["status"] == "running"

    def test_update_task_not_found(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        result = sm.update_task("nonexistent", status="done")
        assert result is None

    def test_add_and_get_workflows(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.add_pending_workflow({"id": "W1", "name": "deploy", "status": "pending"})
        pending = sm.get_pending_workflows()
        assert len(pending) == 1

    def test_add_and_resolve_approvals(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.add_approval({"id": "A1", "action": "delete", "status": "pending"})
        pending = sm.get_pending_approvals()
        assert len(pending) == 1

        resolved = sm.resolve_approval("A1", "approved", "looks good")
        assert resolved["status"] == "approved"

    def test_record_and_get_changes(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.record_change("src/main.py", "modified", task_id="T1")
        sm.record_change("src/utils.py", "added", task_id="T1")
        changes = sm.get_recent_changes()
        assert len(changes) == 2

    def test_get_recent_changes_limit(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        for i in range(30):
            sm.record_change(f"file{i}.py", "modified")
        changes = sm.get_recent_changes(limit=10)
        assert len(changes) == 10

    def test_branch_state(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.set_branch_state("main", "abc123")
        state = sm.get_branch_state()
        assert state["branch"] == "main"
        assert state["commit_hash"] == "abc123"

    def test_get_summary(self, tmp_dir):
        from core.project_manager.workspace.session_memory import SessionMemory
        sm = SessionMemory(tmp_dir)
        sm.start_session("testuser")
        sm.add_task({"id": "T1", "title": "Task 1", "status": "pending"})
        sm.add_pending_workflow({"id": "W1", "name": "deploy", "status": "pending"})
        sm.add_approval({"id": "A1", "action": "delete", "status": "pending"})
        sm.record_change("src/main.py", "modified")
        summary = sm.get_summary()
        assert summary["session"] is not None
        assert len(summary["open_tasks"]) == 1
        assert len(summary["pending_workflows"]) == 1
        assert len(summary["pending_approvals"]) == 1
        assert len(summary["recent_changes"]) == 1


# ===========================================================================
# P9 — Task Traceability
# ===========================================================================

class TestTaskTraceability:
    def test_record_task_start(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        entry = tt.record_task_start("T-001", "Add login", "coder")
        assert entry["event"] == "task_start"
        assert entry["task_id"] == "T-001"
        assert entry["status"] == "in_progress"

    def test_record_file_change(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        entry = tt.record_file_change("T-001", "src/auth.py", "modified", ["login", "validate"])
        assert entry["event"] == "file_change"
        assert entry["change_type"] == "modified"
        assert "login" in entry["symbols_affected"]

    def test_record_file_change_invalid_type(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        with pytest.raises(ValueError):
            tt.record_file_change("T-001", "file.py", "invalid_type")

    def test_record_task_complete(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        entry = tt.record_task_complete("T-001", "completed")
        assert entry["event"] == "task_complete"
        assert entry["status"] == "completed"

    def test_get_task_trace(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        tt.record_task_start("T-001", "Add login", "coder")
        tt.record_file_change("T-001", "src/auth.py", "modified", ["login"])
        tt.record_task_complete("T-001", "completed")
        trace = tt.get_task_trace("T-001")
        assert trace["task_id"] == "T-001"
        assert trace["description"] == "Add login"
        assert trace["agent"] == "coder"
        assert trace["status"] == "completed"
        assert len(trace["file_changes"]) == 1
        assert "login" in trace["all_symbols"]

    def test_get_task_trace_unknown(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        trace = tt.get_task_trace("NONEXISTENT")
        assert trace["status"] == "unknown"

    def test_get_file_history(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        tt.record_task_start("T-001", "Add login", "coder")
        tt.record_file_change("T-001", "src/auth.py", "modified", ["login"])
        tt.record_task_start("T-002", "Add logout", "reviewer")
        tt.record_file_change("T-002", "src/auth.py", "modified", ["logout"])
        history = tt.get_file_history("src/auth.py")
        assert len(history) == 2

    def test_get_symbol_history(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        tt.record_task_start("T-001", "Add login", "coder")
        tt.record_file_change("T-001", "src/auth.py", "modified", ["login", "validate"])
        history = tt.get_symbol_history("login")
        assert len(history) == 1
        assert history[0]["task_id"] == "T-001"

    def test_find_related_tasks(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        tt.record_task_start("T-001", "Add login", "coder")
        tt.record_file_change("T-001", "src/auth.py", "modified", ["login"])
        tt.record_task_start("T-002", "Add logout", "reviewer")
        tt.record_file_change("T-002", "src/auth.py", "modified", ["logout"])
        related = tt.find_related_tasks("T-001")
        assert len(related) == 1
        assert related[0]["task_id"] == "T-002"
        assert "src/auth.py" in related[0]["shared_files"]

    def test_generate_trace_report(self, tmp_dir):
        from core.project_manager.workspace.task_traceability import TaskTraceability
        tt = TaskTraceability(tmp_dir)
        tt.record_task_start("T-001", "Add login", "coder")
        tt.record_file_change("T-001", "src/auth.py", "modified", ["login"])
        tt.record_task_complete("T-001", "completed")
        report = tt.generate_trace_report("T-001")
        assert "TASK TRACEABILITY REPORT" in report
        assert "T-001" in report
        assert "Add login" in report


# ===========================================================================
# P10 — Patch Review
# ===========================================================================

class TestPatchReview:
    SAMPLE_DIFF = (
        "diff --git a/src/main.py b/src/main.py\n"
        "--- a/src/main.py\n"
        "+++ b/src/main.py\n"
        "@@ -1,3 +1,5 @@\n"
        " import os\n"
        " import sys\n"
        "+import json\n"
        "+import re\n"
        " def main():\n"
        "-    print('hello')\n"
        "+    print('world')\n"
    )

    def test_generate_review(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        pr = PatchReview()
        review = pr.generate_review(self.SAMPLE_DIFF, tmp_dir)
        assert "files_changed" in review
        assert "risk_level" in review
        assert "risk_score" in review
        assert "confidence_score" in review
        assert "rollback_plan" in review
        assert "summary" in review
        assert len(review["files_changed"]) > 0

    def test_risk_level_low(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        small_diff = (
            "diff --git a/small.py b/small.py\n"
            "--- a/small.py\n"
            "+++ b/small.py\n"
            "@@ -1,2 +1,3 @@\n"
            " x = 1\n"
            "+y = 2\n"
        )
        pr = PatchReview()
        review = pr.generate_review(small_diff, tmp_dir)
        assert review["risk_level"] == "low"

    def test_risk_level_high_entry_point(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        diff = (
            "diff --git a/main.py b/main.py\n"
            "--- a/main.py\n"
            "+++ b/main.py\n"
            "@@ -1,2 +1,3 @@\n"
            " x = 1\n"
            "+y = 2\n"
        )
        pr = PatchReview()
        review = pr.generate_review(diff, tmp_dir)
        assert review["risk_level"] == "high"

    def test_risk_level_high_config(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        diff = (
            "diff --git a/config.py b/config.py\n"
            "--- a/config.py\n"
            "+++ b/config.py\n"
            "@@ -1,2 +1,3 @@\n"
            " x = 1\n"
            "+y = 2\n"
        )
        pr = PatchReview()
        review = pr.generate_review(diff, tmp_dir)
        assert review["risk_level"] == "high"

    def test_risk_score_range(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        pr = PatchReview()
        review = pr.generate_review(self.SAMPLE_DIFF, tmp_dir)
        assert 0.0 <= review["risk_score"] <= 1.0

    def test_confidence_score_range(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        pr = PatchReview()
        review = pr.generate_review(self.SAMPLE_DIFF, tmp_dir)
        assert 0.0 <= review["confidence_score"] <= 1.0

    def test_affected_modules(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        pr = PatchReview()
        review = pr.generate_review(self.SAMPLE_DIFF, tmp_dir)
        assert isinstance(review["affected_modules"], list)
        assert len(review["affected_modules"]) > 0

    def test_validation_impact(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        pr = PatchReview()
        review = pr.generate_review(self.SAMPLE_DIFF, tmp_dir)
        assert isinstance(review["validation_impact"], list)

    def test_rollback_plan(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        pr = PatchReview()
        review = pr.generate_review(self.SAMPLE_DIFF, tmp_dir)
        rb = review["rollback_plan"]
        assert "command" in rb
        assert "git reset" in rb["command"]

    def test_format_review_for_display(self, tmp_dir):
        from core.project_manager.workspace.patch_review import PatchReview
        pr = PatchReview()
        review = pr.generate_review(self.SAMPLE_DIFF, tmp_dir)
        display = pr.format_review_for_display(review)
        assert "PATCH REVIEW REPORT" in display
        assert "Risk Level" in display
        assert "Rollback Plan" in display

    def test_compare_patches(self):
        from core.project_manager.workspace.patch_review import PatchReview
        old_diff = (
            "diff --git a/file1.py b/file1.py\n"
            "--- a/file1.py\n"
            "+++ b/file1.py\n"
            "@@ -1 +1,2 @@\n"
            " x = 1\n"
            "+y = 2\n"
        )
        new_diff = (
            "diff --git a/file1.py b/file1.py\n"
            "diff --git a/file2.py b/file2.py\n"
            "--- a/file1.py\n"
            "+++ b/file1.py\n"
            "@@ -1 +1,3 @@\n"
            " x = 1\n"
            " y = 2\n"
            "+z = 3\n"
            "--- a/file2.py\n"
            "+++ b/file2.py\n"
            "@@ -0,0 +1 @@\n"
            "+a = 1\n"
        )
        pr = PatchReview()
        comparison = pr.compare_patches(old_diff, new_diff)
        assert "files_only_in_new" in comparison
        assert "files_only_in_old" in comparison
        assert "summary" in comparison

    def test_parse_diff_files(self):
        from core.project_manager.workspace.patch_review import _parse_diff_files
        diff = (
            "diff --git a/src/a.py b/src/a.py\n"
            "diff --git a/src/b.py b/src/b.py\n"
        )
        files = _parse_diff_files(diff)
        assert "src/a.py" in files
        assert "src/b.py" in files

    def test_count_diff_lines(self):
        from core.project_manager.workspace.patch_review import _count_diff_lines
        diff = (
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,2 +1,3 @@\n"
            " kept\n"
            "-removed\n"
            "+added1\n"
            "+added2\n"
        )
        added, deleted = _count_diff_lines(diff)
        assert added == 2
        assert deleted == 1

    def test_is_entry_point(self):
        from core.project_manager.workspace.patch_review import _is_entry_point
        assert _is_entry_point("main.py") is True
        assert _is_entry_point("app.js") is True
        assert _is_entry_point("src/utils.py") is False

    def test_is_config_file(self):
        from core.project_manager.workspace.patch_review import _is_config_file
        assert _is_config_file("config.py") is True
        assert _is_config_file(".env") is True
        assert _is_config_file("src/main.py") is False

    def test_is_test_file(self):
        from core.project_manager.workspace.patch_review import _is_test_file
        assert _is_test_file("tests/test_foo.py") is True
        assert _is_test_file("src/main.py") is False

    def test_extract_modules(self):
        from core.project_manager.workspace.patch_review import _extract_modules
        modules = _extract_modules(["src/a.py", "src/b.py", "tests/test_a.py"])
        assert "src" in modules
        assert "tests" in modules

    def test_compute_risk_score(self):
        from core.project_manager.workspace.patch_review import _compute_risk_score
        score = _compute_risk_score(1, 10, 5, False, False, False)
        assert 0.0 <= score <= 1.0

    def test_compute_confidence_score(self):
        from core.project_manager.workspace.patch_review import _compute_confidence_score
        score = _compute_confidence_score(1, 10, 5, False, False)
        assert 0.0 <= score <= 1.0


# ===========================================================================
# P13/P17/P18 — User Modes
# ===========================================================================

class TestUserModes:
    def setup_method(self):
        from core.project_manager.workspace.user_modes import (
            UserModeManager, AutonomyLimits,
            BEGINNER_MODE, ADVANCED_MODE, MODE_CONFIGS,
            GLOBAL_AUTONOMY_LIMITS,
        )
        self.UserModeManager = UserModeManager
        self.AutonomyLimits = AutonomyLimits
        self.BEGINNER_MODE = BEGINNER_MODE
        self.ADVANCED_MODE = ADVANCED_MODE
        self.MODE_CONFIGS = MODE_CONFIGS
        self.GLOBAL_AUTONOMY_LIMITS = GLOBAL_AUTONOMY_LIMITS

    def test_default_mode_is_beginner(self):
        mgr = self.UserModeManager()
        assert mgr.get_mode() == self.BEGINNER_MODE

    def test_set_mode_advanced(self):
        mgr = self.UserModeManager()
        mgr.set_mode("advanced")
        assert mgr.get_mode() == self.ADVANCED_MODE

    def test_set_mode_invalid(self):
        mgr = self.UserModeManager()
        with pytest.raises(ValueError):
            mgr.set_mode("superadmin")

    def test_beginner_config(self):
        cfg = self.MODE_CONFIGS[self.BEGINNER_MODE]
        assert cfg.max_autonomous_files == 1
        assert cfg.explain_before_action is True
        assert cfg.guided_workflows_only is True
        assert cfg.batch_approvals is False
        assert cfg.risk_threshold == "low"

    def test_advanced_config(self):
        cfg = self.MODE_CONFIGS[self.ADVANCED_MODE]
        assert cfg.max_autonomous_files == 10
        assert cfg.explain_before_action is False
        assert cfg.guided_workflows_only is False
        assert cfg.batch_approvals is True
        assert cfg.risk_threshold == "medium"

    def test_get_mode_config(self):
        mgr = self.UserModeManager()
        cfg = mgr.get_mode_config()
        assert "max_autonomous_files" in cfg
        assert "risk_threshold" in cfg

    def test_beginner_allows_low_risk_create(self):
        mgr = self.UserModeManager("beginner")
        result = mgr.is_action_allowed("create", "low")
        assert result["allowed"] is True
        assert result["requires_approval"] is False

    def test_beginner_blocks_high_risk(self):
        mgr = self.UserModeManager("beginner")
        result = mgr.is_action_allowed("create", "high")
        assert result["allowed"] is False
        assert result["requires_approval"] is True

    def test_beginner_requires_approval_for_delete(self):
        mgr = self.UserModeManager("beginner")
        result = mgr.is_action_allowed("delete", "low")
        assert result["allowed"] is False
        assert result["requires_approval"] is True

    def test_advanced_allows_medium_risk(self):
        mgr = self.UserModeManager("advanced")
        result = mgr.is_action_allowed("create", "medium")
        assert result["allowed"] is True

    def test_advanced_blocks_critical_risk(self):
        mgr = self.UserModeManager("advanced")
        result = mgr.is_action_allowed("create", "critical")
        assert result["allowed"] is False

    def test_hard_limit_architecture_change(self):
        mgr = self.UserModeManager("advanced")
        result = mgr.is_action_allowed("architecture_change", "low")
        assert result["allowed"] is False
        assert "hard autonomy limit" in result["reason"]

    def test_hard_limit_governance_change(self):
        mgr = self.UserModeManager("advanced")
        result = mgr.is_action_allowed("governance_change", "low")
        assert result["allowed"] is False

    def test_hard_limit_modify_pm_core(self):
        mgr = self.UserModeManager("advanced")
        result = mgr.is_action_allowed("modify_pm_core", "low")
        assert result["allowed"] is False

    def test_hard_limit_bypass_approval(self):
        mgr = self.UserModeManager("advanced")
        result = mgr.is_action_allowed("bypass_approval", "low")
        assert result["allowed"] is False

    def test_autonomy_limits_to_dict(self):
        limits = self.AutonomyLimits()
        d = limits.to_dict()
        assert d["can_silently_rewrite_architecture"] is False
        assert d["can_self_modify_governance"] is False
        assert d["can_bypass_approvals"] is False

    def test_get_autonomy_limits(self):
        mgr = self.UserModeManager()
        limits = mgr.get_autonomy_limits()
        assert isinstance(limits, dict)
        assert len(limits) == 7

    def test_mode_config_to_dict(self):
        cfg = self.MODE_CONFIGS[self.BEGINNER_MODE]
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["max_autonomous_files"] == 1

    def test_unknown_risk_level_blocked(self):
        mgr = self.UserModeManager("beginner")
        result = mgr.is_action_allowed("create", "unknown_risk")
        assert result["allowed"] is False


# ===========================================================================
# P2 — Project Health
# ===========================================================================

class TestProjectHealth:
    def _make_mock_pm(self, files=None, deps=None, stats=None):
        pm = MagicMock()
        pm._files = files or {}
        pm.dependencies = deps or {}
        pm.get_stats.return_value = stats or {"total_files": 0, "total_dependencies": 0}
        pm._git = None
        pm._query_history = {}
        return pm

    def test_build_empty_project(self):
        from core.project_manager.workspace.project_health import ProjectHealthBuilder
        pm = self._make_mock_pm()
        builder = ProjectHealthBuilder(pm)
        dash = builder.build()
        assert dash.total_files == 0
        assert dash.total_modules == 0
        assert dash.overall_score == 1.0
        assert dash.overall_status == "healthy"

    def test_build_with_files(self):
        from core.project_manager.workspace.project_health import ProjectHealthBuilder
        from core.project_manager.models import FileEntry
        files = {
            "src/a.py": MagicMock(symbols=["f1", "f2", "f3"]),
            "src/b.py": MagicMock(symbols=["f1"] * 60),  # high complexity
        }
        pm = self._make_mock_pm(files=files, stats={"total_files": 2})
        builder = ProjectHealthBuilder(pm)
        dash = builder.build()
        assert dash.total_modules == 2
        assert dash.total_files == 2

    def test_build_dict(self):
        from core.project_manager.workspace.project_health import ProjectHealthBuilder
        pm = self._make_mock_pm()
        builder = ProjectHealthBuilder(pm)
        d = builder.build_dict()
        assert "overall_score" in d
        assert "overall_status" in d
        assert "recommendations" in d

    def test_score_to_status(self):
        from core.project_manager.workspace.project_health import ProjectHealthBuilder
        assert ProjectHealthBuilder._score_to_status(0.9) == "healthy"
        assert ProjectHealthBuilder._score_to_status(0.7) == "warning"
        assert ProjectHealthBuilder._score_to_status(0.5) == "degraded"
        assert ProjectHealthBuilder._score_to_status(0.2) == "critical"

    def test_recommendations_empty(self):
        from core.project_manager.workspace.project_health import (
            ProjectHealthBuilder, ProjectHealthDashboard,
        )
        dash = ProjectHealthDashboard()
        recs = ProjectHealthBuilder._generate_recommendations(dash)
        assert any("healthy" in r for r in recs)

    def test_recommendations_high_complexity(self):
        from core.project_manager.workspace.project_health import (
            ProjectHealthBuilder, ProjectHealthDashboard,
        )
        dash = ProjectHealthDashboard()
        dash.complexity_score = 0.8
        recs = ProjectHealthBuilder._generate_recommendations(dash)
        assert any("complexity" in r.lower() for r in recs)

    def test_circular_dependency_risk(self):
        from core.project_manager.workspace.project_health import ProjectHealthBuilder
        pm = self._make_mock_pm(
            files={"a.py": MagicMock(symbols=[]), "b.py": MagicMock(symbols=[])},
            deps={"a.py": ["b.py"], "b.py": ["a.py"]},
            stats={"total_files": 2},
        )
        builder = ProjectHealthBuilder(pm)
        dash = builder.build()
        assert len(dash.dependency_risks) > 0
        assert dash.dependency_risks[0].risk_type == "circular"

    def test_deep_dependency_chain(self):
        from core.project_manager.workspace.project_health import ProjectHealthBuilder
        deps = {
            "a.py": ["b.py"],
            "b.py": ["c.py"],
            "c.py": ["d.py"],
            "d.py": ["e.py"],
            "e.py": ["f.py"],
            "f.py": ["g.py"],
        }
        pm = self._make_mock_pm(
            files={k: MagicMock(symbols=[]) for k in deps},
            deps=deps,
            stats={"total_files": len(deps)},
        )
        builder = ProjectHealthBuilder(pm)
        dash = builder.build()
        deep = [r for r in dash.dependency_risks if r.risk_type == "deep_chain"]
        assert len(deep) > 0

    def test_overall_score_range(self):
        from core.project_manager.workspace.project_health import ProjectHealthBuilder
        pm = self._make_mock_pm(
            files={"a.py": MagicMock(symbols=[])},
            stats={"total_files": 1},
        )
        builder = ProjectHealthBuilder(pm)
        dash = builder.build()
        assert 0.0 <= dash.overall_score <= 1.0
