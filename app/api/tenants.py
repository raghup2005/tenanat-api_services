
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.tenant import TenantCreate, TenantCreated
from app.services.tenant_service import create_tenant

from app.core.auth import get_current_tenant
from app.models.tenant import Tenant

from app.core.rate_limiter import enforce_rate_limit
from app.services.usage_service import record_request_and_enforce_quota


router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post(
    "",
    response_model=TenantCreated,
    status_code=status.HTTP_201_CREATED,
)
def register_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
):
    try:
        tenant, api_key = create_tenant(db, tenant_data)

        return TenantCreated(
            id=tenant.id,
            name=tenant.name,
            rate_limit_per_minute=tenant.rate_limit_per_minute,
            daily_quota=tenant.daily_quota,
            is_active=tenant.is_active,
            created_at=tenant.created_at,
            api_key=api_key,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tenant with this name already exists",
        ) from exc




@router.get("/me")
def get_my_tenant(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    # First, enforce the per-minute request limit.
    enforce_rate_limit(tenant)

    # Then, record the request and enforce the daily quota.
    request_count = record_request_and_enforce_quota(db, tenant)

    return {
        "id": tenant.id,
        "name": tenant.name,
        "rate_limit_per_minute": tenant.rate_limit_per_minute,
        "daily_quota": tenant.daily_quota,
        "is_active": tenant.is_active,
        "requests_used_today": request_count,
        "requests_remaining_today": max(
            tenant.daily_quota - request_count,
            0,
        ),
    }
