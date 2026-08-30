from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.ai import subscribers
from app.api.router import api_router
from app.core.config import settings
from app.core.database import create_all, ping
from app.core.logging import configure_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)

logger = logging.getLogger("erp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("starting AI ERP %s env=%s provider=%s", __version__, settings.app_env,
                settings.ai_provider)
    if settings.auto_create_tables:
        create_all()
    subscribers.register()
    yield


app = FastAPI(
    title="AI ERP",
    version=__version__,
    description="AI-powered ERP — deterministic core with an AI intelligence layer above it.",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# Order matters: outermost first.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)

app.include_router(api_router)


@app.get("/", tags=["meta"])
def root():
    return {"name": "AI ERP", "version": __version__, "env": settings.app_env}


@app.get("/health/live", tags=["meta"])
def liveness():
    return {"status": "ok"}


@app.get("/health", tags=["meta"])
def readiness():
    db_ok = ping()
    body = {"status": "ok" if db_ok else "degraded", "database": db_ok, "version": __version__}
    return JSONResponse(body, status_code=200 if db_ok else 503)
