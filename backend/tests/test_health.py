from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "3d-print-farm-backend"


def test_openapi_docs_accessible(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200


def test_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/api/nonexistent")

    assert response.status_code == 404
