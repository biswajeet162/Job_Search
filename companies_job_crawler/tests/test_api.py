import pytest
from fastapi.testclient import TestClient

from app.dependencies import reset_container
from app.main import create_app


@pytest.fixture
def client():
    reset_container()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    reset_container()


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_companies_endpoint(client: TestClient) -> None:
    response = client.get("/companies")
    assert response.status_code == 200
    data = response.json()
    assert "companies" in data
    assert len(data["companies"]) >= 1


def test_scheduler_status_endpoint(client: TestClient) -> None:
    response = client.get("/scheduler/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data
    assert data["running"] is True
