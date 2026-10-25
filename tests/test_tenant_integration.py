
from sqlalchemy import select

from app.db.database import Base
from app.models.tenant import Tenant
from uuid import uuid4


def test_register_tenant_persists_to_test_database(integration_client):
    print("DIAG: Sending tenant registration request", flush=True)
    tenant_name = f"integration_{uuid4().hex[:12]}"
    response = integration_client.post(
        "/tenants",
        json={
            "name": tenant_name,
            "rate_limit_per_minute": 10,
            "daily_quota": 100,
        },
    )
    print("DIAG: Registration response received", flush=True)

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == tenant_name
    assert data["rate_limit_per_minute"] == 10
    assert data["daily_quota"] == 100
    assert data["is_active"] is True
    assert data["api_key"].startswith("tsk_")

    # Verify the tenant was actually saved in the test database.
    # Use the same test database connection configured by the fixture.
    from os import getenv
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

   
    engine = create_engine(
    getenv("TEST_DATABASE_URL"),
    connect_args={"connect_timeout": 5},
)
    try:
        print("DIAG: Checking tenant in PostgreSQL", flush=True)
        with Session(engine) as db:
            tenant = db.scalar(
                select(Tenant).where(
                    Tenant.name == tenant_name
                )
            )

            assert tenant is not None
            assert tenant.api_key_hash != data["api_key"]
    finally:
        engine.dispose()


def test_registered_api_key_authenticates_its_tenant(integration_client):
    tenant_name = f"auth_integration_{uuid4().hex[:12]}"

    registration = integration_client.post(
        "/tenants",
        json={
            "name": tenant_name,
            "rate_limit_per_minute": 10,
            "daily_quota": 100,
        },
    )

    assert registration.status_code == 201
    data = registration.json()
    api_key = data["api_key"]

    response = integration_client.get(
        "/tenants/me",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200

    profile = response.json()
    assert profile["id"] == data["id"]
    assert profile["name"] == tenant_name
    assert profile["requests_used_today"] == 1
    assert profile["requests_remaining_today"] == 99


def test_daily_quota_is_enforced(integration_client):
    tenant_name = f"quota_integration_{uuid4().hex[:12]}"

    registration = integration_client.post(
        "/tenants",
        json={
            "name": tenant_name,
            "rate_limit_per_minute": 100,
            "daily_quota": 2,
        },
    )

    assert registration.status_code == 201
    api_key = registration.json()["api_key"]

    headers = {"X-API-Key": api_key}

    # The first two requests should succeed.
    first = integration_client.get("/tenants/me", headers=headers)
    second = integration_client.get("/tenants/me", headers=headers)

    assert first.status_code == 200
    assert first.json()["requests_used_today"] == 1

    assert second.status_code == 200
    assert second.json()["requests_used_today"] == 2

    # The third request must exceed the daily quota.
    third = integration_client.get("/tenants/me", headers=headers)

    assert third.status_code == 429
    assert third.json()["detail"] == "Daily API quota exceeded."


def test_rate_limit_is_enforced(integration_client):
    tenant_name = f"rate_limit_integration_{uuid4().hex[:12]}"

    registration = integration_client.post(
        "/tenants",
        json={
            "name": tenant_name,
            "rate_limit_per_minute": 2,
            "daily_quota": 100,
        },
    )

    assert registration.status_code == 201

    api_key = registration.json()["api_key"]
    headers = {"X-API-Key": api_key}

    # The first two requests should succeed.
    first = integration_client.get("/tenants/me", headers=headers)
    second = integration_client.get("/tenants/me", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200

    # The third request should exceed the per-minute limit.
    third = integration_client.get("/tenants/me", headers=headers)

    assert third.status_code == 429
    assert third.json()["detail"] == (
        "Rate limit exceeded. Try again later."
    )
    assert third.headers["retry-after"]=="60"
