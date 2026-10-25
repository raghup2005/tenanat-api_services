
from datetime import date

from pydantic import BaseModel, ConfigDict


class UsageResponse(BaseModel):
    tenant_id: int
    usage_date: date
    requests_used: int
    daily_quota: int
    requests_remaining: int

    model_config = ConfigDict(from_attributes=True)
