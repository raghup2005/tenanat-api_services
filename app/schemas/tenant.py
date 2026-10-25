
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    daily_quota: int = Field(default=10000, ge=1)


class TenantResponse(BaseModel):
    id: int
    name: str
    rate_limit_per_minute: int
    daily_quota: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantCreated(TenantResponse):
    api_key: str
