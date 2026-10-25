
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_schema_contains_expected_endpoints():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    paths = schema["paths"]

    assert "/tenants" in paths
    assert "post" in paths["/tenants"]

    assert "/tenants/me" in paths
    assert "get" in paths["/tenants/me"]

    assert "/usage/me" in paths
    assert "get" in paths["/usage/me"]

    assert "/health" in paths
    assert "get" in paths["/health"]


def test_openapi_documents_api_key_authentication():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    schemes = schema["components"]["securitySchemes"]

    assert "APIKeyHeader" in schemes
    assert schemes["APIKeyHeader"]["type"] == "apiKey"
    assert schemes["APIKeyHeader"]["in"] == "header"
    assert schemes["APIKeyHeader"]["name"] == "X-API-Key"


def test_missing_api_key_error_includes_request_id():
    response = client.get("/tenants/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert len(request_id) == 36


def test_client_request_id_is_returned_on_auth_error():
    request_id = "contract-test-request-123"

    response = client.get(
        "/tenants/me",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == request_id
