"""
Тесты безопасности: валидатор команд терминала и закрытые опасные роуты.

Появились после аудита 14.10.2026: валидатор пропускал цепочки команд
(`&&`, `;`, `|`), произвольный `python -c`, `git push` и `find . -delete`,
а роуты `/api/developer/terminal` и `/api/developer/execute` были доступны
без всякой авторизации. Сервер при этом мог слушать 0.0.0.0, а CORS был `*`.
"""

import pytest

from core.project_manager.runtime.developer.developer_terminal import DeveloperTerminal


class TestTerminalValidation:
    """Одна команда без склеек; опасные формы отклоняются."""

    @pytest.mark.parametrize("command", [
        "echo a && echo b",
        "echo a ; echo b",
        "echo a | grep b",
        "ls > out.txt",
        "ls `whoami`",
        "echo $(whoami)",
        "cat a & cat b",
    ])
    def test_chains_and_redirects_blocked(self, command):
        cmd = DeveloperTerminal().validate_command(command)
        assert cmd.allowed is False
        assert "Dangerous" in cmd.block_reason

    @pytest.mark.parametrize("command", [
        'python -c "print(1)"',
        "python -i",
        "git push origin main",
        "git config user.name someone",
        "git remote set-url origin https://example.invalid",
        "git branch -D main",
        "find . -delete",
        "pip install requests",
        "npm install some-package",
        "npx some-tool",
    ])
    def test_dangerous_arguments_blocked(self, command):
        cmd = DeveloperTerminal().validate_command(command)
        assert cmd.allowed is False

    @pytest.mark.parametrize("command", [
        "ls -la",
        "cat README.md",
        "git status",
        "git diff",
        "git log --oneline -5",
        "python --version",
        "python -m pytest tests -q",
        "pytest -v",
        "pip list",
        "find . -name '*.py'",
    ])
    def test_normal_commands_allowed(self, command):
        cmd = DeveloperTerminal().validate_command(command)
        assert cmd.allowed is True, cmd.block_reason


class TestDangerousRoutesDisabled:
    """Опасные роуты по умолчанию выключены и включаются только флагом."""

    def test_terminal_route_forbidden_without_flag(self, monkeypatch):
        from fastapi.testclient import TestClient
        from web_ui.app import app

        monkeypatch.delenv("AITEAM_DEV_EXEC", raising=False)
        client = TestClient(app)
        response = client.post("/api/developer/terminal", params={"command": "ls"})
        assert response.status_code == 403

    def test_execute_route_forbidden_without_flag(self, monkeypatch):
        from fastapi.testclient import TestClient
        from web_ui.app import app

        monkeypatch.delenv("AITEAM_DEV_EXEC", raising=False)
        client = TestClient(app)
        response = client.post(
            "/api/developer/execute",
            json={"title": "t", "objective": "o"},
        )
        assert response.status_code == 403


class TestCorsIsLocalOnly:
    """CORS не должен разрешать все источники и не должен слать credentials."""

    def test_cors_origins_are_local(self):
        from starlette.middleware.cors import CORSMiddleware
        from web_ui.app import app

        entries = [m for m in app.user_middleware if getattr(m, "cls", None) is CORSMiddleware]
        assert entries, "CORSMiddleware не найден"

        kwargs = getattr(entries[0], "kwargs", {}) or {}
        origins = kwargs.get("allow_origins", [])
        assert "*" not in origins, f"CORS разрешает все источники: {origins}"
        assert kwargs.get("allow_credentials") is False
