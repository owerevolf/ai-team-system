"""
Tests for new v5.1 modules
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from core.fallback_manager import FallbackManager, FallbackConfig, FallbackEvent
from core.learning_mode import LearningMode, TutorialStep
from core.mode_switcher import ModeSwitcher, MODES


class TestFallbackManager:
    def setup_method(self):
        self.manager = FallbackManager()
    
    def test_should_not_fallback_good_response(self):
        should, reason = self.manager.should_fallback(
            "This is a good response with enough tokens to pass the minimum threshold for testing purposes and more words here",
            5.0,
            "medium"
        )
        assert should is False
    
    def test_should_fallback_short_response(self):
        should, reason = self.manager.should_fallback(
            "Short",
            5.0,
            "hard"
        )
        assert should is True
    
    def test_should_fallback_uncertain(self):
        should, reason = self.manager.should_fallback(
            "I'm not sure about this answer",
            5.0,
            "medium"
        )
        assert should is True
    
    def test_should_fallback_timeout(self):
        should, reason = self.manager.should_fallback(
            "Some response text here",
            35.0,
            "medium"
        )
        assert should is True
    
    def test_should_not_fallback_always_local(self):
        config = FallbackConfig(always_local=True)
        manager = FallbackManager(config)
        
        should, reason = manager.should_fallback("Short", 5.0, "hard")
        assert should is False
    
    def test_get_fallback_provider_no_keys(self):
        with patch.dict('os.environ', {}, clear=True):
            provider = self.manager.get_fallback_provider()
            assert provider is None
    
    def test_record_fallback(self):
        self.manager.record_fallback("ollama", "groq", "timeout")
        assert len(self.manager.history) == 1
    
    def test_cache_response(self):
        self.manager.cache_response("test query", "test response")
        result = self.manager.get_cached_response("test query")
        assert result == "test response"
    
    def test_get_stats(self):
        self.manager.record_fallback("ollama", "groq", "test")
        stats = self.manager.get_stats()
        assert stats["total_fallbacks"] == 1


class TestLearningMode:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mode = LearningMode(Path(self.temp_dir))
    
    def test_get_current_step(self):
        step = self.mode.get_current_step()
        assert step is not None
        assert step.id == 1
    
    def test_complete_step(self):
        self.mode.complete_step(1, "test_concept")
        assert 1 in self.mode.progress.completed_steps
        assert "test_concept" in self.mode.progress.concepts_learned
    
    def test_get_next_action(self):
        action = self.mode.get_next_action()
        assert action["status"] == "in_progress"
        assert "step" in action
    
    def test_get_glossary(self):
        glossary = self.mode.get_glossary()
        assert len(glossary) > 0
        assert "term" in glossary[0]
    
    def test_search_glossary(self):
        results = self.mode.search_glossary("агент")
        assert len(results) > 0
    
    def test_get_progress_report(self):
        report = self.mode.get_progress_report()
        assert "completed" in report
        assert "total" in report
        assert "percent" in report


class TestModeSwitcher:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.switcher = ModeSwitcher(Path(self.temp_dir) / "mode.json")
    
    def test_default_mode(self):
        assert self.switcher.current_mode == "advanced"
    
    def test_get_config(self):
        config = self.switcher.get_config()
        assert config.name == "Продвинутый"
    
    def test_switch_mode(self):
        result = self.switcher.switch("simple")
        assert result["new_mode"] == "simple"
        assert self.switcher.current_mode == "simple"
    
    def test_get_available_modes(self):
        modes = self.switcher.get_available_modes()
        assert "simple" in modes
        assert "learning" in modes
        assert "advanced" in modes
    
    def test_switch_invalid(self):
        with pytest.raises(ValueError):
            self.switcher.switch("invalid_mode")
    
    def test_modes_config(self):
        assert MODES["simple"].parallel is False
        assert MODES["advanced"].parallel is True
        assert MODES["learning"].learning_mode is True
