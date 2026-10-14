"""Единый клиент облачных ИИ с OpenAI-совместимым API: Qwen (DashScope), DeepSeek, Kimi.

Ключ читается только из окружения (.env) и никуда не сохраняется.
Имя заголовка авторизации берётся из общей константы проекта, чтобы не дублировать его
в двух местах.

Использование:
    from core.openai_compat import chat

    result = chat([{"role": "user", "content": "привет"}],
                  base_url="https://api.deepseek.com", model="deepseek-chat")
    print(result.ok, result.text or result.error)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
from urllib import error, request

from core.provider_probe import AUTH_HEADER_NAME

TIMEOUT_SECONDS = 60


@dataclass
class ChatResult:
    """Ответ облачной модели. ok=False — честная причина лежит в error."""

    ok: bool
    text: str = ""
    model: str = ""
    status: int = 0
    error: str = ""


def key_from_env(names: Sequence[str]) -> Optional[str]:
    """Ищет ключ в окружении по списку имён. Нет ключа — None, а не пустая строка."""
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return None


def build_headers(api_key: str) -> Dict[str, str]:
    """Заголовки запроса. Имя авторизационного заголовка — общая константа проекта."""
    return {"Content-Type": "application/json", AUTH_HEADER_NAME: "Bearer " + api_key}


def chat(
    messages: List[Dict[str, str]],
    *,
    base_url: str,
    model: str,
    key_names: Sequence[str] = ("DASHSCOPE_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY"),
    temperature: float = 0.7,
) -> ChatResult:
    """Один запрос к /chat/completions. Сеть или ключ подводят — возвращает причину, не падает."""
    api_key = key_from_env(key_names)
    if not api_key:
        return ChatResult(False, error="нет ключа: добавь в .env " + " или ".join(key_names))

    payload = {"model": model, "messages": messages, "temperature": temperature}
    req = request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=build_headers(api_key),
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        return ChatResult(False, status=exc.code, error=f"HTTP {exc.code}: {exc.reason}")
    except Exception as exc:  # noqa: BLE001 — сеть бывает разной, ломать чат из-за неё нельзя
        return ChatResult(False, error=f"сеть недоступна: {exc}")

    choices = data.get("choices") or []
    if not choices:
        return ChatResult(False, status=200, error="в ответе нет choices")
    message = choices[0].get("message") or {}
    return ChatResult(
        True,
        text=(message.get("content") or "").strip(),
        model=data.get("model") or model,
        status=200,
    )
