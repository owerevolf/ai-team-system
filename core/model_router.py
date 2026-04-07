"""
Model Router v4 — маршрутизация LLM с кэшем, rate limiter и exponential backoff
Версия: 4.0
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
from functools import lru_cache
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

MAX_REQUESTS_PER_MIN = 10
CACHE_MAX_SIZE = 100
MAX_RETRIES = 3
BASE_BACKOFF = 1.0


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

    def check_rate_limit(self) -> bool:
        return self.rate_limiter.check_rate_limit()

    def get_cached(self, prompt_hash: str) -> Optional[str]:
        return self.cache.get(prompt_hash)

    def cache_set(self, prompt_hash: str, answer: str) -> None:
        self.cache.set(prompt_hash, answer)

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:12]

    def generate(self, prompt: str, agent: Optional[str] = None, model: Optional[str] = None, beginner_mode: Optional[bool] = None) -> str:
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
            raise RuntimeError("Нет доступных провайдеров! Настройте .env файл.")

        tried: List[str] = []
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            if not provider:
                break

            tried.append(provider)
            try:
                if bm:
                    from core.learning_mode import LearningMode
                    lm = LearningMode()
                    full_prompt = lm.generate_agent_prompt(agent or "assistant", prompt, beginner_mode=True)
                else:
                    full_prompt = prompt

                start_time = time.time()

                if provider == "groq":
                    response = self._generate_openai_compat(full_prompt, "groq", model)
                elif provider == "deepseek":
                    response = self._generate_openai_compat(full_prompt, "deepseek", model)
                elif provider == "google":
                    response = self._generate_google(full_prompt, model)
                elif provider == "openrouter":
                    response = self._generate_openai_compat(full_prompt, "openrouter", model)
                elif provider == "xai":
                    response = self._generate_openai_compat(full_prompt, "xai", model)
                elif provider == "ollama":
                    response = self._generate_ollama(full_prompt, model)
                elif provider == "anthropic":
                    response = self._generate_anthropic(full_prompt, model)
                elif provider == "openai":
                    response = self._generate_openai_compat(full_prompt, "openai", model)
                else:
                    raise ValueError(f"Неизвестный провайдер: {provider}")

                response_time = time.time() - start_time
                logger.info(f"Ответ от {provider} за {response_time:.1f}с")

                if provider == "ollama" and self._should_fallback(response, response_time):
                    logger.info("Локальная модель неуверенна → fallback на облако")
                    provider = self._get_next_provider(provider)
                    continue

                self.cache.set(prompt_hash, response)
                return response

            except Exception as e:
                last_error = e
                logger.warning(f"Ошибка {provider} (попытка {attempt + 1}): {e}")
                backoff = BASE_BACKOFF * (2 ** attempt)
                time.sleep(backoff)
                provider = self._get_next_provider(provider)
                continue

        raise RuntimeError(f"Все провайдеры не работают: {tried}. Последняя ошибка: {last_error}")

    def _should_fallback(self, response: str, response_time: float) -> bool:
        if not response:
            return True
        if response_time > 30:
            return True
        if len(response.split()) < 50:
            uncertain_patterns = [
                r"not sure", r"don't know", r"не уверен", r"не знаю",
                r"cannot determine", r"hard to say", r"возможно",
            ]
            for pattern in uncertain_patterns:
                if re.search(pattern, response.lower()):
                    return True
        return False

    def _get_next_provider(self, current: str) -> Optional[str]:
        try:
            idx = self.priority.index(current)
            for p in self.priority[idx + 1:]:
                if self.providers[p]["enabled"]:
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
            "options": {"num_ctx": 8192, "temperature": 0.7},
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
            "profile": self.profile,
            "beginner_mode": self.beginner_mode,
            "cache_size": len(self.cache._cache),
            "rate_limit_remaining": self.rate_limiter.max_requests - len(self.rate_limiter._requests),
        }
