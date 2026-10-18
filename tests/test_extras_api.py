"""
Тесты дополнительных эндпоинтов: словарь терминов и агент истины.

Роутер подключается в маленькое приложение — это быстрее, чем поднимать весь
`web_ui.app`, и не тянет за собой лишние зависимости.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web_ui.extras_api import router


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestGlossaryEndpoints:
    def test_returns_terms(self, client):
        response = client.get("/api/glossary")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 40
        assert any(item["term"] == "промпт" for item in data["terms"])

    def test_explains_known_term(self, client):
        response = client.get("/api/glossary/explain", params={"term": "коммит"})
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["term"]["explanation"].startswith("коммит —")

    def test_explains_by_alias(self, client):
        response = client.get("/api/glossary/explain", params={"term": "prompt"})
        assert response.json()["term"]["term"] == "промпт"

    def test_unknown_term_reported_honestly(self, client):
        response = client.get("/api/glossary/explain", params={"term": "не-термин"})
        assert response.status_code == 200
        assert response.json()["found"] is False


class TestTruthEndpoints:
    def test_ask_returns_facts_with_sources(self, client):
        response = client.post("/api/truth/ask", json={"question": "где определён get_agent_prompt"})
        assert response.status_code == 200
        data = response.json()
        assert data["found"] >= 1
        assert all(fact["source"] for fact in data["facts"])

    def test_ask_reports_no_data_instead_of_guessing(self, client):
        data = client.post("/api/truth/ask", json={"question": "расскажи про квазар"}).json()
        assert data["found"] == 0
        assert data["facts"] == []

    def test_ask_requires_question(self, client):
        assert client.post("/api/truth/ask", json={}).status_code == 400

    def test_verify_flags_invented_name(self, client):
        response = client.post("/api/truth/verify", json={"text": "вызови `create_magic_widget()`"})
        assert response.status_code == 200
        assert "create_magic_widget" in {item["name"] for item in response.json()["issues"]}

    def test_verify_requires_text(self, client):
        assert client.post("/api/truth/verify", json={}).status_code == 400


class TestTourEndpoint:
    def test_returns_steps_from_resource(self, client):
        response = client.get("/api/tour", params={"lang": "ru"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 9
        assert data["steps"][0]["title"]

    def test_missing_language_falls_back_to_russian(self, client):
        data = client.get("/api/tour", params={"lang": "de"}).json()
        assert data["total"] >= 9


class TestAskAgentEndpoint:
    def test_question_uses_project_folder(self, client, tmp_path, monkeypatch):
        """На паузе агент должен видеть проект, иначе «этот файл» ему неизвестен."""
        import core.agent_manager as agent_manager
        import core.model_router as model_router

        seen = {}

        class FakeRouter:
            def __init__(self, *args, **kwargs):
                pass

            def generate(self, prompt=None, agent=None):
                seen['prompt'] = prompt
                return 'ответ'

        class FakeManager:
            def __init__(self, router=None):
                self.model_router = router
                self.project_path = None

            def set_project_path(self, path):
                self.project_path = path

            def get_agent_prompt(self, agent, level):
                return 'ROLE'

            def _project_state_block(self):
                return 'TRUTH BLOCK'

        monkeypatch.setattr(model_router, 'ModelRouter', FakeRouter)
        monkeypatch.setattr(agent_manager, 'AgentManager', FakeManager)

        data = client.post('/api/agent/ask', json={
            'agent': 'architect',
            'question': 'зачем этот файл?',
            'level': 'zero',
            'project_dir': str(tmp_path),
        }).json()

        assert data == {'status': 'ok', 'agent': 'architect', 'answer': 'ответ'}
        assert 'TRUTH BLOCK' in seen['prompt']


class TestBuildCheckEndpoint:
    def test_refuses_folder_outside_projects(self, client, tmp_path, monkeypatch):
        import web_ui.extras_api as extras

        monkeypatch.setattr(extras, "_SESSIONS_DIR", tmp_path / "projects")
        (tmp_path / "outside").mkdir()

        response = client.post("/api/build/check", json={"path": str(tmp_path / "outside")})

        assert response.status_code == 403

    def test_reports_broken_import_of_the_project(self, client, tmp_path, monkeypatch):
        import web_ui.extras_api as extras

        root = tmp_path / "projects"
        project = root / "demo"
        project.mkdir(parents=True)
        (project / "main.py").write_text("import missing_local_module\n", encoding="utf-8")
        monkeypatch.setattr(extras, "_SESSIONS_DIR", root)

        data = client.post("/api/build/check", json={"path": str(project)}).json()

        assert data["ok"] is False
        assert any("missing_local_module" in error for error in data["errors"])

    def test_uses_latest_project_when_path_is_omitted(self, client, tmp_path, monkeypatch):
        import web_ui.extras_api as extras

        root = tmp_path / "projects"
        older = root / "older"
        newer = root / "newer"
        for folder in (older, newer):
            folder.mkdir(parents=True)
            (folder / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
        monkeypatch.setattr(extras, "_SESSIONS_DIR", root)

        data = client.post("/api/build/check", json={}).json()

        assert data["files"] >= 1
        assert data["project"].endswith(("older", "newer"))
