
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate


def create_tenant(db: Session, tenant_data: TenantCreate):
    existing_tenant = db.scalar(
        select(Tenant).where(Tenant.name == tenant_data.name)
    )

    if existing_tenant:
        raise ValueError("A tenant with this name already exists")

    api_key = generate_api_key()

    tenant = Tenant(
        name=tenant_data.name,
        api_key_hash=hash_api_key(api_key),
        rate_limit_per_minute=tenant_data.rate_limit_per_minute,
        daily_quota=tenant_data.daily_quota,
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant, api_key
