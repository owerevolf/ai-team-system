"""
Tests for all Phase 9 durability modules.

Covers:
  - state_lifecycle (P1)
  - context_gc (P2)
  - recovery_engine (P3)
  - large_repo (P4)
  - explainability_layer (P5)
  - cognitive_load (P6)
  - chaos_testing (P7)
  - observability (P8)
  - plugin_boundaries (P9)
  - simplification (P10)
"""

import os
import tempfile
import shutil
import time
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
# P1 — State Lifecycle
# ===========================================================================

class TestStateLifecycle:
    def test_put_and_get(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        mgr.put("key1", "value1", StateTier.SESSION)
        assert mgr.get("key1") == "value1"

    def test_get_nonexistent(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        assert mgr.get("nonexistent") is None
        assert mgr.get("nonexistent", "default") == "default"

    def test_ephemeral_expires(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        mgr.put("temp", "data", StateTier.EPHEMERAL, ttl=0.01)
        assert mgr.get("temp") == "data"
        time.sleep(0.02)
        assert mgr.get("temp") is None

    def test_structural_never_expires(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        mgr.put("arch", {"map": "data"}, StateTier.STRUCTURAL)
        entry = mgr.get_entry("arch")
        assert entry is not None
        assert entry.tier == StateTier.STRUCTURAL
        assert not entry.is_expired

    def test_promote(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        mgr.put("key", "val", StateTier.EPHEMERAL)
        assert mgr.promote("key", StateTier.STRUCTURAL) is True
        entry = mgr.get_entry("key")
        assert entry.tier == StateTier.STRUCTURAL

    def test_remove(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        mgr.put("key", "val", StateTier.SESSION)
        assert mgr.remove("key") is True
        assert mgr.get("key") is None

    def test_cleanup(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        mgr.put("temp1", "a", StateTier.EPHEMERAL, ttl=0.01)
        mgr.put("temp2", "b", StateTier.EPHEMERAL, ttl=0.01)
        mgr.put("perm", "c", StateTier.STRUCTURAL)
        time.sleep(0.02)
        removed = mgr.cleanup()
        assert removed.get("ephemeral", 0) == 2
        assert mgr.get("perm") == "c"

    def test_tier_stats(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        mgr.put("e1", "a", StateTier.EPHEMERAL)
        mgr.put("s1", "b", StateTier.SESSION)
        mgr.put("o1", "c", StateTier.OPERATIONAL)
        mgr.put("st1", "d", StateTier.STRUCTURAL)
        stats = mgr.get_tier_stats()
        assert stats["ephemeral"]["total"] == 1
        assert stats["session"]["total"] == 1
        assert stats["operational"]["total"] == 1
        assert stats["structural"]["total"] == 1

    def test_get_all_keys(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr = StateLifecycleManager(tmp_dir)
        mgr.put("a", 1, StateTier.EPHEMERAL)
        mgr.put("b", 2, StateTier.SESSION)
        mgr.put("c", 3, StateTier.STRUCTURAL)
        keys = mgr.get_all_keys()
        assert len(keys) == 3

    def test_persistence(self, tmp_dir):
        from core.project_manager.runtime.durability.state_lifecycle import (
            StateLifecycleManager, StateTier,
        )
        mgr1 = StateLifecycleManager(tmp_dir)
        mgr1.put("persist", "hello", StateTier.STRUCTURAL)
        # Create new manager pointing to same dir
        mgr2 = StateLifecycleManager(tmp_dir)
        assert mgr2.get("persist") == "hello"


# ===========================================================================
# P2 — Context GC
# ===========================================================================

class TestContextGC:
    def test_track_and_get(self):
        from core.project_manager.runtime.durability.context_gc import (
            ContextGC, ContextType,
        )
        gc = ContextGC()
        gc.track("ctx1", ContextType.ASSUMPTION, ttl=3600)
        status = gc.get_status("ctx1")
        assert status["key"] == "ctx1"
        assert status["type"] == "assumption"

    def test_invalidate(self):
        from core.project_manager.runtime.durability.context_gc import (
            ContextGC, ContextType, ContextStatus,
        )
        gc = ContextGC()
        gc.track("ctx1", ContextType.ASSUMPTION, ttl=3600)
        assert gc.invalidate("ctx1", source="test") is True
        status = gc.get_status("ctx1")
        assert status["status"] == "invalidated"
        assert status["prunable"] is True

    def test_audit_never_pruned(self):
        from core.project_manager.runtime.durability.context_gc import (
            ContextGC, ContextType,
        )
        gc = ContextGC()
        gc.track("audit1", ContextType.ASSUMPTION, is_audit=True)
        status = gc.get_status("audit1")
        assert status["is_audit"] is True
        assert status["prunable"] is False
        report = gc.collect()
        assert report.audit_protected == 1
        assert report.pruned == 0

    def test_collect_expired(self):
        from core.project_manager.runtime.durability.context_gc import (
            ContextGC, ContextType,
        )
        gc = ContextGC()
        gc.track("old", ContextType.SUMMARY, ttl=0.01)
        time.sleep(0.02)
        report = gc.collect()
        assert report.pruned == 1
        assert report.kept == 0

    def test_collect_dry_run(self):
        from core.project_manager.runtime.durability.context_gc import (
            ContextGC, ContextType,
        )
        gc = ContextGC()
        gc.track("old", ContextType.SUMMARY, ttl=0.01)
        time.sleep(0.02)
        report = gc.collect(dry_run=True)
        assert report.pruned == 1
        # Should still be there after dry run
        assert gc.get_status("old") is not None

    def test_validate_resets_ttl(self):
        from core.project_manager.runtime.durability.context_gc import (
            ContextGC, ContextType,
        )
        gc = ContextGC()
        gc.track("ctx1", ContextType.ASSUMPTION, ttl=0.02)
        time.sleep(0.01)
        gc.validate("ctx1")
        time.sleep(0.015)
        # Should still be valid because validate reset the TTL
        status = gc.get_status("ctx1")
        assert status["status"] == "active"

    def test_get_stats(self):
        from core.project_manager.runtime.durability.context_gc import (
            ContextGC, ContextType,
        )
        gc = ContextGC()
        gc.track("a1", ContextType.ASSUMPTION)
        gc.track("a2", ContextType.ASSUMPTION)
        gc.track("w1", ContextType.WORKFLOW_STATE)
        stats = gc.get_stats()
        assert stats["total_tracked"] == 3


# ===========================================================================
# P3 — Recovery Engine
# ===========================================================================

class TestRecoveryEngine:
    def test_register_and_get_workflow(self, tmp_dir):
        from core.project_manager.runtime.durability.recovery_engine import (
            DeterministicRecoveryEngine, RecoveryStep,
        )
        engine = DeterministicRecoveryEngine(tmp_dir)
        steps = [
            RecoveryStep("s1", "Step 1", "action1"),
            RecoveryStep("s2", "Step 2", "action2"),
        ]
        engine.register_workflow("wf1", steps)
        wf = engine.get_workflow("wf1")
        assert wf is not None
        assert len(wf) == 2

    def test_capture_failure(self, tmp_dir):
        from core.project_manager.runtime.durability.recovery_engine import (
            DeterministicRecoveryEngine, RecoveryStep,
        )
        engine = DeterministicRecoveryEngine(tmp_dir)
        step = RecoveryStep("s2", "Step 2", "action2")
        snapshot = engine.capture_failure("wf1", step, "Something broke", "runtime")
        assert snapshot.workflow_id == "wf1"
        assert snapshot.failed_step_id == "s2"
        assert snapshot.error_message == "Something broke"

    def test_replay(self, tmp_dir):
        from core.project_manager.runtime.durability.recovery_engine import (
            DeterministicRecoveryEngine, RecoveryStep,
        )
        engine = DeterministicRecoveryEngine(tmp_dir)
        steps = [
            RecoveryStep("s1", "Step 1", "action1"),
            RecoveryStep("s2", "Step 2", "action2"),
            RecoveryStep("s3", "Step 3", "action3"),
        ]
        engine.register_workflow("wf1", steps)
        result = engine.replay("wf1", from_step="s2")
        assert result.success is True
        assert result.steps_replayed == 2  # s2 and s3
        assert result.steps_skipped == 1  # s1

    def test_replay_nonexistent_workflow(self, tmp_dir):
        from core.project_manager.runtime.durability.recovery_engine import (
            DeterministicRecoveryEngine,
        )
        engine = DeterministicRecoveryEngine(tmp_dir)
        result = engine.replay("nonexistent", from_step="s1")
        assert result.success is False

    def test_rewind_step(self, tmp_dir):
        from core.project_manager.runtime.durability.recovery_engine import (
            DeterministicRecoveryEngine, RecoveryStep, RecoveryStepStatus,
        )
        engine = DeterministicRecoveryEngine(tmp_dir)
        steps = [
            RecoveryStep("s1", "Step 1", "action1", status=RecoveryStepStatus.COMPLETED),
            RecoveryStep("s2", "Step 2", "action2", status=RecoveryStepStatus.FAILED),
        ]
        engine.register_workflow("wf1", steps)
        result = engine.rewind_step("wf1", "s2")
        assert result["rewound"] is True
        assert result["previous_status"] == "failed"

    def test_get_snapshots(self, tmp_dir):
        from core.project_manager.runtime.durability.recovery_engine import (
            DeterministicRecoveryEngine, RecoveryStep,
        )
        engine = DeterministicRecoveryEngine(tmp_dir)
        step = RecoveryStep("s1", "Step 1", "action1")
        engine.capture_failure("wf1", step, "Error 1")
        engine.capture_failure("wf1", step, "Error 2")
        snapshots = engine.get_snapshots(limit=10)
        assert len(snapshots) == 2


# ===========================================================================
# P4 — Large Repository Survival
# ===========================================================================

class TestLargeRepoSurvival:
    def test_analyze_small_repo(self, tmp_dir):
        from core.project_manager.runtime.durability.large_repo import (
            LargeRepoSurvival, RepoSizeCategory,
        )
        # Create a small project
        (Path(tmp_dir) / "main.py").write_text("x = 1\n")
        (Path(tmp_dir) / "utils.py").write_text("def f(): pass\n")

        survival = LargeRepoSurvival()
        profile = survival.analyze(tmp_dir)
        assert profile.size_category == RepoSizeCategory.SMALL
        assert profile.total_files == 2

    def test_analyze_detects_languages(self, tmp_dir):
        from core.project_manager.runtime.durability.large_repo import LargeRepoSurvival
        (Path(tmp_dir) / "app.py").write_text("x = 1\n")
        (Path(tmp_dir) / "index.js").write_text("x = 1\n")

        survival = LargeRepoSurvival()
        profile = survival.analyze(tmp_dir)
        assert "python" in profile.languages
        assert "javascript" in profile.languages

    def test_analyze_detects_git(self, tmp_dir):
        from core.project_manager.runtime.durability.large_repo import LargeRepoSurvival
        os.system(f"cd {tmp_dir} && git init -q && git config user.email 't@t.com' && git config user.name 'T' && echo x > f && git add -A && git commit -q -m init")
        (Path(tmp_dir) / "main.py").write_text("x = 1\n")

        survival = LargeRepoSurvival()
        profile = survival.analyze(tmp_dir)
        assert profile.has_git is True

    def test_get_strategy_small(self, tmp_dir):
        from core.project_manager.runtime.durability.large_repo import (
            LargeRepoSurvival, RepoProfile, RepoSizeCategory, RepoHealth,
        )
        survival = LargeRepoSurvival()
        profile = RepoProfile(path=tmp_dir, total_files=50, size_category=RepoSizeCategory.SMALL)
        strategy = survival.get_strategy(profile)
        assert strategy["index_batch_size"] == 100
        assert strategy["parallel_scanning"] is False

    def test_get_strategy_monorepo(self, tmp_dir):
        from core.project_manager.runtime.durability.large_repo import (
            LargeRepoSurvival, RepoProfile, RepoSizeCategory, RepoHealth,
        )
        survival = LargeRepoSurvival()
        profile = RepoProfile(path=tmp_dir, total_files=50000, size_category=RepoSizeCategory.MONOREPO)
        strategy = survival.get_strategy(profile)
        assert strategy["parallel_scanning"] is True
        assert strategy["memory_limit_mb"] == 1024

    def test_estimate_index_time(self, tmp_dir):
        from core.project_manager.runtime.durability.large_repo import (
            LargeRepoSurvival, RepoProfile, RepoSizeCategory,
        )
        survival = LargeRepoSurvival()
        profile = RepoProfile(path=tmp_dir, total_files=500, size_category=RepoSizeCategory.MEDIUM)
        estimate = survival.estimate_index_time(profile)
        assert "estimated_seconds" in estimate
        assert "estimated_human" in estimate


# ===========================================================================
# P5 — Explainability Layer
# ===========================================================================

class TestExplainabilityLayer:
    def test_explain(self):
        from core.project_manager.runtime.durability.explainability_layer import (
            ExplainabilityLayer,
        )
        layer = ExplainabilityLayer()
        exp = layer.explain(
            action_type="file_modify",
            why="Fix broken import",
            source="repo_repair scan",
            constraints=["beginner_mode"],
            impact=["src/auth.py"],
            confidence=0.95,
            recovery="git reset --hard abc123",
        )
        assert exp.action_type == "file_modify"
        assert exp.confidence == 0.95

    def test_get_explanations(self):
        from core.project_manager.runtime.durability.explainability_layer import (
            ExplainabilityLayer,
        )
        layer = ExplainabilityLayer()
        layer.explain(action_type="file_modify", why="Fix A")
        layer.explain(action_type="file_delete", why="Remove B")
        layer.explain(action_type="file_modify", why="Fix C")
        all_exp = layer.get_explanations()
        assert len(all_exp) == 3
        modifies = layer.get_explanations(action_type="file_modify")
        assert len(modifies) == 2

    def test_format_display(self):
        from core.project_manager.runtime.durability.explainability_layer import (
            ExplainabilityLayer,
        )
        layer = ExplainabilityLayer()
        exp = layer.explain(
            action_type="test_action",
            why="Because of X",
            source="data Y",
            confidence=0.9,
        )
        display = exp.format_display()
        assert "test_action" in display
        assert "Because of X" in display
        assert "90%" in display

    def test_get_stats(self):
        from core.project_manager.runtime.durability.explainability_layer import (
            ExplainabilityLayer,
        )
        layer = ExplainabilityLayer()
        layer.explain(action_type="a", confidence=0.9)
        layer.explain(action_type="b", confidence=0.8)
        stats = layer.get_stats()
        assert stats["total_explanations"] == 2
        assert stats["avg_confidence"] == 0.85


# ===========================================================================
# P6 — Cognitive Load Protection
# ===========================================================================

class TestCognitiveLoad:
    def test_beginner_filter(self):
        from core.project_manager.runtime.durability.cognitive_load import (
            CognitiveLoadProtector, DetailLevel,
        )
        prot = CognitiveLoadProtector(DetailLevel.BEGINNER)
        assert prot.should_show("approvals") is True
        assert prot.should_show("traces") is False
        assert prot.should_show("educational_overlays") is True
        assert prot.should_show("raw_errors") is False

    def test_expert_filter(self):
        from core.project_manager.runtime.durability.cognitive_load import (
            CognitiveLoadProtector, DetailLevel,
        )
        prot = CognitiveLoadProtector(DetailLevel.EXPERT)
        assert prot.should_show("approvals") is True
        assert prot.should_show("traces") is True
        assert prot.should_show("governance_details") is True
        assert prot.should_show("raw_errors") is True

    def test_filter_items(self):
        from core.project_manager.runtime.durability.cognitive_load import (
            CognitiveLoadProtector, DetailLevel,
        )
        prot = CognitiveLoadProtector(DetailLevel.BEGINNER)
        items = [{"type": "approval", "id": i} for i in range(20)]
        filtered = prot.filter_items(items, "approval")
        assert len(filtered) <= 5  # beginner max_items_per_panel

    def test_set_level(self):
        from core.project_manager.runtime.durability.cognitive_load import (
            CognitiveLoadProtector, DetailLevel,
        )
        prot = CognitiveLoadProtector(DetailLevel.BEGINNER)
        assert prot.should_show("traces") is False
        prot.set_level(DetailLevel.EXPERT)
        assert prot.should_show("traces") is True

    def test_get_filter(self):
        from core.project_manager.runtime.durability.cognitive_load import (
            CognitiveLoadProtector, DetailLevel,
        )
        prot = CognitiveLoadProtector(DetailLevel.ADVANCED)
        f = prot.get_filter()
        assert f["detail_level"] == "advanced"
        assert "traces" in f["visible_elements"]


# ===========================================================================
# P7 — Chaos Testing
# ===========================================================================

class TestChaosTesting:
    def test_list_scenarios(self):
        from core.project_manager.runtime.durability.chaos_testing import ChaosTester
        tester = ChaosTester()
        scenarios = tester.list_scenarios()
        assert len(scenarios) >= 5

    def test_run_scenario(self):
        from core.project_manager.runtime.durability.chaos_testing import ChaosTester
        tester = ChaosTester()
        result = tester.run_scenario("ctx-corrupt")
        assert result.scenario_id == "ctx-corrupt"

    def test_run_all(self):
        from core.project_manager.runtime.durability.chaos_testing import ChaosTester
        tester = ChaosTester()
        results = tester.run_all()
        assert len(results) >= 5

    def test_generate_report(self):
        from core.project_manager.runtime.durability.chaos_testing import ChaosTester
        tester = ChaosTester()
        tester.run_all()
        report = tester.generate_report()
        assert "total_scenarios" in report
        assert "pass_rate" in report

    def test_unknown_scenario(self):
        from core.project_manager.runtime.durability.chaos_testing import ChaosTester
        tester = ChaosTester()
        result = tester.run_scenario("nonexistent")
        assert result.success is False


# ===========================================================================
# P8 — Operational Observability
# ===========================================================================

class TestObservability:
    def test_record_event(self):
        from core.project_manager.runtime.durability.observability import (
            OperationalObservability, EntryType,
        )
        obs = OperationalObservability()
        entry = obs.record_event(EntryType.RUNTIME_EVENT, "Import started", data={"files": 10})
        assert entry.title == "Import started"
        assert entry.success is True

    def test_record_decision(self):
        from core.project_manager.runtime.durability.observability import (
            OperationalObservability,
        )
        obs = OperationalObservability()
        trace = obs.record_decision("Use incremental", "Only 3 files changed", confidence=0.95)
        assert trace.decision == "Use incremental"
        assert trace.confidence == 0.95

    def test_get_timeline(self):
        from core.project_manager.runtime.durability.observability import (
            OperationalObservability, EntryType,
        )
        obs = OperationalObservability()
        obs.record_event(EntryType.RUNTIME_EVENT, "Event 1")
        obs.record_event(EntryType.ERROR, "Event 2", success=False)
        obs.record_event(EntryType.RUNTIME_EVENT, "Event 3")
        timeline = obs.get_timeline()
        assert len(timeline) == 3
        errors = obs.get_timeline(entry_type=EntryType.ERROR)
        assert len(errors) == 1

    def test_get_decisions(self):
        from core.project_manager.runtime.durability.observability import (
            OperationalObservability,
        )
        obs = OperationalObservability()
        obs.record_decision("A", "reason A")
        obs.record_decision("B", "reason B")
        decisions = obs.get_decisions()
        assert len(decisions) == 2

    def test_get_summary(self):
        from core.project_manager.runtime.durability.observability import (
            OperationalObservability, EntryType,
        )
        obs = OperationalObservability()
        obs.record_event(EntryType.RUNTIME_EVENT, "E1")
        obs.record_event(EntryType.ERROR, "E2", success=False)
        obs.record_decision("D1", "reason", confidence=0.9)
        summary = obs.get_summary()
        assert summary["total_events"] == 2
        assert summary["errors"] == 1
        assert summary["total_decisions"] == 1


# ===========================================================================
# P9 — Plugin Boundaries
# ===========================================================================

class TestPluginBoundaries:
    def test_register_untrusted(self):
        from core.project_manager.runtime.durability.plugin_boundaries import (
            PluginBoundaryEnforcer, PluginManifest, PluginTrustLevel,
            PluginCapability,
        )
        enforcer = PluginBoundaryEnforcer()
        manifest = PluginManifest("p1", "Plugin 1", "1.0", trust_level=PluginTrustLevel.UNTRUSTED)
        sandbox = enforcer.register_plugin(manifest)
        assert sandbox.plugin_id == "p1"

    def test_check_capability(self):
        from core.project_manager.runtime.durability.plugin_boundaries import (
            PluginBoundaryEnforcer, PluginManifest, PluginTrustLevel,
            PluginCapability,
        )
        enforcer = PluginBoundaryEnforcer()
        manifest = PluginManifest("p1", "Plugin 1", "1.0", trust_level=PluginTrustLevel.BASIC)
        enforcer.register_plugin(manifest)
        assert enforcer.check_capability("p1", PluginCapability.READ_FILES) is True
        assert enforcer.check_capability("p1", PluginCapability.MODIFY_GOVERNANCE) is False

    def test_untrusted_cannot_request_governance(self):
        from core.project_manager.runtime.durability.plugin_boundaries import (
            PluginBoundaryEnforcer, PluginManifest, PluginTrustLevel,
            PluginCapability,
        )
        enforcer = PluginBoundaryEnforcer()
        manifest = PluginManifest(
            "p1", "Plugin 1", "1.0",
            trust_level=PluginTrustLevel.UNTRUSTED,
            requested_capabilities=[PluginCapability.MODIFY_GOVERNANCE],
        )
        with pytest.raises(ValueError):
            enforcer.register_plugin(manifest)

    def test_get_allowed_capabilities(self):
        from core.project_manager.runtime.durability.plugin_boundaries import (
            PluginBoundaryEnforcer, PluginManifest, PluginTrustLevel,
        )
        enforcer = PluginBoundaryEnforcer()
        manifest = PluginManifest("p1", "Plugin 1", "1.0", trust_level=PluginTrustLevel.TRUSTED)
        enforcer.register_plugin(manifest)
        caps = enforcer.get_allowed_capabilities("p1")
        assert "read_files" in caps
        assert "write_files" in caps
        assert "modify_governance" not in caps

    def test_unregister(self):
        from core.project_manager.runtime.durability.plugin_boundaries import (
            PluginBoundaryEnforcer, PluginManifest, PluginTrustLevel,
            PluginCapability,
        )
        enforcer = PluginBoundaryEnforcer()
        manifest = PluginManifest("p1", "Plugin 1", "1.0")
        enforcer.register_plugin(manifest)
        assert enforcer.unregister_plugin("p1") is True
        assert enforcer.check_capability("p1", PluginCapability.READ_FILES) is False

    def test_list_plugins(self):
        from core.project_manager.runtime.durability.plugin_boundaries import (
            PluginBoundaryEnforcer, PluginManifest, PluginTrustLevel,
        )
        enforcer = PluginBoundaryEnforcer()
        enforcer.register_plugin(PluginManifest("p1", "P1", "1.0"))
        enforcer.register_plugin(PluginManifest("p2", "P2", "2.0"))
        plugins = enforcer.list_plugins()
        assert len(plugins) == 2


# ===========================================================================
# P10 — Simplification
# ===========================================================================

class TestSimplification:
    def test_register_and_evaluate(self):
        from core.project_manager.runtime.durability.simplification import (
            RuntimeSimplification, SubsystemRisk,
        )
        simpl = RuntimeSimplification()
        simpl.register_subsystem("mod1", purpose="Handles X")
        for _ in range(10):
            simpl.record_usage("mod1")
        health = simpl.evaluate("mod1")
        assert health.name == "mod1"
        assert health.risk_level == SubsystemRisk.LOW

    def test_no_purpose_is_risky(self):
        from core.project_manager.runtime.durability.simplification import (
            RuntimeSimplification, SubsystemRisk,
        )
        simpl = RuntimeSimplification()
        simpl.register_subsystem("mod1", purpose="")
        health = simpl.evaluate("mod1")
        assert health.risk_level in (SubsystemRisk.MEDIUM, SubsystemRisk.HIGH)

    def test_never_used_is_suspicious(self):
        from core.project_manager.runtime.durability.simplification import (
            RuntimeSimplification,
        )
        simpl = RuntimeSimplification()
        simpl.register_subsystem("mod1", purpose="Does stuff")
        health = simpl.evaluate("mod1")
        assert any("Never used" in r for r in health.recommendations)

    def test_high_errors_is_risky(self):
        from core.project_manager.runtime.durability.simplification import (
            RuntimeSimplification, SubsystemRisk,
        )
        simpl = RuntimeSimplification()
        simpl.register_subsystem("mod1", purpose="Does stuff")
        for _ in range(15):
            simpl.record_error("mod1")
        health = simpl.evaluate("mod1")
        assert health.risk_level in (SubsystemRisk.HIGH, SubsystemRisk.DANGEROUS)

    def test_evaluate_all(self):
        from core.project_manager.runtime.durability.simplification import (
            RuntimeSimplification,
        )
        simpl = RuntimeSimplification()
        simpl.register_subsystem("a", purpose="A")
        simpl.register_subsystem("b", purpose="B")
        result = simpl.evaluate_all()
        assert result["total_subsystems"] == 2

    def test_removable_candidates(self):
        from core.project_manager.runtime.durability.simplification import (
            RuntimeSimplification,
        )
        simpl = RuntimeSimplification()
        simpl.register_subsystem("dead_mod", purpose="")
        simpl.register_subsystem("alive_mod", purpose="Important")
        candidates = simpl.get_removable_candidates()
        assert any(c["name"] == "dead_mod" for c in candidates)

    def test_record_usage(self):
        from core.project_manager.runtime.durability.simplification import (
            RuntimeSimplification,
        )
        simpl = RuntimeSimplification()
        simpl.register_subsystem("mod1", purpose="Test")
        simpl.record_usage("mod1")
        simpl.record_usage("mod1")
        ss = simpl._subsystems["mod1"]
        assert ss.usage_count == 2
