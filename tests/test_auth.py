
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_missing_api_key_returns_401():
    response = client.get("/tenants/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_invalid_api_key_returns_401():
    response = client.get(
        "/tenants/me",
        headers={"X-API-Key": "tsk_invalid_test_key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"
