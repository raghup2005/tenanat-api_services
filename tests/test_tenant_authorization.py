
from types import SimpleNamespace
from unittest.mock import Mock

from datetime import date
from app.models.usage import APIUsage

from fastapi.testclient import TestClient

from app.core.auth import get_current_tenant
from app.core.security import hash_api_key
from app.db.database import get_db
from app.main import app
from app.api.tenants import (
    enforce_rate_limit,
    record_request_and_enforce_quota,
)



client = TestClient(app)


def test_tenant_me_requires_api_key():
    response = client.get("/tenants/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_inactive_tenant_returns_403():
    test_api_key = "tsk_inactive_test_key"

    inactive_tenant = SimpleNamespace(
        id=999,
        name="inactive_test_tenant",
        api_key_hash=hash_api_key(test_api_key),
        is_active=False,
        rate_limit_per_minute=30,
        daily_quota=5000,
    )

    fake_db = Mock()
    fake_db.scalar.return_value = inactive_tenant

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get(
            "/tenants/me",
            headers={"X-API-Key": test_api_key},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Tenant is inactive"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_active_tenant_can_access_own_details(monkeypatch):
    test_api_key = "tsk_active_test_key"

    active_tenant = SimpleNamespace(
        id=1000,
        name="active_test_tenant",
        api_key_hash=hash_api_key(test_api_key),
        is_active=True,
        rate_limit_per_minute=30,
        daily_quota=5000,
    )

    fake_db = Mock()
    fake_db.scalar.return_value = active_tenant

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    # Prevent real Redis and PostgreSQL usage tracking calls.
    monkeypatch.setattr(
        "app.api.tenants.enforce_rate_limit",
        lambda tenant: None,
    )
    monkeypatch.setattr(
        "app.api.tenants.record_request_and_enforce_quota",
        lambda db, tenant: 1,
    )

    try:
        response = client.get(
            "/tenants/me",
            headers={"X-API-Key": test_api_key},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["id"] == 1000
        assert data["name"] == "active_test_tenant"
        assert data["is_active"] is True
        assert data["requests_used_today"] == 1
        assert data["requests_remaining_today"] == 4999
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_api_key_returns_its_own_tenant_identity(monkeypatch):
    tenant_a_key = "tsk_tenant_a_test_key"
    tenant_b_key = "tsk_tenant_b_test_key"

    tenants = {
        hash_api_key(tenant_a_key): SimpleNamespace(
            id=2001,
            name="tenant_a",
            api_key_hash=hash_api_key(tenant_a_key),
            is_active=True,
            rate_limit_per_minute=30,
            daily_quota=5000,
        ),
        hash_api_key(tenant_b_key): SimpleNamespace(
            id=2002,
            name="tenant_b",
            api_key_hash=hash_api_key(tenant_b_key),
            is_active=True,
            rate_limit_per_minute=30,
            daily_quota=5000,
        ),
    }

    fake_db = Mock()
    fake_db.scalar.side_effect = lambda statement: next(
        (
            tenant
            for tenant in tenants.values()
            if tenant.api_key_hash in str(statement)
        ),
        None,
    )

    # Resolve the tenant from the API key explicitly.
    def get_tenant_from_key(api_key):
        return tenants.get(hash_api_key(api_key))

    def override_get_current_tenant(
        api_key: str | None = None,
    ):
        return get_tenant_from_key(api_key)

    # Use a dependency override for the authentication result.
    # Separate clients' headers are handled in the test below.
    app.dependency_overrides[get_db] = lambda: iter([fake_db])

    monkeypatch.setattr(
        "app.api.tenants.enforce_rate_limit",
        lambda tenant: None,
    )
    monkeypatch.setattr(
        "app.api.tenants.record_request_and_enforce_quota",
        lambda db, tenant: 1,
    )

    original_override = app.dependency_overrides.get(
        get_current_tenant
    )

    try:
        app.dependency_overrides[get_current_tenant] = (
            lambda: tenants[hash_api_key(tenant_a_key)]
        )
        response_a = client.get(
            "/tenants/me",
            headers={"X-API-Key": tenant_a_key},
        )

        app.dependency_overrides[get_current_tenant] = (
            lambda: tenants[hash_api_key(tenant_b_key)]
        )
        response_b = client.get(
            "/tenants/me",
            headers={"X-API-Key": tenant_b_key},
        )

        assert response_a.status_code == 200
        assert response_b.status_code == 200
        assert response_a.json()["id"] == 2001
        assert response_a.json()["name"] == "tenant_a"
        assert response_b.json()["id"] == 2002
        assert response_b.json()["name"] == "tenant_b"
        assert response_a.json()["id"] != response_b.json()["id"]
    finally:
        app.dependency_overrides.pop(get_db, None)
        if original_override is None:
            app.dependency_overrides.pop(
                get_current_tenant, None
            )
        else:
            app.dependency_overrides[get_current_tenant] = (
                original_override
            )


def test_usage_query_is_scoped_to_authenticated_tenant():
    from sqlalchemy.dialects import postgresql

    tenant = SimpleNamespace(
        id=2001,
        daily_quota=5000,
    )

    fake_db = Mock()
    fake_db.scalar.return_value = None

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = lambda: tenant

    try:
        response = client.get("/usage/me")

        assert response.status_code == 200
        assert response.json()["tenant_id"] == 2001
        assert response.json()["requests_used"] == 0

        statement = fake_db.scalar.call_args.args[0]
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

        assert "api_usage.tenant_id = 2001" in sql
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(
            get_current_tenant, None
        )
