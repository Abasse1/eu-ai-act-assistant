from fastapi.testclient import TestClient

from ai_service.main import app


def test_liveness_returns_alive() -> None:

    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

def test_readiness_returns_ready() -> None:
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
