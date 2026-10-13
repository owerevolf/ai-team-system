"""
Тесты автопоиска источников моделей и скоринга (WP5).

Проверяют логику без обращения к сети и без реальных моделей: каталог, поведение пробников,
сохранение состояния, бенчмарк на заглушках и выбор лучшей модели под тип задачи.
"""

import json

from core import model_scores, provider_probe


class TestProviderCatalog:
    def test_catalog_has_free_local_source(self):
        rows = provider_probe.catalogue_for_ui()
        ollama = next(r for r in rows if r["id"] == "ollama")
        assert ollama["cost"] == "free"
        assert ollama["reachable_from_ru"] == "yes"
        assert ollama["needs_key"] is False

    def test_every_row_has_required_fields(self):
        for row in provider_probe.catalogue_for_ui():
            assert row["name"], "у источника нет названия"
            assert row["kind"] in ("local", "aggregator", "cloud")
            assert row["cost"] in ("free", "paid")
            assert row["reachable_from_ru"] in ("yes", "no", "unknown")
            assert row["how"], "не сказано, как получить источник"

    def test_openrouter_is_marked_unreachable_from_ru(self):
        row = next(r for r in provider_probe.catalogue_for_ui() if r["id"] == "openrouter")
        assert row["reachable_from_ru"] == "no"


class TestProbes:
    def test_missing_key_reports_no_key(self):
        probe = provider_probe.probe_http_provider("groq", env={})
        assert probe.available is False
        assert "нет ключа" in probe.note

    def test_unconfigured_compat_reports_hint(self):
        probe = provider_probe.probe_http_provider("openai_compat", env={})
        assert probe.available is False
        assert "OPENAI_COMPAT_BASE_URL" in probe.note

    def test_ollama_probe_survives_dead_service(self):
        probe = provider_probe.probe_ollama("http://127.0.0.1:9")
        assert probe.available is False
        assert probe.note

    def test_free_available_filters_by_cost_and_status(self):
        state = {
            "ollama": {"available": True},
            "groq": {"available": True},
            "deepseek": {"available": True},
            "openrouter": {"available": False},
        }
        assert provider_probe.free_available(state) == ["ollama", "groq"]

    def test_state_roundtrip(self, tmp_path):
        state = {"ollama": {"available": True, "note": "моделей: 1"}}
        path = provider_probe.save_state(state, tmp_path / "state.json")

        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["providers"]["ollama"]["available"] is True
        assert provider_probe.load_state(path)["ollama"]["note"] == "моделей: 1"

    def test_no_keys_are_stored(self, tmp_path):
        """В файл состояния не должны попадать ключи — только статусы."""
        probe = provider_probe.probe_http_provider("groq", env={"GROQ_API_KEY": "секрет-которого-нет"})
        provider_probe.save_state({"groq": probe.to_dict()}, tmp_path / "state.json")
        raw = (tmp_path / "state.json").read_text(encoding="utf-8")
        assert "секрет-которого-нет" not in raw


class TestScoring:
    def test_benchmark_counts_passed_tasks(self):
        tasks = [
            model_scores.BenchTask("t1", "code", "?", lambda text: "def" in text),
            model_scores.BenchTask("t2", "code", "?", lambda text: "return" in text),
        ]
        run = model_scores.run_benchmark(lambda prompt: "def f():\n    return 1", tasks=tasks)
        assert run["passed"] == 2
        assert run["total"] == 2
        assert model_scores.score_from_results(run) == 1.0

    def test_benchmark_tolerates_model_error(self):
        def boom(prompt):
            raise RuntimeError("модель недоступна")

        run = model_scores.run_benchmark(boom, tasks=model_scores.TASKS[:2])
        assert run["passed"] == 0
        assert all(task["error"] == "RuntimeError" for task in run["tasks"])

    def test_record_run_and_pick_strongest(self, tmp_path):
        path = tmp_path / "scores.json"
        strong = {"total": 2, "passed": 2, "tasks": [
            {"id": "a", "kind": "code", "passed": True, "ms": 100},
            {"id": "b", "kind": "code", "passed": True, "ms": 100},
        ]}
        weak = {"total": 2, "passed": 1, "tasks": [
            {"id": "a", "kind": "code", "passed": True, "ms": 10},
            {"id": "b", "kind": "code", "passed": False, "ms": 10},
        ]}
        model_scores.record_run("strong", strong, path)
        model_scores.record_run("weak", weak, path)

        scores = model_scores.load_scores(path)
        assert model_scores.best_model("code", scores) == "strong"
        assert model_scores.best_model("code", scores, available=["weak"]) == "weak"
        assert model_scores.best_model("explain", scores) is None

    def test_tie_break_by_speed(self):
        scores = {
            "slow": {"tasks": [{"kind": "code", "passed": True, "ms": 900}]},
            "fast": {"tasks": [{"kind": "code", "passed": True, "ms": 100}]},
        }
        assert model_scores.best_model("code", scores) == "fast"

    def test_score_of_empty_run_is_zero(self):
        assert model_scores.score_from_results({"total": 0, "passed": 0, "tasks": []}) == 0.0
