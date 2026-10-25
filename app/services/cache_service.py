
import logging
from datetime import date

from redis import Redis

from app.core.config import settings


logger = logging.getLogger(__name__)

cache_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)

CACHE_TTL_SECONDS = 30


def _usage_cache_key(tenant_id: int, usage_date: date) -> str:
    return f"usage:tenant:{tenant_id}:{usage_date.isoformat()}"


def get_cached_usage(
    tenant_id: int,
    usage_date: date,
) -> int | None:
    """Return the cached request count, or None on a cache miss/failure."""
    try:
        value = cache_client.get(
            _usage_cache_key(tenant_id, usage_date)
        )
        return int(value) if value is not None else None
    except Exception:
        logger.warning("Redis usage-cache read failed", exc_info=True)
        return None


def set_cached_usage(
    tenant_id: int,
    usage_date: date,
    requests_used: int,
) -> None:
    """Cache a usage count temporarily. A cache failure is non-fatal."""
    try:
        cache_client.set(
            _usage_cache_key(tenant_id, usage_date),
            requests_used,
            ex=CACHE_TTL_SECONDS,
        )
    except Exception:
        logger.warning("Redis usage-cache write failed", exc_info=True)


def invalidate_usage_cache(
    tenant_id: int,
    usage_date: date,
) -> None:
    """Remove the cached usage count after a successful usage update."""
    try:
        cache_client.delete(
            _usage_cache_key(tenant_id, usage_date)
        )
    except Exception:
        logger.warning("Redis usage-cache invalidation failed", exc_info=True)
