"""
Tests for PHASE 7 — Real-World Execution & Human Workflow Integration.
"""

import time
from pathlib import Path

# ── P2: Git Workflow ──

def test_git_workflow_branch_classification():
    from core.project_manager.runtime.git_workflow import GitWorkflowIntegration, BranchType
    gw = GitWorkflowIntegration(Path("."))
    assert gw._classify_branch("main") == BranchType.MAIN
    assert gw._classify_branch("feature/new-ui") == BranchType.FEATURE
    assert gw._classify_branch("bugfix/crash") == BranchType.BUGFIX
    assert gw._classify_branch("refactor/core") == BranchType.REFACTOR
    assert gw._classify_branch("hotfix/security") == BranchType.HOTFIX
    assert gw._classify_branch("unknown") == BranchType.UNKNOWN

def test_git_workflow_commit_parsing():
    from core.project_manager.runtime.git_workflow import GitWorkflowIntegration, CommitType
    gw = GitWorkflowIntegration(Path("."))
    commit = gw.parse_commit("feat(auth): add login flow")
    assert commit.commit_type == CommitType.FEAT
    assert commit.scope == "auth"
    assert commit.subject == "add login flow"

    commit2 = gw.parse_commit("fix: resolve crash on startup")
    assert commit2.commit_type == CommitType.FIX

    commit3 = gw.parse_commit("refactor(core)!: restructure module")
    assert commit3.commit_type == CommitType.REFACTOR
    assert commit3.is_breaking is True

def test_git_workflow_commit_grouping():
    from core.project_manager.runtime.git_workflow import GitWorkflowIntegration, CommitType
    gw = GitWorkflowIntegration(Path("."))
    commits = [
        gw.parse_commit("feat: add feature A"),
        gw.parse_commit("feat: add feature B"),
        gw.parse_commit("fix: fix bug"),
        gw.parse_commit("docs: update readme"),
    ]
    groups = gw.group_commits_by_type(commits)
    assert len(groups["feat"]) == 2
    assert len(groups["fix"]) == 1

def test_git_workflow_scope_detection():
    from core.project_manager.runtime.git_workflow import GitWorkflowIntegration
    gw = GitWorkflowIntegration(Path("."))
    scope = gw._detect_scope(["core/main.py", "core/utils.py", "tests/test.py"])
    assert scope == "core"

def test_git_workflow_commit_message_generation():
    from core.project_manager.runtime.git_workflow import GitWorkflowIntegration
    gw = GitWorkflowIntegration(Path("."))
    msg = gw.generate_commit_message(
        ["core/main.py", "core/utils.py"],
        type("obj", (), {"files_changed": 2, "has_tests": False, "has_config": False})()
    )
    assert "feat" in msg or "chore" in msg


# ── P5: Failure Analysis ──

def test_failure_analysis_record():
    from core.project_manager.runtime.failure_analysis import (
        FailureAnalysisSystem, FailureCategory, FailureSeverity
    )
    fas = FailureAnalysisSystem()
    record = fas.record_failure(
        FailureCategory.WORKFLOW, FailureSeverity.HIGH,
        "task-1", "feature", "execution", "Step failed"
    )
    assert record.id != ""
    assert record.category == FailureCategory.WORKFLOW

def test_failure_analysis_patterns():
    from core.project_manager.runtime.failure_analysis import (
        FailureAnalysisSystem, FailureCategory, FailureSeverity
    )
    fas = FailureAnalysisSystem()
    for i in range(5):
        fas.record_failure(
            FailureCategory.VALIDATION, FailureSeverity.MEDIUM,
            f"task-{i}", "feature", "validation", "Import error"
        )
    patterns = fas.get_patterns(min_frequency=2)
    assert len(patterns) >= 1

def test_failure_analysis_taxonomy():
    from core.project_manager.runtime.failure_analysis import (
        FailureAnalysisSystem, FailureCategory, FailureSeverity
    )
    fas = FailureAnalysisSystem()
    fas.record_failure(FailureCategory.WORKFLOW, FailureSeverity.HIGH, "t1", "f", "e", "msg")
    fas.record_failure(FailureCategory.VALIDATION, FailureSeverity.LOW, "t2", "f", "v", "msg")
    taxonomy = fas.get_taxonomy()
    assert taxonomy['total_failures'] == 2


# ── P6: Engineering Memory ──

def test_engineering_memory_add_recall():
    from core.project_manager.runtime.engineering_memory import (
        EngineeringMemorySystem, MemoryType
    )
    ems = EngineeringMemorySystem()
    entry = ems.add_memory(
        MemoryType.ARCH_DECISION,
        "Use SQLite for storage",
        "Chose SQLite for simplicity and zero-config",
        tags=["storage", "database"],
        module="core/project_manager/storage"
    )
    assert entry.id != ""

    recalled = ems.recall(entry.id)
    assert recalled is not None
    assert recalled.title == "Use SQLite for storage"

def test_engineering_memory_search():
    from core.project_manager.runtime.engineering_memory import (
        EngineeringMemorySystem, MemoryType
    )
    ems = EngineeringMemorySystem()
    ems.add_memory(MemoryType.UNSTABLE_MODULE, "Auth module", "Frequently breaks", module="auth")
    ems.add_memory(MemoryType.RISKY_WORKFLOW, "DB migration", "Risky workflow", module="db")

    results = ems.search(query="breaks")
    assert len(results) >= 1

    results = ems.search(module="auth")
    assert len(results) >= 1

def test_engineering_memory_unstable_modules():
    from core.project_manager.runtime.engineering_memory import (
        EngineeringMemorySystem, MemoryType
    )
    ems = EngineeringMemorySystem()
    ems.add_memory(
        MemoryType.UNSTABLE_MODULE, "Payment module",
        "Breaks on edge cases",
        context={"module": "payment", "incident_count": 5}
    )
    unstable = ems.get_unstable_modules()
    assert len(unstable) >= 1
    assert unstable[0]['module'] == 'payment'


# ── P9: Engineering Session ──

def test_session_create():
    from core.project_manager.session import EngineeringSessionSystem, SessionState
    ess = EngineeringSessionSystem()
    session = ess.create_session("Test session", project_path="/tmp")
    assert session.id != ""
    assert session.state == SessionState.ACTIVE

def test_session_lifecycle():
    from core.project_manager.session import EngineeringSessionSystem, SessionState
    ess = EngineeringSessionSystem()
    s = ess.create_session("Test")
    assert ess.pause_session(s.id) is True
    s = ess.get_session(s.id)
    assert s.state == SessionState.PAUSED
    assert ess.resume_session(s.id) is True
    s = ess.get_session(s.id)
    assert s.state == SessionState.ACTIVE
    assert ess.complete_session(s.id) is True
    s = ess.get_session(s.id)
    assert s.state == SessionState.COMPLETED

def test_session_checkpoints():
    from core.project_manager.session import EngineeringSessionSystem
    ess = EngineeringSessionSystem()
    s = ess.create_session("Test")
    cp = ess.add_checkpoint(s.id, "Before refactor", git_ref="abc123")
    assert cp is not None
    latest = ess.get_latest_checkpoint(s.id)
    assert latest is not None
    assert latest.description == "Before refactor"

def test_session_approvals():
    from core.project_manager.session import EngineeringSessionSystem
    ess = EngineeringSessionSystem()
    s = ess.create_session("Test")
    ess.add_pending_approval(s.id, {"id": "apr-1", "type": "patch"})
    s = ess.get_session(s.id)
    assert len(s.pending_approvals) == 1
    assert ess.resolve_approval(s.id, "apr-1", approved=True, resolved_by="user") is True
    s = ess.get_session(s.id)
    assert len(s.pending_approvals) == 0
    assert len(s.approved_actions) == 1


# ── P10: Execution Explainability ──

def test_explainability_workflow_choice():
    from core.project_manager.runtime.explainability import (
        ExecutionExplainability, ExplainabilityTopic
    )
    exp = ExecutionExplainability()
    explanation = exp.explain_workflow_choice(
        "feature", "new feature", "medium",
        ["feature", "bugfix", "refactor"]
    )
    assert explanation.decision == "feature"
    assert "feature" in explanation.reason.lower()

def test_explainability_patch_safety():
    from core.project_manager.runtime.explainability import ExecutionExplainability
    exp = ExecutionExplainability()
    explanation = exp.explain_patch_safety(
        "core/main.py", True, 0.2,
        ["syntax_check", "import_check"], []
    )
    assert explanation.decision == "safe"
    assert "0.2" in explanation.reason

def test_explainability_format():
    from core.project_manager.runtime.explainability import ExecutionExplainability
    exp = ExecutionExplainability()
    explanation = exp.explain_workflow_choice("bugfix", "fix", "low", ["bugfix", "feature"])
    formatted = exp.format_explanation(explanation)
    assert "Workflow Choice" in formatted
    assert "bugfix" in formatted


# ── P11: Workflow Templates ──

def test_workflow_template_registry():
    from core.project_manager.runtime.workflow_templates import WorkflowTemplateRegistry
    reg = WorkflowTemplateRegistry()
    names = reg.get_template_names()
    assert "feature" in names
    assert "bugfix" in names
    assert "refactor" in names

def test_workflow_template_get():
    from core.project_manager.runtime.workflow_templates import WorkflowTemplateRegistry
    reg = WorkflowTemplateRegistry()
    t = reg.get_template("feature")
    assert t is not None
    assert t.name == "feature"
    assert len(t.steps) > 0

def test_workflow_template_by_tag():
    from core.project_manager.runtime.workflow_templates import WorkflowTemplateRegistry
    reg = WorkflowTemplateRegistry()
    templates = reg.list_templates(tag="development")
    assert len(templates) >= 1


# ── P12: Runtime Recovery ──

def test_recovery_create_point():
    from core.project_manager.runtime.recovery import RuntimeRecoverySystem
    rrs = RuntimeRecoverySystem(Path("/tmp"))
    rp = rrs.create_recovery_point("Before changes", git_ref="abc123")
    assert rp.id != ""
    assert rp.description == "Before changes"

def test_recovery_operations():
    from core.project_manager.runtime.recovery import (
        RuntimeRecoverySystem, RecoveryStatus
    )
    rrs = RuntimeRecoverySystem(Path("/tmp"))
    rp = rrs.create_recovery_point("Test point")
    op = rrs.restore_checkpoint(rp.id)
    assert op.status == RecoveryStatus.COMPLETED

def test_recovery_latest_point():
    from core.project_manager.runtime.recovery import RuntimeRecoverySystem
    rrs = RuntimeRecoverySystem(Path("/tmp"))
    rrs.create_recovery_point("First")
    rrs.create_recovery_point("Second")
    latest = rrs.get_latest_recovery_point()
    assert latest is not None
    assert latest.description == "Second"


# ── P14: Knowledge Graph ──

def test_knowledge_graph_add_node():
    from core.project_manager.runtime.knowledge_graph import (
        EngineeringKnowledgeGraph, NodeType
    )
    g = EngineeringKnowledgeGraph()
    node = g.add_node(NodeType.MODULE, "core/main.py")
    assert node.id != ""
    assert node.node_type == NodeType.MODULE

def test_knowledge_graph_add_edge():
    from core.project_manager.runtime.knowledge_graph import (
        EngineeringKnowledgeGraph, NodeType, EdgeType
    )
    g = EngineeringKnowledgeGraph()
    a = g.add_node(NodeType.MODULE, "module_a")
    b = g.add_node(NodeType.MODULE, "module_b")
    edge = g.add_edge(a.id, b.id, EdgeType.DEPENDS_ON)
    assert edge is not None

def test_knowledge_graph_neighbors():
    from core.project_manager.runtime.knowledge_graph import (
        EngineeringKnowledgeGraph, NodeType, EdgeType
    )
    g = EngineeringKnowledgeGraph()
    a = g.add_node(NodeType.MODULE, "a")
    b = g.add_node(NodeType.MODULE, "b")
    g.add_edge(a.id, b.id, EdgeType.DEPENDS_ON)
    neighbors = g.get_neighbors(a.id)
    assert len(neighbors) == 1
    assert neighbors[0].label == "b"

def test_knowledge_graph_path():
    from core.project_manager.runtime.knowledge_graph import (
        EngineeringKnowledgeGraph, NodeType, EdgeType
    )
    g = EngineeringKnowledgeGraph()
    a = g.add_node(NodeType.MODULE, "a")
    b = g.add_node(NodeType.MODULE, "b")
    c = g.add_node(NodeType.MODULE, "c")
    g.add_edge(a.id, b.id, EdgeType.DEPENDS_ON)
    g.add_edge(b.id, c.id, EdgeType.DEPENDS_ON)
    path = g.find_path(a.id, c.id)
    assert path is not None
    assert len(path) == 3


# ── P16: Trust Calibration ──

def test_trust_calibration_register():
    from core.project_manager.runtime.trust_calibration import (
        TrustCalibrationSystem, TrustLevel
    )
    tcs = TrustCalibrationSystem()
    score = tcs.register_target("feature", "workflow")
    assert score.target_id == "feature"
    assert score.level == TrustLevel.MEDIUM

def test_trust_calibration_success():
    from core.project_manager.runtime.trust_calibration import (
        TrustCalibrationSystem, TrustLevel
    )
    tcs = TrustCalibrationSystem()
    tcs.register_target("feature", "workflow")
    for i in range(10):
        tcs.record_success("feature")
    level = tcs.get_trust_level("feature")
    assert level in (TrustLevel.HIGH, TrustLevel.VERIFIED)

def test_trust_calibration_failure():
    from core.project_manager.runtime.trust_calibration import (
        TrustCalibrationSystem, TrustLevel
    )
    tcs = TrustCalibrationSystem()
    tcs.register_target("bugfix", "workflow")
    for i in range(5):
        tcs.record_failure("bugfix")
    assert tcs.should_stricten("bugfix") is True

def test_trust_calibration_streamline():
    from core.project_manager.runtime.trust_calibration import TrustCalibrationSystem
    tcs = TrustCalibrationSystem()
    tcs.register_target("cleanup", "workflow")
    for i in range(20):
        tcs.record_success("cleanup")
    assert tcs.should_streamline("cleanup") is True
