"""Smoke tests for the FastAPI app root and health endpoints."""

from fastapi.testclient import TestClient

from src.main import app


def test_health_when_called_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_when_called_redirects_to_docs() -> None:
    c = TestClient(app, follow_redirects=False)
    response = c.get("/")
    assert response.status_code in (307, 308)
    assert response.headers["location"] == "/docs"
