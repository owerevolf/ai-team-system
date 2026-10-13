"""
Каталог источников моделей, пробники доступности и состояние провайдеров.

Зачем: список бесплатных сервисов устаревает быстро, а часть из них недоступна из РФ
(OpenRouter — живой пример). Поэтому статус источника не «зашит» в код, а **измеряется**
пробником и сохраняется вместе с датой проверки.

Что делает модуль:
* держит каталог источников (бесплатные/локальные/платные, где взять ключ);
* проверяет доступность каждого включённого источника лёгким запросом;
* сохраняет результат в `.cache/providers_state.json` (файл машинный, в git не попадает);
* никогда не сохраняет и не печатает сами ключи — только статус.

Пример:
    python -m core.provider_probe
    from core.provider_probe import probe_all, save_state
"""

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / ".cache" / "providers_state.json"


@dataclass
class ProviderProbe:
    """Результат проверки одного источника."""

    provider: str
    available: bool = False
    status: Optional[int] = None
    latency_ms: Optional[int] = None
    checked_at: str = ""
    note: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Каталог источников ───────────────────────────────────────────────────────
# kind: local | aggregator | cloud     cost: free | paid
# reachable_from_ru: yes | no | unknown — это НЕ гарантия, а подсказка для человека
PROVIDER_CATALOG: Dict[str, Dict] = {
    "ollama": {
        "name": "Ollama (локально)",
        "kind": "local",
        "cost": "free",
        "needs_key": False,
        "reachable_from_ru": "yes",
        "how": "Установить Ollama и скачать модель: ollama pull qwen3:8b",
        "signup": "https://ollama.com/download",
        "models_url": "/api/tags",
    },
    "openai_compat": {
        "name": "OpenAI-совместимый адрес (свой шлюз)",
        "kind": "aggregator",
        "cost": "free",
        "needs_key": False,
        "reachable_from_ru": "yes",
        "how": "Задай OPENAI_COMPAT_BASE_URL и OPENAI_COMPAT_MODEL в .env",
        "signup": "",
        "models_url": "/models",
    },
    "omniroute": {
        "name": "OmniRoute (локальный шлюз бесплатных тарифов)",
        "kind": "aggregator",
        "cost": "free",
        "needs_key": False,
        "reachable_from_ru": "yes",
        "how": "npm install -g omniroute && omniroute (слушает localhost:20128)",
        "signup": "https://omniroute.online",
        "models_url": "/models",
    },
    "groq": {
        "name": "Groq",
        "kind": "cloud",
        "cost": "free",
        "needs_key": True,
        "reachable_from_ru": "unknown",
        "how": "Бесплатный тариф, ключ в .env как GROQ_API_KEY",
        "signup": "https://console.groq.com/keys",
        "base_url": "https://api.groq.com/openai/v1",
        "models_url": "/models",
    },
    "google": {
        "name": "Google AI Studio (Gemini)",
        "kind": "cloud",
        "cost": "free",
        "needs_key": True,
        "reachable_from_ru": "unknown",
        "how": "Бесплатный тариф, ключ в .env как GOOGLE_AI_STUDIO_KEY",
        "signup": "https://aistudio.google.com/app/apikey",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models_url": "/models",
    },
    "deepseek": {
        "name": "DeepSeek",
        "kind": "cloud",
        "cost": "paid",
        "needs_key": True,
        "reachable_from_ru": "yes",
        "how": "Ключ в .env как DEEPSEEK_API_KEY",
        "signup": "https://platform.deepseek.com",
        "base_url": "https://api.deepseek.com",
        "models_url": "/models",
    },
    "openrouter": {
        "name": "OpenRouter",
        "kind": "cloud",
        "cost": "free",
        "needs_key": True,
        "reachable_from_ru": "no",
        "how": "С 27.06.2026 не обслуживает российские аккаунты и IP",
        "signup": "https://openrouter.ai/keys",
        "base_url": "https://openrouter.ai/api/v1",
        "models_url": "/models",
    },
    "xai": {
        "name": "xAI (Grok)",
        "kind": "cloud",
        "cost": "paid",
        "needs_key": True,
        "reachable_from_ru": "unknown",
        "how": "Ключ в .env как XAI_API_KEY",
        "signup": "https://console.x.ai",
        "base_url": "https://api.x.ai/v1",
        "models_url": "/models",
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "kind": "cloud",
        "cost": "paid",
        "needs_key": True,
        "reachable_from_ru": "no",
        "how": "Ключ в .env как ANTHROPIC_API_KEY",
        "signup": "https://console.anthropic.com",
        "base_url": "",
        "models_url": "",
    },
    "openai": {
        "name": "OpenAI",
        "kind": "cloud",
        "cost": "paid",
        "needs_key": True,
        "reachable_from_ru": "no",
        "how": "Ключ в .env как OPENAI_API_KEY",
        "signup": "https://platform.openai.com/api-keys",
        "base_url": "https://api.openai.com/v1",
        "models_url": "/models",
    },
}

# Какие переменные окружения включают источник
PROVIDER_KEY_ENV: Dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "google": "GOOGLE_AI_STUDIO_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "xai": "XAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def catalogue_for_ui() -> List[Dict]:
    """Каталог для интерфейса: что это, сколько стоит, где взять, доступно ли из РФ."""
    rows = []
    for provider_id, info in PROVIDER_CATALOG.items():
        rows.append({
            "id": provider_id,
            "name": info["name"],
            "kind": info["kind"],
            "cost": info["cost"],
            "needs_key": info["needs_key"],
            "reachable_from_ru": info["reachable_from_ru"],
            "how": info["how"],
            "signup": info["signup"],
            "check_env": PROVIDER_KEY_ENV.get(provider_id, ""),
        })
    return rows


def _request(url: str, headers: Optional[Dict] = None, timeout: int = 8):
    request = urllib.request.Request(url, headers=headers or {})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(64 * 1024)
        latency = int((time.perf_counter() - started) * 1000)
        return response.status, body, latency


def probe_ollama(base_url: Optional[str] = None, timeout: int = 5) -> ProviderProbe:
    """Локальная Ollama: проверяем, что сервис отвечает и сколько в нём моделей."""
    base = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
    try:
        status, body, latency = _request(f"{base}/api/tags", timeout=timeout)
        models = json.loads(body.decode("utf-8")).get("models", [])
        return ProviderProbe(
            provider="ollama",
            available=True,
            status=status,
            latency_ms=latency,
            checked_at=_now(),
            note=f"моделей: {len(models)}" + ("" if models else " — нужна хотя бы одна: ollama pull qwen3:8b"),
        )
    except Exception as exc:  # noqa: BLE001 — нужен любой сбой сети/сервиса
        return ProviderProbe(
            provider="ollama", available=False, checked_at=_now(),
            note=f"не отвечает: {type(exc).__name__}. Запусти Ollama",
        )


def probe_http_provider(provider_id: str, env: Optional[Dict] = None) -> ProviderProbe:
    """
    Проверяет облачный источник: есть ли ключ и принимает ли его сервис.

    Ключ нигде не сохраняется — только результат проверки.
    """
    env = env if env is not None else os.environ
    info = PROVIDER_CATALOG.get(provider_id, {})
    env_name = PROVIDER_KEY_ENV.get(provider_id, "")

    if provider_id == "openai_compat":
        base = (env.get("OPENAI_COMPAT_BASE_URL") or "").rstrip("/")
        if not base:
            return ProviderProbe(provider_id, note="не настроен: нет OPENAI_COMPAT_BASE_URL", checked_at=_now())
        key = env.get("OPENAI_COMPAT_API_KEY", "")
    elif provider_id == "omniroute":
        base = (env.get("OMNIROUTE_URL") or "http://localhost:20128/v1").rstrip("/")
        key = env.get("OMNIROUTE_API_KEY", "")
    else:
        base = (info.get("base_url") or "").rstrip("/")
        key = env.get(env_name, "") if env_name else ""

    if info.get("needs_key") and not key:
        return ProviderProbe(provider_id, note=f"нет ключа: {env_name}", checked_at=_now())
    if not base:
        return ProviderProbe(provider_id, note="не задан адрес сервиса", checked_at=_now())

    url = f"{base}{info.get('models_url') or ''}"
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        status, _body, latency = _request(url, headers=headers)
        return ProviderProbe(
            provider=provider_id, available=200 <= status < 300, status=status,
            latency_ms=latency, checked_at=_now(), note="ключ принят" if 200 <= status < 300 else "",
        )
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            note = "ключ не принят (401/403)"
        else:
            note = f"ответ сервиса: {exc.code}"
        return ProviderProbe(provider_id, available=False, status=exc.code, checked_at=_now(), note=note)
    except Exception as exc:  # noqa: BLE001
        return ProviderProbe(
            provider_id, available=False, checked_at=_now(),
            note=f"нет связи: {type(exc).__name__} (возможно, блокировка по региону)",
        )


def probe_all(env: Optional[Dict] = None) -> Dict[str, Dict]:
    """Проверяет все источники каталога и возвращает состояние по каждому."""
    env = env if env is not None else os.environ
    state: Dict[str, Dict] = {}

    state["ollama"] = probe_ollama(env.get("OLLAMA_BASE_URL") if env is not None else None).to_dict()

    for provider_id in PROVIDER_CATALOG:
        if provider_id == "ollama":
            continue
        state[provider_id] = probe_http_provider(provider_id, env).to_dict()

    return state


def free_available(state: Dict[str, Dict]) -> List[str]:
    """Бесплатные и доступные прямо сейчас источники — их и стоит пробовать первыми."""
    result = []
    for provider_id, probe in state.items():
        info = PROVIDER_CATALOG.get(provider_id, {})
        if info.get("cost") == "free" and probe.get("available"):
            result.append(provider_id)
    return result


def save_state(state: Dict[str, Dict], path: Optional[Path] = None) -> Path:
    target = Path(path) if path else STATE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"checked_at": _now(), "providers": state}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def load_state(path: Optional[Path] = None) -> Dict[str, Dict]:
    target = Path(path) if path else STATE_FILE
    if not target.exists():
        return {}
    data = json.loads(target.read_text(encoding="utf-8"))
    return data.get("providers", {})


if __name__ == "__main__":
    state = probe_all()
    saved = save_state(state)
    for provider_id, probe in state.items():
        mark = "OK " if probe.get("available") else "-- "
        print(f"{mark}{provider_id:14} {probe.get('note', '')}")
    print(f"\nСостояние сохранено: {saved}")
