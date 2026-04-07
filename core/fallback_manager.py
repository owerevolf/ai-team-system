"""
Fallback Manager - Проактивное переключение на облако
Если локальная модель неуверена / медленная / задача сложная
"""

import re
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FallbackConfig:
    confidence_threshold: float = 0.5
    max_response_time: float = 30.0
    min_tokens: int = 50
    always_local: bool = False
    fallback_order: List[str] = field(default_factory=lambda: [
        "groq", "deepseek", "google", "openrouter", "xai"
    ])


@dataclass
class FallbackEvent:
    trigger: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: str = ""


class FallbackManager:
    UNCERTAIN_PATTERNS = [
        r"i'm not sure",
        r"i don't know",
        r"не уверен",
        r"не знаю",
        r"возможно",
        r"может быть",
        r"hard to say",
        r"cannot determine",
    ]
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self.history: List[FallbackEvent] = []
        self._cache: Dict[str, str] = {}
    
    def should_fallback(self, response: str, response_time: float, 
                       task_complexity: str = "medium") -> tuple[bool, str]:
        """Проверка нужно ли переключиться на облако"""
        if self.config.always_local:
            return False, ""
        
        response_lower = response.lower()
        
        if len(response) < self.config.min_tokens and task_complexity in ["hard", "complex"]:
            return True, "Слишком короткий ответ для сложной задачи"
        
        for pattern in self.UNCERTAIN_PATTERNS:
            if re.search(pattern, response_lower):
                return True, f"Модель неуверена: найдено '{pattern}'"
        
        if response_time > self.config.max_response_time:
            return True, f"Таймаут: {response_time:.1f}с > {self.config.max_response_time}с"
        
        return False, ""
    
    def get_fallback_provider(self) -> Optional[str]:
        """Получить следующий провайдер для fallback"""
        for provider in self.config.fallback_order:
            if self._is_provider_available(provider):
                return provider
        return None
    
    def _is_provider_available(self, provider: str) -> bool:
        """Проверка доступности провайдера"""
        import os
        key_map = {
            "groq": "GROQ_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "google": "GOOGLE_AI_STUDIO_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "xai": "XAI_API_KEY"
        }
        return bool(os.getenv(key_map.get(provider, "")))
    
    def record_fallback(self, from_provider: str, to_provider: str, reason: str):
        """Записать событие fallback"""
        self.history.append(FallbackEvent(
            trigger=f"{from_provider} → {to_provider}: {reason}"
        ))
    
    def get_cached_response(self, query: str) -> Optional[str]:
        """Получить кэшированный ответ"""
        import hashlib
        key = hashlib.md5(query[:200].encode()).hexdigest()
        return self._cache.get(key)
    
    def cache_response(self, query: str, response: str):
        """Кэшировать ответ"""
        import hashlib
        key = hashlib.md5(query[:200].encode()).hexdigest()
        self._cache[key] = response
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика fallback"""
        return {
            "total_fallbacks": len(self.history),
            "always_local": self.config.always_local,
            "recent_events": [h.trigger for h in self.history[-5:]]
        }
