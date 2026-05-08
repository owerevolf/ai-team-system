"""
Tests for FallbackManager
"""

import pytest
from unittest.mock import patch
from core.fallback_manager import FallbackManager, FallbackConfig, FallbackEvent


class TestFallbackConfig:
    def test_defaults(self):
        config = FallbackConfig()
        assert config.confidence_threshold == 0.5
        assert config.max_response_time == 30.0
        assert config.min_tokens == 50
        assert config.always_local is False
        assert "openrouter" in config.fallback_order

    def test_custom(self):
        config = FallbackConfig(confidence_threshold=0.8, always_local=True)
        assert config.confidence_threshold == 0.8
        assert config.always_local is True


class TestFallbackManager:
    def setup_method(self):
        self.manager = FallbackManager()

    def test_no_fallback_for_good_response(self):
        response = "Here is a detailed answer with lots of content about the topic."
        should, reason = self.manager.should_fallback(response, response_time=5.0)
        assert should is False
        assert reason == ""

    def test_fallback_for_uncertain_response_english(self):
        response = "I'm not sure about this, maybe you should try something else."
        should, reason = self.manager.should_fallback(response, response_time=5.0)
        assert should is True
        assert "неуверена" in reason.lower() or "not sure" in reason.lower()

    def test_fallback_for_uncertain_response_russian(self):
        response = "Я не уверен, возможно это сложно определить."
        should, reason = self.manager.should_fallback(response, response_time=5.0)
        assert should is True

    def test_fallback_for_short_response_hard_task(self):
        response = "ok"
        should, reason = self.manager.should_fallback(
            response, response_time=5.0, task_complexity="hard"
        )
        assert should is True
        assert "короткий" in reason.lower() or "short" in reason.lower()

    def test_no_fallback_for_short_response_easy_task(self):
        response = "ok"
        should, reason = self.manager.should_fallback(
            response, response_time=5.0, task_complexity="easy"
        )
        assert should is False

    def test_fallback_for_slow_response(self):
        response = "Some response content here that is long enough."
        should, reason = self.manager.should_fallback(
            response, response_time=45.0
        )
        assert should is True
        assert "таймаут" in reason.lower() or "timeout" in reason.lower()

    def test_always_local_prevents_fallback(self):
        config = FallbackConfig(always_local=True)
        manager = FallbackManager(config)
        response = "I don't know"
        should, reason = manager.should_fallback(response, response_time=5.0)
        assert should is False
        assert reason == ""

    def test_get_fallback_provider_with_openrouter_key(self):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test"}):
            provider = self.manager.get_fallback_provider()
            assert provider is not None

    def test_get_fallback_provider_no_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove all provider keys
            for key in ["GROQ_API_KEY", "DEEPSEEK_API_KEY", "GOOGLE_AI_STUDIO_KEY",
                        "OPENROUTER_API_KEY", "XAI_API_KEY"]:
                import os
                os.environ.pop(key, None)
            provider = self.manager.get_fallback_provider()
            assert provider is None

    def test_record_fallback(self):
        self.manager.record_fallback("ollama", "openrouter", "timeout")
        assert len(self.manager.history) == 1
        assert self.manager.history[0].trigger == "ollama → openrouter: timeout"

    def test_cache_response(self):
        self.manager.cache_response("test query", "test response")
        cached = self.manager.get_cached_response("test query")
        assert cached == "test response"

    def test_cache_miss(self):
        cached = self.manager.get_cached_response("nonexistent query")
        assert cached is None

    def test_get_stats(self):
        self.manager.record_fallback("ollama", "openrouter", "test")
        stats = self.manager.get_stats()
        assert stats["total_fallbacks"] == 1
        assert "ollama → openrouter" in stats["recent_events"][0]

    def test_stats_empty_history(self):
        stats = self.manager.get_stats()
        assert stats["total_fallbacks"] == 0
        assert stats["recent_events"] == []

    def test_multiple_uncertain_patterns(self):
        """Test that various uncertain patterns trigger fallback"""
        patterns = [
            "I don't know the answer",
            "может быть это работает",
            "hard to say for sure",
            "cannot determine the exact approach",
        ]
        for pattern in patterns:
            manager = FallbackManager()
            should, _ = manager.should_fallback(pattern, response_time=5.0)
            assert should is True, f"Pattern '{pattern}' should trigger fallback"


class TestFallbackEvent:
    def test_creation(self):
        event = FallbackEvent(trigger="test trigger", details="some details")
        assert event.trigger == "test trigger"
        assert event.details == "some details"
        assert event.timestamp is not None
