"""
Тесты агента истины (WP4, основа).

Индекс строится по настоящему репозиторию, поэтому проверки говорят о фактах с адресами
`файл:строка`, а не о догадках. Правило модуля: нет факта в индексе — честное «в коде этого нет».
"""

import textwrap
from pathlib import Path

import pytest

from core import truth

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def index():
    return truth.CodeIndex(REPO_ROOT).build()


class TestIndex:
    def test_finds_known_class(self, index):
        hits = index.find("ModelRouter")
        assert hits, "класс ModelRouter не найден в индексе"
        assert hits[0].kind == "class"
        assert hits[0].path == "core/model_router.py"
        assert hits[0].line > 0

    def test_finds_method_with_parent(self, index):
        hits = [s for s in index.find("get_agent_prompt") if s.kind == "method"]
        assert hits, "метод get_agent_prompt не найден"
        assert hits[0].parent == "AgentManager"

    def test_finds_routes(self, index):
        paths = {s.name for s in index.routes()}
        assert "/api/health" in paths

    def test_finds_module_constant(self, index):
        assert index.find("SKIP_DIRS"), "константа SKIP_DIRS не найдена"

    def test_unknown_name_gives_nothing(self, index):
        assert index.find("AbsolutelyNotAFunctionHere") == []


class TestAsk:
    def test_returns_facts_with_sources(self, index):
        facts = truth.ask("где живёт get_agent_prompt и что делает ModelRouter?", index)
        assert facts, "факты не найдены"
        assert all(f.symbol.source() for f in facts)
        assert "get_agent_prompt" in {f.symbol.name for f in facts}

    def test_empty_result_for_unknown_question(self, index):
        assert truth.ask("расскажи про квазар и бозон Хиггса", index) == []

    def test_no_duplicate_facts(self, index):
        facts = truth.ask("ModelRouter ModelRouter ModelRouter", index)
        keys = [(f.symbol.name, f.symbol.path, f.symbol.line) for f in facts]
        assert len(keys) == len(set(keys))


class TestVerifier:
    def test_flags_invented_function(self, index):
        issues = truth.verify_text("Вызови `create_magic_widget()` из core/magic.py", index)
        assert "create_magic_widget" in {i.name for i in issues}

    def test_accepts_real_names(self, index):
        text = "Используй `get_agent_prompt` и `ModelRouter` из core/agent_manager.py"
        flagged = {i.name for i in truth.verify_text(text, index)}
        assert not ({"get_agent_prompt", "ModelRouter"} & flagged)

    def test_ignores_stdlib_and_builtins(self, index):
        assert truth.verify_text("import json, os; print(len(items))", index) == []


class TestSmallTree:
    """Поведение не зависит от содержимого боевого репозитория."""

    @pytest.fixture()
    def small_root(self, tmp_path):
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "mod.py").write_text(
            textwrap.dedent(
                '''
                """Модуль."""

                CONST = 1


                class Thing:
                    def method_one(self):
                        return 1


                def free_function():
                    return 2
                '''
            ),
            encoding="utf-8",
        )
        return tmp_path

    def test_builds_symbols_of_all_kinds(self, small_root):
        idx = truth.CodeIndex(small_root).build()
        kinds = {(s.name, s.kind) for s in idx.symbols}
        assert ("Thing", "class") in kinds
        assert ("method_one", "method") in kinds
        assert ("free_function", "function") in kinds
        assert ("CONST", "constant") in kinds

    def test_save_and_load_roundtrip(self, small_root):
        idx = truth.CodeIndex(small_root).build()
        path = idx.save(small_root / "index.json")
        restored = truth.CodeIndex.load(path)
        assert len(restored.symbols) == len(idx.symbols)

    def test_route_extraction(self, small_root):
        (small_root / "pkg" / "api.py").write_text(
            textwrap.dedent(
                '''
                from fastapi import APIRouter

                router = APIRouter()


                @router.get("/api/ping")
                async def ping():
                    return {"ok": True}
                '''
            ),
            encoding="utf-8",
        )
        idx = truth.CodeIndex(small_root).build()
        assert "/api/ping" in {s.name for s in idx.routes()}
