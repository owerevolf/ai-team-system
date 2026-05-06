"""
Model Registry — парсинг и кэширование бесплатных моделей с провайдеров.

Провайдеры:
- OpenRouter (публичный API, без ключа)
- Ollama (локальный API, без ключа)
- OmniRoute (локальный API, без ключа)

Кэш: JSON файл, TTL 1 час.
"""

import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "model_registry.json"
CACHE_TTL = 3600  # 1 час


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    context_length: int = 0
    is_free: bool = True
    strength: str = "general"  # reasoning | coding | fast | strong | general
    description: str = ""


@dataclass
class ProviderInfo:
    id: str
    name: str
    url: str
    api_base: str
    requires_key: bool = False
    is_available: bool = False
    models: List[ModelInfo] = field(default_factory=list)
    signup_url: str = ""
    api_key_url: str = ""
    description: str = ""


# Статический список провайдеров с инструкциями
PROVIDERS_STATIC = {
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai",
        "api_base": "https://openrouter.ai/api/v1",
        "requires_key": True,
        "signup_url": "https://openrouter.ai/sign-up",
        "api_key_url": "https://openrouter.ai/keys",
        "description": "Единый API для 100+ моделей. Бесплатные модели доступны без подписки.",
    },
    "ollama": {
        "name": "Ollama (локальный)",
        "url": "https://ollama.com",
        "api_base": "http://localhost:11434",
        "requires_key": False,
        "signup_url": "https://ollama.com/download",
        "api_key_url": "",
        "description": "Локальные модели на твоём компьютере. Полностью бесплатно, работает оффлайн.",
    },
    "omniroute": {
        "name": "OmniRoute",
        "url": "https://omniroute.online",
        "api_base": "http://localhost:20128/v1",
        "requires_key": True,
        "signup_url": "https://omniroute.online/sign-up",
        "api_key_url": "https://omniroute.online/dashboard",
        "description": "Российский агрегатор AI моделей. Объединяет провайдеров в один API.",
    },
}


def _detector_strength(model_id: str, context_length: int) -> str:
    """Определяет 'силу' модели по имени и контексту."""
    mid = model_id.lower()
    if any(kw in mid for kw in ["r1", "reasoning", "o1", "o3", "think"]):
        return "reasoning"
    if any(kw in mid for kw in ["coder", "code", "dev", "programming"]):
        return "coding"
    if any(kw in mid for kw in ["flash", "lite", "nano", "small", "mini"]):
        return "fast"
    if context_length >= 200000:
        return "strong"
    return "general"


def _parse_openrouter_models() -> List[ModelInfo]:
    """Парсит бесплатные модели с OpenRouter API."""
    url = "https://openrouter.ai/api/v1/models"
    models = []

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AITeamSystem/2.0",
                "HTTP-Referer": "https://github.com/owerevolf/ai-team-system",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        for m in data.get("data", []):
            pid = m.get("id", "")
            pricing = m.get("pricing", {})
            prompt_p = pricing.get("prompt", "0")
            completion_p = pricing.get("completion", "0")

            # Бесплатная: price = "0" или ":free" в имени
            is_free = (
                (prompt_p == "0" and completion_p == "0")
                or ":free" in pid.lower()
            )

            if not is_free:
                continue

            ctx = m.get("context_length", 0) or m.get("context", 0) or 0
            name = m.get("name", pid) or pid

            models.append(ModelInfo(
                id=pid,
                name=name,
                provider="openrouter",
                context_length=ctx,
                is_free=True,
                strength=_detector_strength(pid, ctx),
                description=m.get("description", "")[:200],
            ))

        logger.info(f"OpenRouter: спарсено {len(models)} бесплатных моделей")

    except Exception as e:
        logger.warning(f"OpenRouter парсинг не удался: {e}")

    return models


def _parse_ollama_models() -> List[ModelInfo]:
    """Парсит локальные модели Ollama."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    models = []

    try:
        url = f"{base_url}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "AITeamSystem/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        for m in data.get("models", []):
            name = m.get("name", "")
            if not name:
                continue

            # Определяем размер ~контекст
            size_bytes = m.get("size", 0)
            # Примерная оценка контекста по размеру (очень грубо)
            ctx = 8192
            if size_bytes > 10_000_000_000:
                ctx = 131072
            elif size_bytes > 5_000_000_000:
                ctx = 65536
            elif size_bytes > 1_000_000_000:
                ctx = 32768

            models.append(ModelInfo(
                id=name,
                name=name,
                provider="ollama",
                context_length=ctx,
                is_free=True,
                strength=_detector_strength(name, ctx),
                description=f"Локальная модель ({size_bytes // 1_000_000_000}GB)",
            ))

        # Попробуем получить детали для каждой модели
        detailed = {}
        for m_name in [m.id for m in models]:
            try:
                detail_url = f"{base_url}/api/show"
                payload = json.dumps({"name": m_name}).encode()
                req2 = urllib.request.Request(
                    detail_url,
                    data=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "AITeamSystem/2.0"},
                    method="POST",
                )
                with urllib.request.urlopen(req2, timeout=5) as resp:
                    detail = json.loads(resp.read().decode())
                    # Ищем context_length в параметрах
                    params = str(detail.get("parameters", ""))
                    if "context_length" in params:
                        import re
                        match = re.search(r'context_length[=:\s]+(\d+)', params)
                        if match:
                            detailed[m_name] = int(match.group(1))
            except Exception:
                pass

        # Обновляем контекст из деталей
        for m in models:
            if m.id in detailed:
                m.context_length = detailed[m.id]

        logger.info(f"Ollama: спарсено {len(models)} локальных моделей")

    except Exception as e:
        logger.warning(f"Ollama парсинг не удался: {e}")

    return models


def _parse_omniroute_models() -> List[ModelInfo]:
    """Парсит модели OmniRoute."""
    base_url = os.getenv("OMNIROUTE_URL", "http://localhost:20128/v1")
    models = []

    try:
        url = f"{base_url}/models"
        req = urllib.request.Request(url, headers={"User-Agent": "AITeamSystem/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        for m in data.get("data", []):
            mid = m.get("id", "")
            if not mid:
                continue

            ctx = m.get("context_length", 0) or 8192

            models.append(ModelInfo(
                id=mid,
                name=mid,
                provider="omniroute",
                context_length=ctx,
                is_free=True,  # OmniRoute сам фильтрует
                strength=_detector_strength(mid, ctx),
                description="OmniRoute модель",
            ))

        logger.info(f"OmniRoute: спарсено {len(models)} моделей")

    except Exception as e:
        logger.warning(f"OmniRoute парсинг не удался: {e}")

    return models


def _load_cache() -> Optional[Dict]:
    """Загружает кэш если он свежий."""
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cached_at = data.get("_cached_at", 0)
        if time.time() - cached_at < CACHE_TTL:
            return data
        logger.info("Model registry cache expired")
    except Exception:
        pass
    return None


def _save_cache(data: Dict):
    """Сохраняет кэш."""
    data["_cached_at"] = time.time()
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def refresh(force: bool = False) -> Dict[str, ProviderInfo]:
    """
    Обновляет реестр моделей. Парсит всех доступных провайдеров.
    Возвращает словарь {provider_id: ProviderInfo}.
    """
    if not force:
        cached = _load_cache()
        if cached:
            return _deserialize_registry(cached)

    logger.info("Refreshing model registry...")

    registry: Dict[str, ProviderInfo] = {}

    # OpenRouter
    or_models = _parse_openrouter_models()
    or_info = ProviderInfo(
        id="openrouter",
        name=PROVIDERS_STATIC["openrouter"]["name"],
        url=PROVIDERS_STATIC["openrouter"]["url"],
        api_base=PROVIDERS_STATIC["openrouter"]["api_base"],
        requires_key=True,
        is_available=len(or_models) > 0,
        models=or_models,
        signup_url=PROVIDERS_STATIC["openrouter"]["signup_url"],
        api_key_url=PROVIDERS_STATIC["openrouter"]["api_key_url"],
        description=PROVIDERS_STATIC["openrouter"]["description"],
    )
    registry["openrouter"] = or_info

    # Ollama
    ol_models = _parse_ollama_models()
    ol_info = ProviderInfo(
        id="ollama",
        name=PROVIDERS_STATIC["ollama"]["name"],
        url=PROVIDERS_STATIC["ollama"]["url"],
        api_base=PROVIDERS_STATIC["ollama"]["api_base"],
        requires_key=False,
        is_available=len(ol_models) > 0,
        models=ol_models,
        signup_url=PROVIDERS_STATIC["ollama"]["signup_url"],
        api_key_url="",
        description=PROVIDERS_STATIC["ollama"]["description"],
    )
    registry["ollama"] = ol_info

    # OmniRoute
    om_models = _parse_omniroute_models()
    om_info = ProviderInfo(
        id="omniroute",
        name=PROVIDERS_STATIC["omniroute"]["name"],
        url=PROVIDERS_STATIC["omniroute"]["url"],
        api_base=PROVIDERS_STATIC["omniroute"]["api_base"],
        requires_key=True,
        is_available=len(om_models) > 0,
        models=om_models,
        signup_url=PROVIDERS_STATIC["omniroute"]["signup_url"],
        api_key_url=PROVIDERS_STATIC["omniroute"]["api_key_url"],
        description=PROVIDERS_STATIC["omniroute"]["description"],
    )
    registry["omniroute"] = om_info

    # Сохраняем кэш
    _save_cache(_serialize_registry(registry))

    total = sum(len(p.models) for p in registry.values())
    logger.info(f"Model registry refreshed: {total} models from {len(registry)} providers")

    return registry


def _serialize_registry(registry: Dict[str, ProviderInfo]) -> Dict:
    """Сериализует реестр в JSON-совместимый формат."""
    result = {}
    for pid, info in registry.items():
        result[pid] = {
            "id": info.id,
            "name": info.name,
            "url": info.url,
            "api_base": info.api_base,
            "requires_key": info.requires_key,
            "is_available": info.is_available,
            "signup_url": info.signup_url,
            "api_key_url": info.api_key_url,
            "description": info.description,
            "models": [asdict(m) for m in info.models],
        }
    return result


def _deserialize_registry(data: Dict) -> Dict[str, ProviderInfo]:
    """Десериализует реестр из JSON."""
    registry = {}
    for pid, info in data.items():
        if pid.startswith("_"):
            continue
        models = [ModelInfo(**m) for m in info.get("models", [])]
        registry[pid] = ProviderInfo(
            id=info["id"],
            name=info["name"],
            url=info["url"],
            api_base=info["api_base"],
            requires_key=info.get("requires_key", False),
            is_available=info.get("is_available", False),
            models=models,
            signup_url=info.get("signup_url", ""),
            api_key_url=info.get("api_key_url", ""),
            description=info.get("description", ""),
        )
    return registry


def get_free_models(
    provider: Optional[str] = None,
    strength: Optional[str] = None,
    min_context: int = 0,
) -> List[Dict]:
    """
    Возвращает список бесплатных моделей с фильтрами.
    
    Args:
        provider: фильтр по провайдеру (openrouter/ollama/omniroute)
        strength: фильтр по силе (reasoning/coding/fast/strong/general)
        min_context: минимальный контекст
    """
    registry = refresh()
    results = []

    for pid, info in registry.items():
        if provider and pid != provider:
            continue
        for m in info.models:
            if not m.is_free:
                continue
            if strength and m.strength != strength:
                continue
            if min_context and m.context_length < min_context:
                continue
            results.append({
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "context_length": m.context_length,
                "strength": m.strength,
                "description": m.description,
            })

    # Сортируем: сначала по силе (reasoning > coding > strong > general > fast), потом по контексту
    strength_order = {"reasoning": 0, "coding": 1, "strong": 2, "general": 3, "fast": 4}
    results.sort(key=lambda x: (strength_order.get(x["strength"], 5), -x["context_length"]))

    return results


def get_best_model_for_agent(agent_name: str) -> Optional[Dict]:
    """
    Возвращает лучшую бесплатную модель для конкретного агента.
    Использует маппинг скиллов.
    """
    from .agent_skills import AGENT_SKILL_MAP

    skill = AGENT_SKILL_MAP.get(agent_name)
    if not skill:
        return None

    preferred_strength = skill.get("preferred_strength", "general")
    min_context = skill.get("min_context", 32768)

    models = get_free_models(strength=preferred_strength, min_context=min_context)
    if models:
        return models[0]

    # Fallback: любая модель с достаточным контекстом
    models = get_free_models(min_context=min_context)
    if models:
        return models[0]

    # Совсем fallback: любая бесплатная
    models = get_free_models()
    return models[0] if models else None


if __name__ == "__main__":
    # Тест парсинга
    print("=== Testing Model Registry ===")
    registry = refresh(force=True)

    for pid, info in registry.items():
        print(f"\n{pid}: {len(info.models)} моделей (available: {info.is_available})")
        for m in info.models[:5]:
            print(f"  {m.id} [{m.strength}] ctx={m.context_length:,}")
        if len(info.models) > 5:
            print(f"  ... и ещё {len(info.models) - 5}")

    print("\n=== Best models for agents ===")
    for agent in ["teamlead", "architect", "backend", "frontend", "devops", "tester", "documentalist"]:
        best = get_best_model_for_agent(agent)
        if best:
            print(f"  {agent}: {best['id']} [{best['strength']}] ctx={best['context_length']:,}")
        else:
            print(f"  {agent}: НЕТ МОДЕЛИ")
