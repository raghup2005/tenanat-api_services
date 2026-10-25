
from fastapi import FastAPI
from app.api.tenants import router as tenants_router
from app.api.usage import router as usage_router

import logging

from app.core.request_middleware import RequestLoggingMiddleware

app = FastAPI(
    title="Multi-Tenant API Service",
    description=(
        "A secure API platform with tenant authentication, "
        "rate limiting, usage quotas, and caching."
    ),
    version="0.1.0",
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app.add_middleware(RequestLoggingMiddleware)
app.include_router(tenants_router)
app.include_router(usage_router)

@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Multi-Tenant API Service",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "tenant-api-service",
    }
