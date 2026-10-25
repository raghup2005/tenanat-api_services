
import uuid
from datetime import date

import pytest

from app.services import cache_service


@pytest.fixture
def isolated_cache_key():
    """Generate a unique tenant ID and clean up its test key."""
    tenant_id = int(uuid.uuid4().int % 1_000_000_000) + 1
    usage_date = date.today()

    key = cache_service._usage_cache_key(
        tenant_id, usage_date
    )

    cache_service.cache_client.delete(key)

    yield tenant_id, usage_date, key

    cache_service.cache_client.delete(key)


def test_real_redis_can_store_and_retrieve_usage(
    isolated_cache_key,
):
    tenant_id, usage_date, key = isolated_cache_key

    cache_service.set_cached_usage(
        tenant_id, usage_date, 12
    )

    assert cache_service.cache_client.get(key) == "12"
    assert cache_service.get_cached_usage(
        tenant_id, usage_date
    ) == 12


def test_real_redis_expires_cached_usage(
    isolated_cache_key, monkeypatch
):
    tenant_id, usage_date, key = isolated_cache_key

    monkeypatch.setattr(
        cache_service,
        "CACHE_TTL_SECONDS",
        1,
    )

    cache_service.set_cached_usage(
        tenant_id, usage_date, 8
    )

    assert cache_service.cache_client.get(key) == "8"

    assert cache_service.cache_client.ttl(key) in (0, 1)

    import time
    time.sleep(1.1)

    assert cache_service.cache_client.get(key) is None
    assert cache_service.get_cached_usage(
        tenant_id, usage_date
    ) is None


def test_real_redis_invalidation_deletes_usage(
    isolated_cache_key,
):
    tenant_id, usage_date, key = isolated_cache_key

    cache_service.set_cached_usage(
        tenant_id, usage_date, 15
    )

    assert cache_service.cache_client.get(key) == "15"

    cache_service.invalidate_usage_cache(
        tenant_id, usage_date
    )

    assert cache_service.cache_client.get(key) is None
    assert cache_service.get_cached_usage(
        tenant_id, usage_date
    ) is None
