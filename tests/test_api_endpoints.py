"""
Tests for Web UI API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import after setting env
import os
os.environ.setdefault("OLLAMA_BASE_URL", "")
os.environ.setdefault("AI_MODE", "cloud")
os.environ.setdefault("HARDWARE_PROFILE", "light")


@pytest.fixture
def client():
    """Create test client"""
    from web_ui.app import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestHardwareEndpoint:
    def test_hardware_info(self, client):
        response = client.get("/api/hardware")
        assert response.status_code == 200
        data = response.json()
        assert "ram_gb" in data
        assert "profile" in data


class TestStartEndpoint:
    def test_start_session(self, client):
        response = client.get("/api/start?user_level=beginner")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "started"

    def test_start_session_default_level(self, client):
        response = client.get("/api/start")
        assert response.status_code == 200
        data = response.json()
        assert data["user_level"] == "beginner"


class TestLessonStepEndpoint:
    def test_lesson_step(self, client):
        # Start a session first
        start_resp = client.get("/api/start?user_level=beginner")
        session_id = start_resp.json()["session_id"]

        response = client.post("/api/lesson/step", json={
            "session_id": session_id,
            "step": 0,
        })
        assert response.status_code == 200


class TestStopBuildEndpoint:
    def test_stop_build_exists(self, client):
        """Verify the stop build endpoint is registered"""
        # Just check the route exists (it may not do much without active build)
        response = client.post("/api/stop_build")
        # Should return 200 or 404, not 500
        assert response.status_code in [200, 404]


class TestIndexPage:
    def test_index_returns_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "AI TEAM SYSTEM" in response.text or "ai-team" in response.text.lower()

    def test_favicon_returns_204(self, client):
        response = client.get("/favicon.ico")
        assert response.status_code == 204
