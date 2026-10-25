
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.core.rate_limiter import enforce_rate_limit


def test_rate_limit_allows_requests_within_limit(monkeypatch):
    tenant = SimpleNamespace(
        id=1,
        rate_limit_per_minute=3,
    )

    redis_mock = Mock()
    redis_mock.incr.return_value = 2

    monkeypatch.setattr(
        "app.core.rate_limiter.redis_client",
        redis_mock,
    )

    enforce_rate_limit(tenant)

    redis_mock.incr.assert_called_once()
    redis_mock.expire.assert_not_called()


def test_rate_limit_rejects_requests_over_limit(monkeypatch):
    tenant = SimpleNamespace(
        id=1,
        rate_limit_per_minute=3,
    )

    redis_mock = Mock()
    redis_mock.incr.return_value = 4

    monkeypatch.setattr(
        "app.core.rate_limiter.redis_client",
        redis_mock,
    )

    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(tenant)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == (
        "Rate limit exceeded. Try again later."
    )
    assert exc_info.value.headers["Retry-After"] == "60"


def test_rate_limiter_returns_503_when_redis_fails(monkeypatch):
    tenant = SimpleNamespace(
        id=1,
        rate_limit_per_minute=3,
    )

    redis_mock = Mock()
    redis_mock.incr.side_effect = ConnectionError(
        "Redis connection failed"
    )

    monkeypatch.setattr(
        "app.core.rate_limiter.redis_client",
        redis_mock,
    )

    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(tenant)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == (
        "Rate-limiting service is unavailable"
    )


def test_new_rate_limit_counter_expires_after_65_seconds(monkeypatch):
    tenant = SimpleNamespace(id=1, rate_limit_per_minute=3)
    redis_mock = Mock()
    redis_mock.incr.return_value = 1

    monkeypatch.setattr(
        "app.core.rate_limiter.redis_client",
        redis_mock,
    )

    enforce_rate_limit(tenant)

    redis_key = redis_mock.incr.call_args.args[0]
    redis_mock.expire.assert_called_once_with(redis_key, 65)


def test_existing_rate_limit_counter_does_not_reset_expiration(monkeypatch):
    tenant = SimpleNamespace(id=1, rate_limit_per_minute=3)
    redis_mock = Mock()
    redis_mock.incr.return_value = 2

    monkeypatch.setattr(
        "app.core.rate_limiter.redis_client",
        redis_mock,
    )

    enforce_rate_limit(tenant)

    redis_mock.incr.assert_called_once()
    redis_mock.expire.assert_not_called()
