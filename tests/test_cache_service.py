
from datetime import date
from unittest.mock import Mock

from app.services import cache_service


def test_cache_key_is_scoped_by_tenant_and_date():
    first_date = date(2026, 10, 24)
    second_date = date(2026, 10, 25)

    key_a = cache_service._usage_cache_key(1, first_date)
    key_b = cache_service._usage_cache_key(2, first_date)
    key_c = cache_service._usage_cache_key(1, second_date)

    assert key_a != key_b
    assert key_a != key_c


def test_get_cached_usage_returns_cached_count(monkeypatch):
    fake_redis = Mock()
    fake_redis.get.return_value = "12"
    monkeypatch.setattr(cache_service, "cache_client", fake_redis)

    result = cache_service.get_cached_usage(
        1, date(2026, 10, 24)
    )

    assert result == 12


def test_get_cached_usage_returns_none_on_cache_miss(monkeypatch):
    fake_redis = Mock()
    fake_redis.get.return_value = None
    monkeypatch.setattr(cache_service, "cache_client", fake_redis)

    result = cache_service.get_cached_usage(
        1, date(2026, 10, 24)
    )

    assert result is None


def test_get_cached_usage_falls_back_when_redis_fails(monkeypatch):
    fake_redis = Mock()
    fake_redis.get.side_effect = ConnectionError("Redis unavailable")
    monkeypatch.setattr(cache_service, "cache_client", fake_redis)

    result = cache_service.get_cached_usage(
        1, date(2026, 10, 24)
    )

    assert result is None


def test_set_cached_usage_sets_ttl(monkeypatch):
    fake_redis = Mock()
    monkeypatch.setattr(cache_service, "cache_client", fake_redis)
    usage_date = date(2026, 10, 24)

    cache_service.set_cached_usage(1, usage_date, 12)

    fake_redis.set.assert_called_once_with(
        cache_service._usage_cache_key(1, usage_date),
        12,
        ex=cache_service.CACHE_TTL_SECONDS,
    )


def test_invalidate_usage_cache_deletes_key(monkeypatch):
    fake_redis = Mock()
    monkeypatch.setattr(cache_service, "cache_client", fake_redis)
    usage_date = date(2026, 10, 24)

    cache_service.invalidate_usage_cache(1, usage_date)

    fake_redis.delete.assert_called_once_with(
        cache_service._usage_cache_key(1, usage_date)
    )


def test_cache_write_failure_does_not_raise(monkeypatch):
    fake_redis = Mock()
    fake_redis.set.side_effect = ConnectionError("Redis unavailable")
    monkeypatch.setattr(cache_service, "cache_client", fake_redis)

    cache_service.set_cached_usage(
        1, date(2026, 10, 24), 12
    )
