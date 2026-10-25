
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.db.database import Base, get_db
from app.main import app


@pytest.fixture
def integration_client():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.fail(
            "TEST_DATABASE_URL is not set. "
            "Point it to tenant_api_test_db before running integration tests."
        )

    if "tenant_api_test_db" not in database_url:
        pytest.fail(
            "Safety check failed: integration tests must use "
            "tenant_api_test_db."
        )

    test_engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout":5},
    )

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    print("DIAG: Starting test database schema setup", flush=True)

    Base.metadata.create_all(bind=test_engine)

    print("DIAG: Test database schema setup complete", flush=True)

    previous_overrides = app.dependency_overrides.copy()

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        test_engine.dispose()

