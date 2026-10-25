
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.services.usage_service import (
    record_request_and_enforce_quota,
)


def make_tenant(daily_quota=3):
    return SimpleNamespace(
        id=1,
        daily_quota=daily_quota,
    )


def test_usage_increments_when_quota_is_available():
    db = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = 2
    db.execute.return_value = result

    request_count = record_request_and_enforce_quota(
        db,
        make_tenant(daily_quota=3),
    )

    assert request_count == 2
    db.execute.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_usage_rejects_request_when_quota_is_exhausted():
    db = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    with pytest.raises(HTTPException) as exc_info:
        record_request_and_enforce_quota(
            db,
            make_tenant(daily_quota=3),
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "Daily API quota exceeded."
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_usage_returns_503_when_database_fails():
    db = Mock()
    db.execute.side_effect = RuntimeError(
        "Database connection failed"
    )

    with pytest.raises(HTTPException) as exc_info:
        record_request_and_enforce_quota(
            db,
            make_tenant(daily_quota=3),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == (
        "Usage tracking service is unavailable."
    )
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
