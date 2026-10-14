"""
Тесты лестницы уровней (шаг 1.1).

До правки `standard` совпадал с `advanced`, а файлы `<роль>_advanced.md` не загружались
вообще. Теперь компетенция роли и стиль объяснения разделены: к промпту роли добавляется
надстройка `prompts/levels/<уровень>.md`, поэтому четыре уровня дают четыре разных промпта.
"""

from unittest.mock import Mock, patch

import pytest

from core.agent_manager import AgentManager

ROLE = "architect"


@pytest.fixture()
def manager():
    with patch("core.agent_manager.Database"):
        return AgentManager(Mock())


class TestExplanationLadder:
    def test_four_levels_produce_four_different_prompts(self, manager):
        prompts = {level: manager.get_agent_prompt(ROLE, level) for level in manager.LEVEL_ORDER}
        assert len(set(prompts.values())) == 4, "уровни должны давать разные промпты"

    @pytest.mark.parametrize("level", ["zero", "beginner", "standard", "advanced"])
    def test_each_level_has_its_own_overlay_marker(self, manager, level):
        prompt = manager.get_agent_prompt(ROLE, level)
        assert f"Уровень {level.upper()}" in prompt

    def test_standard_differs_from_advanced(self, manager):
        """Главный дефект до правки: эти два уровня были одинаковыми."""
        standard = manager.get_agent_prompt(ROLE, "standard")
        advanced = manager.get_agent_prompt(ROLE, "advanced")
        assert standard != advanced

    def test_unknown_level_falls_back_to_advanced(self, manager):
        assert manager.get_agent_prompt(ROLE, "какой-то") == manager.get_agent_prompt(ROLE, "advanced")

    def test_role_prompt_differs_between_zero_and_advanced(self, manager):
        """Уровни zero/beginner сохраняют свои файлы ролей (обратная совместимость)."""
        assert manager._load_role_prompt(ROLE, "zero") != manager._load_role_prompt(ROLE, "advanced")

    def test_missing_overlay_does_not_break_prompt(self, manager):
        """Если файла надстройки нет, промпт роли всё равно возвращается."""
        with patch.object(AgentManager, "_load_level_overlay", return_value=""):
            prompt = manager.get_agent_prompt(ROLE, "standard")
        assert prompt.strip()

    def test_language_specific_overlay_is_used(self, manager):
        """Английская надстройка берётся для lang="en", русская — по умолчанию."""
        english = manager.get_agent_prompt(ROLE, "zero", lang="en")
        russian = manager.get_agent_prompt(ROLE, "zero")
        assert "Level ZERO" in english
        assert "Уровень ZERO" in russian
        assert english != russian

    def test_unknown_language_falls_back_to_common_overlay(self, manager):
        """Если файлов языка нет, работает общая надстройка."""
        prompt = manager.get_agent_prompt(ROLE, "zero", lang="de")
        assert "Уровень ZERO" in prompt
