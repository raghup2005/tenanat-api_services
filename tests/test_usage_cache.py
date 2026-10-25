
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from app.core.auth import get_current_tenant
from app.db.database import get_db
from app.main import app


def test_usage_endpoint_returns_cached_count(monkeypatch):
    tenant = SimpleNamespace(id=3001, daily_quota=100)

    fake_db = Mock()
    monkeypatch.setattr(
        "app.api.usage.get_cached_usage",
        lambda tenant_id, usage_date: 12,
    )
    set_cache = Mock()
    monkeypatch.setattr(
        "app.api.usage.set_cached_usage",
        set_cache,
    )

    app.dependency_overrides[get_current_tenant] = lambda: tenant
    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            response = client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == 3001
        assert data["requests_used"] == 12
        assert data["requests_remaining"] == 88

        # A cache hit should not query PostgreSQL for usage.
        fake_db.scalar.assert_not_called()
        set_cache.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_current_tenant, None)
        app.dependency_overrides.pop(get_db, None)


def test_usage_endpoint_reads_database_on_cache_miss(monkeypatch):
    tenant = SimpleNamespace(id=3002, daily_quota=100)
    usage_record = SimpleNamespace(request_count=7)

    fake_db = Mock()
    fake_db.scalar.return_value = usage_record
    set_cache = Mock()

    monkeypatch.setattr(
        "app.api.usage.get_cached_usage",
        lambda tenant_id, usage_date: None,
    )
    monkeypatch.setattr(
        "app.api.usage.set_cached_usage",
        set_cache,
    )

    app.dependency_overrides[get_current_tenant] = lambda: tenant
    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            response = client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == 3002
        assert data["requests_used"] == 7
        assert data["requests_remaining"] == 93

        fake_db.scalar.assert_called_once()
        set_cache.assert_called_once_with(
            3002,
            datetime.now(timezone.utc).date(),
            7,
        )
    finally:
        app.dependency_overrides.pop(get_current_tenant, None)
        app.dependency_overrides.pop(get_db, None)
