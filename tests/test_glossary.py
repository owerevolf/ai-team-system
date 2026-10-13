"""
Тесты глоссария терминов (начало WP2 — обучение сленгу).

Глоссарий — это данные: `config/glossary.ru.json`. Модуль `core/glossary.py` умеет искать
термин по названию и синониму, находить термины в тексте (для подсветки в ответах агентов)
и отдавать короткое объяснение.
"""

import pytest

from core import glossary


class TestGlossaryData:
    def test_glossary_file_is_loadable(self):
        terms = glossary.load_terms(force=True)
        assert len(terms) >= 40, f"терминов слишком мало: {len(terms)}"

    def test_every_term_has_required_fields(self):
        for item in glossary.load_terms():
            assert item.get("term"), "у термина нет названия"
            assert item.get("simple"), f"у термина «{item.get('term')}» нет простого объяснения"

    def test_term_names_are_unique(self):
        names = [item["term"].lower() for item in glossary.load_terms()]
        duplicates = {n for n in names if names.count(n) > 1}
        assert not duplicates, f"дубли терминов: {duplicates}"


class TestFindTerm:
    def test_find_by_name(self):
        item = glossary.find_term("промпт")
        assert item and item["term"] == "промпт"

    def test_find_by_alias(self):
        by_name = glossary.find_term("промпт")
        by_alias = glossary.find_term("prompt")
        assert by_alias is not None
        assert by_alias["term"] == by_name["term"]

    def test_case_insensitive(self):
        assert glossary.find_term("КОММИТ")["term"] == "коммит"

    def test_unknown_term_returns_none(self):
        assert glossary.find_term("нет-такого-слова") is None

    def test_explain_returns_readable_line(self):
        line = glossary.explain("коммит")
        assert line.startswith("коммит —")
        assert len(line) > 30


class TestFindTermsInText:
    def test_finds_terms_used_in_agent_answer(self):
        answer = "Сделай коммит и запушь изменения в репозиторий на GitHub."
        found = {item["term"] for item in glossary.find_terms_in_text(answer)}
        assert {"коммит", "репозиторий"} <= found

    def test_order_follows_first_appearance(self):
        text = "Сначала репозиторий, потом коммит."
        found = [item["term"] for item in glossary.find_terms_in_text(text)]
        assert found.index("репозиторий") < found.index("коммит")

    def test_no_terms_no_result(self):
        assert glossary.find_terms_in_text("просто текст без терминов") == []

    def test_empty_text(self):
        assert glossary.find_terms_in_text("") == []

    def test_limit_respected(self):
        text = "репозиторий, коммит, ветка, пуш, тест, модель"
        assert len(glossary.find_terms_in_text(text, limit=3)) == 3
