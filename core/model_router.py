"""
Model Router v4.1 — маршрутизация LLM с кэшем, rate limiter и защитой от зацикливания
Версия: 4.1

Изменения vs 4.0:
- _should_fallback: время ответа больше НЕ является причиной fallback
  (локальная модель на 8GB VRAM может думать 30-60 сек — это нормально)
- Fallback только если ответ реально пустой или содержит явную ошибку
- Защита от зацикливания: каждый провайдер пробуется максимум 1 раз
- Если все провайдеры недоступны — понятное сообщение пользователю
- Новый метод get_fallback_message() для UI
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
            return ["groq", "deepseek", "google", "openrouter", "xai", "anthropic", "openai", "ollama"]
        if self.profile == "light":
            return ["groq", "deepseek", "google", "openrouter", "ollama"]
        elif self.profile == "medium":
            return ["ollama", "groq", "deepseek", "google", "openrouter", "xai"]
        else:
            return ["anthropic", "openai", "deepseek", "google", "xai", "ollama"]

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
    ) -> str:
        bm = beginner_mode if beginner_mode is not None else self.beginner_mode

        prompt_hash = self._hash_prompt(f"{prompt}:{bm}")
        cached = self.cache.get(prompt_hash)
        if cached:
            logger.debug(f"Кэш-попадение: {prompt_hash}")
            return cached

        if not self.rate_limiter.check_rate_limit():
            raise RuntimeError("Лимит запросов: 10 в минуту. Подождите.")

        self.rate_limiter.record_request()

        provider = self._get_available_provider()
        if not provider:
            raise RuntimeError(self.get_fallback_message())

        # Защита от зацикливания: храним уже опробованные провайдеры
        tried: List[str] = []
        last_error: Optional[Exception] = None
        fallback_triggered = False  # флаг: уже был один fallback

        while provider and provider not in tried:
            tried.append(provider)

            try:
                if bm:
                    from core.learning_mode import LearningMode
                    lm = LearningMode()
                    full_prompt = lm.generate_agent_prompt(
                        agent or "assistant", prompt, beginner_mode=True
                    )
                else:
                    full_prompt = prompt

                start_time = time.time()
                response = self._call_provider(provider, full_prompt, model)
                response_time = time.time() - start_time

                logger.info(f"Ответ от {provider} за {response_time:.1f}с")

                # Проверяем качество ответа только для ollama
                # и только если fallback ещё не был (защита от зацикливания)
                if provider == "ollama" and not fallback_triggered:
                    if self._should_fallback(response):
                        next_provider = self._get_next_provider(provider, tried)
                        if next_provider:
                            logger.info(
                                f"Ollama дала пустой/некачественный ответ → "
                                f"пробуем {next_provider}"
                            )
                            fallback_triggered = True
                            provider = next_provider
                            continue
                        else:
                            logger.warning(
                                "Ollama дала слабый ответ, облако недоступно — "
                                "возвращаем что есть"
                            )

                # Ответ принят
                self.cache.set(prompt_hash, response)
                return response

            except Exception as e:
                last_error = e
                logger.warning(f"Ошибка {provider}: {e}")

                next_provider = self._get_next_provider(provider, tried)
                if next_provider:
                    logger.info(f"Переключаемся на {next_provider}")
                    # Небольшая пауза перед следующей попыткой
                    time.sleep(BASE_BACKOFF)
                    provider = next_provider
                else:
                    break

        # Все провайдеры исчерпаны
        error_msg = self.get_fallback_message()
        logger.error(f"Провайдеры опробованы: {tried}. {error_msg}")
        raise RuntimeError(error_msg)

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
        elif provider == "anthropic":
            return self._generate_anthropic(prompt, model)
        elif provider == "openai":
            return self._generate_openai_compat(prompt, "openai", model)
        else:
            raise ValueError(f"Неизвестный провайдер: {provider}")

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
