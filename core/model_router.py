"""
Model Router v5.0 — мульти-провайдер маршрутизация с поддержкой agent Skills.

Изменения vs 4.1:
- Поддержка выбора конкретного провайдера и модели для каждого агента
- Интеграция с agent_skills.py — автоматический выбор модели по роли агента
- Интеграция с model_registry.py — парсинг бесплатных моделей
- Параллельная работа с разных провайдеров для разных агентов
- OpenRouter, Ollama, OmniRoute как основные провайдеры
"""

import os
import re
import json
import time
import hashlib
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List
from collections import OrderedDict
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

MAX_REQUESTS_PER_MIN = 10
CACHE_MAX_SIZE = 100
MAX_RETRIES = 3
BASE_BACKOFF = 1.0

# Минимальная длина ответа чтобы считать его валидным
MIN_RESPONSE_LENGTH = 20


class RateLimiter:
    def __init__(self, max_requests: int = MAX_REQUESTS_PER_MIN, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: List[float] = []

    def check_rate_limit(self) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests = [t for t in self._requests if t > cutoff]
        return len(self._requests) < self.max_requests

    def record_request(self) -> None:
        self._requests.append(time.time())


class ResponseCache:
    def __init__(self, max_size: int = CACHE_MAX_SIZE) -> None:
        self.max_size = max_size
        self._cache: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> Optional[str]:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = value

    def clear(self) -> None:
        self._cache.clear()


class ModelRouter:
    def __init__(self, profile: str = "medium", beginner_mode: bool = False) -> None:
        self.profile = profile
        self.beginner_mode = beginner_mode
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self.providers = self._init_providers()
        self.priority = self._get_priority()
        self.rate_limiter = RateLimiter()
        self.cache = ResponseCache()

    def _init_providers(self) -> Dict[str, Dict[str, Any]]:
        return {
            "groq": {
                "enabled": bool(os.getenv("GROQ_API_KEY")),
                "api_key": os.getenv("GROQ_API_KEY", ""),
                "base_url": "https://api.groq.com/openai/v1",
                "models": ["llama-3.3-70b-versatile", "qwen-3.5-32b", "llama-3.1-8b-instant"],
            },
            "deepseek": {
                "enabled": bool(os.getenv("DEEPSEEK_API_KEY")),
                "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                "base_url": "https://api.deepseek.com",
                "models": ["deepseek-chat", "deepseek-coder"],
            },
            "google": {
                "enabled": bool(os.getenv("GOOGLE_AI_STUDIO_KEY")),
                "api_key": os.getenv("GOOGLE_AI_STUDIO_KEY", ""),
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "models": ["gemini-2.0-flash", "gemini-2.5-flash"],
            },
            "openrouter": {
                "enabled": bool(os.getenv("OPENROUTER_API_KEY")),
                "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                "base_url": "https://openrouter.ai/api/v1",
                "models": ["deepseek/deepseek-r1:free", "qwen/qwen3-32b"],
            },
            "xai": {
                "enabled": bool(os.getenv("XAI_API_KEY")),
                "api_key": os.getenv("XAI_API_KEY", ""),
                "base_url": "https://api.x.ai/v1",
                "models": ["grok-4", "grok-2"],
            },
            "ollama": {
                "enabled": self._check_ollama(),
                "base_url": self.ollama_base_url,
                "models": [self.ollama_model],
            },
            "omniroute": {
                "enabled": bool(os.getenv("OMNIROUTE_API_KEY")),
                "api_key": os.getenv("OMNIROUTE_API_KEY", ""),
                "base_url": os.getenv("OMNIROUTE_URL", "http://localhost:20128/v1"),
                "models": ["auto"],
            },
            "anthropic": {
                "enabled": bool(os.getenv("ANTHROPIC_API_KEY")),
                "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
                "models": ["claude-3-5-sonnet-20241022"],
            },
            "openai": {
                "enabled": bool(os.getenv("OPENAI_API_KEY")),
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "models": ["gpt-4o", "gpt-4o-mini"],
            },
        }

    def _check_ollama(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self.ollama_base_url}/api/tags",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    def _get_priority(self) -> List[str]:
        mode = os.getenv("AI_MODE", "local")
        if mode == "cloud":
            return ["openrouter", "ollama", "omniroute", "google", "anthropic", "openai"]
        # local-first: Ollama → OpenRouter (free models) → OmniRoute → облако
        return ["ollama", "openrouter", "omniroute", "google", "anthropic", "openai"]

    def _get_available_provider(self) -> Optional[str]:
        for provider in self.priority:
            if self.providers[provider]["enabled"]:
                return provider
        return None

    def _has_cloud_fallback(self) -> bool:
        """Проверяем есть ли хоть один облачный провайдер с ключом"""
        cloud_providers = ["groq", "deepseek", "google", "openrouter", "xai", "anthropic", "openai"]
        return any(self.providers[p]["enabled"] for p in cloud_providers)

    def get_fallback_message(self) -> str:
        """Сообщение для UI когда все провайдеры не справились"""
        if self._has_cloud_fallback():
            return (
                "⚠️ Локальная модель не справилась с задачей, "
                "но облачный провайдер тоже не ответил. "
                "Попробуй позже или упрости запрос."
            )
        return (
            "⚠️ Локальная модель не справилась с задачей. "
            "Облачные провайдеры не настроены. "
            "Добавь API-ключ в .env (например GROQ_API_KEY — бесплатно) "
            "чтобы система могла обратиться за помощью в облако."
        )

    def check_rate_limit(self) -> bool:
        return self.rate_limiter.check_rate_limit()

    def get_cached(self, prompt_hash: str) -> Optional[str]:
        return self.cache.get(prompt_hash)

    def cache_set(self, prompt_hash: str, answer: str) -> None:
        self.cache.set(prompt_hash, answer)

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:12]

    def generate(
        self,
        prompt: str,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        beginner_mode: Optional[bool] = None,
        provider: Optional[str] = None,
    ) -> str:
        """
        Генерация ответа с поддержкой мульти-провайдера.
        
        Args:
            prompt: промпт
            agent: имя агента (teamlead, architect, backend, ...)
            model: конкретная модель (опционально)
            beginner_mode: режим новичка
            provider: конкретный провайдер (опционально)
        """
        bm = beginner_mode if beginner_mode is not None else self.beginner_mode

        prompt_hash = self._hash_prompt(f"{prompt}:{bm}:{provider}:{model}")
        cached = self.cache.get(prompt_hash)
        if cached:
            logger.debug(f"Кэш-попадение: {prompt_hash}")
            return cached

        if not self.rate_limiter.check_rate_limit():
            raise RuntimeError("Лимит запросов: 10 в минуту. Подождите.")

        self.rate_limiter.record_request()

        # Определяем провайдера и модель
        target_provider = provider
        target_model = model

        # Если указан агент но не указан провайдер/модель — берём из agent_skills
        if agent and not provider:
            from .agent_skills import AGENT_SKILL_MAP
            skill = AGENT_SKILL_MAP.get(agent, {})
            target_model = target_model or self._get_agent_model(agent)
            # Определяем провайдер по модели
            if target_model:
                target_provider = self._resolve_provider_for_model(target_model)

        # Если всё ещё нет провайдера — берём из приоритета
        if not target_provider:
            target_provider = self._get_available_provider()

        if not target_provider:
            raise RuntimeError(self.get_fallback_message())

        # Пробуем целевой провайдер, потом fallback по цепочке
        tried: List[str] = []
        last_error: Optional[Exception] = None

        # Строим цепочку: сначала целевой, потом остальные по приоритету
        chain = [target_provider] + [p for p in self.priority if p != target_provider]

        for prov in chain:
            if prov in tried:
                continue
            if not self.providers.get(prov, {}).get("enabled", False):
                continue

            tried.append(prov)

            try:
                # Для Ollama — модель из конфига или дефолтная
                actual_model = target_model
                if prov == "ollama" and not actual_model:
                    actual_model = self.ollama_model

                response = self._call_provider(prov, prompt, actual_model)

                if self._should_fallback(response):
                    logger.warning(f"{prov}: слабый ответ, fallback")
                    last_error = RuntimeError(f"Слабый ответ от {prov}")
                    continue

                self.cache.set(prompt_hash, response)
                logger.info(f"Ответ от {prov}" + (f"/{actual_model}" if actual_model else ""))
                return response

            except Exception as e:
                last_error = e
                logger.warning(f"Ошибка {prov}: {e}")
                continue

        # Все провайдеры исчерпаны
        error_msg = self.get_fallback_message()
        logger.error(f"Провайдеры опробованы: {tried}. {error_msg}")
        raise RuntimeError(error_msg)

    def _get_agent_model(self, agent: str) -> Optional[str]:
        """Получает модель для агента из model_registry."""
        try:
            from .model_registry import get_best_model_for_agent
            best = get_best_model_for_agent(agent)
            if best:
                return best["id"]
        except Exception as e:
            logger.warning(f"Не удалось получить модель для {agent}: {e}")
        return None

    def _resolve_provider_for_model(self, model_id: str) -> Optional[str]:
        """Определяет провайдер по ID модели."""
        # OpenRouter модели содержат /
        if "/" in model_id and not model_id.startswith("ollama/"):
            return "openrouter"
        # Ollama модели начинаются с ollama/ или содержат :
        if model_id.startswith("ollama/"):
            return "ollama"
        if ":" in model_id and "/" not in model_id:
            return "ollama"
        # OmniRoute
        if model_id.startswith("omniroute/"):
            return "omniroute"
        # По умолчанию openrouter
        return "openrouter"

    def _call_provider(self, provider: str, prompt: str, model: Optional[str]) -> str:
        """Вызов конкретного провайдера. Без retry — retry делает generate()."""
        if provider == "groq":
            return self._generate_openai_compat(prompt, "groq", model)
        elif provider == "deepseek":
            return self._generate_openai_compat(prompt, "deepseek", model)
        elif provider == "google":
            return self._generate_google(prompt, model)
        elif provider == "openrouter":
            return self._generate_openai_compat(prompt, "openrouter", model)
        elif provider == "xai":
            return self._generate_openai_compat(prompt, "xai", model)
        elif provider == "ollama":
            return self._generate_ollama(prompt, model)
        elif provider == "omniroute":
            return self._generate_omniroute(prompt, model)
        elif provider == "anthropic":
            return self._generate_anthropic(prompt, model)
        elif provider == "openai":
            return self._generate_openai_compat(prompt, "openai", model)
        else:
            raise ValueError(f"Неизвестный провайдер: {provider}")

    def _generate_omniroute(self, prompt: str, model: Optional[str] = None) -> str:
        """Генерация через OmniRoute (OpenAI-совместимый API)."""
        base_url = os.getenv("OMNIROUTE_URL", "http://localhost:20128/v1")
        api_key = os.getenv("OMNIROUTE_API_KEY", "")

        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("Установите openai: pip install openai")

        client = OpenAI(
            api_key=api_key or "sk-omniroute",
            base_url=base_url,
        )

        model_name = model or "auto"

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _should_fallback(self, response: str) -> bool:
        """
        Нужен ли fallback на облако?

        ВАЖНО: время ответа НЕ является критерием.
        Локальная модель на 8GB VRAM может думать 30-60 сек — это нормально.
        Fallback только если ответ реально пустой или слишком короткий.
        """
        if not response:
            return True
        if len(response.strip()) < MIN_RESPONSE_LENGTH:
            return True
        return False

    def _get_next_provider(self, current: str, already_tried: List[str]) -> Optional[str]:
        """Следующий доступный провайдер которого ещё не пробовали"""
        try:
            idx = self.priority.index(current)
            for p in self.priority[idx + 1:]:
                if self.providers[p]["enabled"] and p not in already_tried:
                    return p
        except ValueError:
            pass
        return None

    def _generate_openai_compat(self, prompt: str, provider: str, model: Optional[str] = None) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("Установите openai: pip install openai")

        cfg = self.providers[provider]
        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        model_name = model or cfg["models"][0]

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _generate_deepseek(self, prompt: str, model: Optional[str] = None) -> str:
        return self._generate_openai_compat(prompt, "deepseek", model)

    def _generate_google(self, prompt: str, model: Optional[str] = None) -> str:
        model_name = model or "gemini-2.0-flash"
        api_key = self.providers["google"]["api_key"]
        url = f"{self.providers['google']['base_url']}/models/{model_name}:generateContent?key={api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]

    def _generate_ollama(self, prompt: str, model: Optional[str] = None) -> str:
        model_name = model or self.ollama_model
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 8192,       # контекст входа
                "num_predict": 4096,   # лимит выходных токенов — без этого модель обрезает ответ
                "temperature": 0.7,
            },
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama недоступна: {e}")

    def _generate_anthropic(self, prompt: str, model: Optional[str] = None) -> str:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise RuntimeError("Установите anthropic: pip install anthropic")

        client = Anthropic(api_key=self.providers["anthropic"]["api_key"])
        model_name = model or self.providers["anthropic"]["models"][0]

        message = client.messages.create(
            model=model_name,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def list_models(self) -> Dict[str, List[str]]:
        models: Dict[str, List[str]] = {}
        for name, config in self.providers.items():
            if config["enabled"]:
                if name == "ollama":
                    try:
                        req = urllib.request.Request(
                            f"{self.ollama_base_url}/api/tags",
                            headers={"Content-Type": "application/json"},
                        )
                        with urllib.request.urlopen(req, timeout=5) as response:
                            data = json.loads(response.read().decode("utf-8"))
                            models[name] = [m["name"] for m in data.get("models", [])]
                    except Exception:
                        models[name] = config["models"]
                else:
                    models[name] = config["models"]
        return models

    def get_status(self) -> Dict[str, Any]:
        return {
            "active_provider": self._get_available_provider(),
            "available_providers": [n for n, c in self.providers.items() if c["enabled"]],
            "has_cloud_fallback": self._has_cloud_fallback(),
            "profile": self.profile,
            "beginner_mode": self.beginner_mode,
            "cache_size": len(self.cache._cache),
            "rate_limit_remaining": self.rate_limiter.max_requests - len(self.rate_limiter._requests),
        }
