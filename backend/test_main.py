from fastapi.testclient import TestClient
from uuid import uuid4

from main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "ok"
        assert data["keys_configured"] >= 2
        assert data["cache_enabled"] is True


def test_empty_message():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "session_id": "test-session",
                "message": ""
            }
        )

        assert response.status_code == 422


def test_whitespace_message():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "session_id": "test-session",
                "message": "   "
            }
        )

        assert response.status_code == 422


def test_missing_session_id():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Hello"}
        )

        assert response.status_code == 422


def test_long_message():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "session_id": "test-session",
                "message": "a" * 4001
            }
        )

        assert response.status_code == 422


def test_invalid_session_id():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "session_id": "a" * 129,
                "message": "Hello"
            }
        )

        assert response.status_code == 422


def test_session_not_found():
    session_id = str(uuid4())

    with TestClient(app) as client:
        response = client.get(
            f"/sessions/{session_id}/messages"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "session not found"


def test_all_providers_unavailable():
    session_id = str(uuid4())

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={
                "X-Simulate-Failure": "*=429"
            },
            json={
                "session_id": session_id,
                "message": "Test provider failure"
            }
        )

        assert response.status_code == 503
        assert response.json()["detail"] == (
            "all providers unavailable"
        )

        history = client.get(
            f"/sessions/{session_id}/messages"
        )

        assert history.status_code == 404