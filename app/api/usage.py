
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_tenant
from app.db.database import get_db
from app.models.tenant import Tenant
from app.models.usage import APIUsage
from app.schemas.usage import UsageResponse
from app.services.cache_service import (
    get_cached_usage,
    set_cached_usage,
)


router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("/me", response_model=UsageResponse)
def get_my_usage(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    today = datetime.now(timezone.utc).date()

    # 1. Try Redis first.
    requests_used = get_cached_usage(tenant.id, today)

    # 2. If Redis has no value, query PostgreSQL.
    if requests_used is None:
        usage = db.scalar(
            select(APIUsage).where(
                APIUsage.tenant_id == tenant.id,
                APIUsage.usage_date == today,
            )
        )

        requests_used = usage.request_count if usage else 0

        # 3. Store the count in Redis for subsequent requests.
        set_cached_usage(tenant.id, today, requests_used)

    # 4. Calculate the response using the current tenant quota.
    return UsageResponse(
        tenant_id=tenant.id,
        usage_date=today,
        requests_used=requests_used,
        daily_quota=tenant.daily_quota,
        requests_remaining=max(
            tenant.daily_quota - requests_used,
            0,
        ),
    )
