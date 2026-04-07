"""
Tests for ModelRouter
"""

import pytest
from unittest.mock import patch, Mock

from core.model_router import ModelRouter


class TestModelRouter:
    def test_init_default(self):
        router = ModelRouter()
        
        assert router.profile == "medium"
        assert "ollama" in router.providers
    
    def test_init_light_profile(self):
        router = ModelRouter(profile="light")
        
        assert router.profile == "light"
        assert "groq" in router.priority
    
    def test_init_heavy_profile(self):
        router = ModelRouter(profile="heavy")
        
        assert router.profile == "heavy"
        assert router.priority[0] in ["anthropic", "openai"]
    
    def test_ollama_disabled_when_not_running(self):
        with patch('core.model_router.ModelRouter._check_ollama', return_value=False):
            router = ModelRouter()
            assert router.providers["ollama"]["enabled"] is False
    
    def test_get_available_provider_no_providers(self):
        with patch('core.model_router.ModelRouter._check_ollama', return_value=False):
            router = ModelRouter()
            for p in router.providers:
                router.providers[p]["enabled"] = False
            
            result = router._get_available_provider()
            assert result is None
    
    def test_get_status(self):
        with patch('core.model_router.ModelRouter._check_ollama', return_value=True):
            router = ModelRouter()
            status = router.get_status()
            
            assert "active_provider" in status
            assert "available_providers" in status
            assert "profile" in status


class TestGroqIntegration:
    def test_groq_enabled_with_key(self):
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            router = ModelRouter()
            assert router.providers["groq"]["enabled"] is True
    
    def test_groq_disabled_without_key(self):
        with patch.dict('os.environ', {}, clear=True):
            router = ModelRouter()
            assert router.providers["groq"]["enabled"] is False


class TestDeepSeekIntegration:
    def test_deepseek_enabled_with_key(self):
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}):
            router = ModelRouter()
            assert router.providers["deepseek"]["enabled"] is True
    
    def test_deepseek_disabled_without_key(self):
        with patch.dict('os.environ', {}, clear=True):
            router = ModelRouter()
            assert router.providers["deepseek"]["enabled"] is False
