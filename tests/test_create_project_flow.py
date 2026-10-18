"""
Дымовой тест потока «Создать проект» (POST /api/create_project_stream).

Проверяет управляющий поток роута без вызова модели: роутер подменяется заглушкой.
Тест ловит два класса регрессий, которые уже случались в этом роуте:
  * вызывался несуществующий метод `manager.set_project_path` (AttributeError) — исправлено;
  * не был импортирован `AgentManager` (NameError) — поток обрывался, кнопка не работала.

Маркер xfail(strict=True) стоит потому, что вторую поломку нельзя исправить из кода:
`web_ui/app.py` блокирует фильтр записи. Правку вносит владелец по docs/SECURITY_FIX.md,
после чего маркер надо снять — иначе зелёный тест станет ошибкой.
"""

import pathlib

from fastapi.testclient import TestClient


class _FakeRouter:
    """Заглушка роутера: отвечает мгновенно и не создаёт файлов."""

    def __init__(self, *args, **kwargs):
        pass

    def generate(self, *args, **kwargs):
        return '{"status": "success", "files_created": [], "summary": "заглушка"}'


def test_create_project_stream_smoke(tmp_path, monkeypatch):
    import core.model_router as model_router
    from core import build_gates
    from web_ui.app import app

    monkeypatch.setattr(model_router, "ModelRouter", _FakeRouter)
    # Папку проектов уводим в tmp, чтобы тест не мусорил в домашнем каталоге
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))

    # Пауза между агентами ждёт человека до получаса: в тесте жмём «Дальше» сразу.
    async def always_continue(build_id, agent):
        return True

    monkeypatch.setattr(build_gates.gate, "wait_for_continue", always_continue)

    client = TestClient(app)
    with client.stream(
        "POST",
        "/api/create_project_stream",
        json={"project_name": "smoke_test", "query": "проверка потока", "level": "beginner"},
    ) as response:
        assert response.status_code == 200
        events = [line for line in response.iter_lines() if line.startswith("data:")]

    assert events, "SSE-поток пуст"
    assert any('"agent_start"' in e for e in events), "агенты не запускались"
    assert any('"type": "done"' in e for e in events), "поток не завершился событием done"
    assert any('"project_dir"' in e for e in events), "папка проекта не сообщена интерфейсу"
    # Проверка сборки целиком встроена в поток: без неё Тестер работает вслепую.
    assert any('"type": "build_check"' in e for e in events), "нет проверки сборки"
    assert any('"stage": "after_tester"' in e for e in events), "нет итога после Тестера"
