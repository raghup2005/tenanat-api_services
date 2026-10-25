
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.usage import APIUsage

from app.services.cache_service import invalidate_usage_cache


def record_request_and_enforce_quota(
    db: Session,
    tenant: Tenant,
) -> int:
    """Atomically record one request without exceeding the daily quota."""

    today = datetime.now(timezone.utc).date()

    statement = insert(APIUsage).values(
        tenant_id=tenant.id,
        usage_date=today,
        request_count=1,
    )

    statement = statement.on_conflict_do_update(
        constraint="uq_api_usage_tenant_date",
        set_={
            "request_count": APIUsage.request_count + 1,
        },
        where=APIUsage.request_count < tenant.daily_quota,
    ).returning(APIUsage.request_count)

    try:
        result = db.execute(statement)
        request_count = result.scalar_one_or_none()

        if request_count is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily API quota exceeded.",
            )

        db.commit()
        invalidate_usage_cache(tenant.id, today)
        return request_count

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Usage tracking service is unavailable.",
        ) from exc
