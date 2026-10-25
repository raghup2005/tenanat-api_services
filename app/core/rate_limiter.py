
from fastapi import HTTPException, status
from redis import Redis

from app.core.config import settings
from app.models.tenant import Tenant


redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def enforce_rate_limit(tenant: Tenant) -> None:
    """
    Enforce a fixed-window request limit for a tenant.
    The counter is shared through Redis.
    """
    window_seconds = 60
    current_window = int(__import__("time").time()) // window_seconds

    redis_key = (
        f"rate_limit:tenant:{tenant.id}:{current_window}"
    )

    try:
        count = redis_client.incr(redis_key)

        if count == 1:
            redis_client.expire(redis_key, window_seconds + 5)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate-limiting service is unavailable",
        ) from exc

    if count > tenant.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(window_seconds)},
        )
