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
