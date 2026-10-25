
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_api_key
from app.db.database import get_db
from app.models.tenant import Tenant


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def get_current_tenant(
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> Tenant:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    api_key_hash = hash_api_key(api_key)

    tenant = db.scalar(
        select(Tenant).where(
            Tenant.api_key_hash == api_key_hash
        )
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive",
        )

    return tenant
