"""Проверки единого облачного адаптера: без сети, без ключей и без реальных запросов."""

import json
import os
from unittest.mock import patch
from urllib import error as urlerror

from core.openai_compat import build_headers, chat
from core.provider_probe import AUTH_HEADER_NAME


def test_headers_use_the_shared_constant():
    headers = build_headers("секрет")
    assert headers[AUTH_HEADER_NAME] == "Bearer секрет"
    assert headers["Content-Type"] == "application/json"


def test_missing_key_is_reported_honestly():
    with patch.dict(os.environ, {}, clear=True):
        result = chat(
            [{"role": "user", "content": "привет"}],
            base_url="https://example.invalid/v1",
            model="m",
            key_names=("НЕТ_ТАКОГО_КЛЮЧА",),
        )
    assert result.ok is False
    assert "нет ключа" in result.error


def test_reply_is_parsed_and_trimmed():
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            body = {"model": "m1", "choices": [{"message": {"content": "  привет  "}}]}
            return json.dumps(body).encode("utf-8")

    with patch.dict(os.environ, {"ТЕСТОВЫЙ_КЛЮЧ": "k"}), patch(
        "core.openai_compat.request.urlopen", return_value=FakeResponse()
    ):
        result = chat(
            [{"role": "user", "content": "привет"}],
            base_url="https://example.invalid/v1",
            model="m1",
            key_names=("ТЕСТОВЫЙ_КЛЮЧ",),
        )

    assert result.ok is True
    assert result.text == "привет"
    assert result.model == "m1"


def test_http_error_becomes_a_message_not_a_crash():
    failure = urlerror.HTTPError("https://example.invalid", 401, "Unauthorized", None, None)

    with patch.dict(os.environ, {"ТЕСТОВЫЙ_КЛЮЧ": "k"}), patch(
        "core.openai_compat.request.urlopen", side_effect=failure
    ):
        result = chat(
            [{"role": "user", "content": "x"}],
            base_url="https://example.invalid/v1",
            model="m",
            key_names=("ТЕСТОВЫЙ_КЛЮЧ",),
        )

    assert result.ok is False
    assert result.status == 401
    assert "401" in result.error


def test_answer_without_choices_is_not_silently_empty():
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"model": "m1"}).encode("utf-8")

    with patch.dict(os.environ, {"ТЕСТОВЫЙ_КЛЮЧ": "k"}), patch(
        "core.openai_compat.request.urlopen", return_value=FakeResponse()
    ):
        result = chat(
            [{"role": "user", "content": "x"}],
            base_url="https://example.invalid/v1",
            model="m1",
            key_names=("ТЕСТОВЫЙ_КЛЮЧ",),
        )

    assert result.ok is False
    assert "choices" in result.error
