from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.request_middleware import RequestLoggingMiddleware


def create_test_app():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    return app


def test_request_id_is_generated():
    client = TestClient(create_test_app())

    response = client.get("/test")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_existing_request_id_is_preserved():
    client = TestClient(create_test_app())

    response = client.get(
        "/test",
        headers={"X-Request-ID": "test-request-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_invalid_long_request_id_is_replaced():
    client = TestClient(create_test_app())

    response = client.get(
        "/test",
        headers={"X-Request-ID": "x" * 129},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "x" * 129
    assert len(response.headers["X-Request-ID"]) == 36