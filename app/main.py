from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.ai import subscribers
from app.api.router import api_router
from app.core.config import settings
from app.core.database import create_all
from app.core.exceptions import ERPError
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.auto_create_tables:
        create_all()
    subscribers.register()
    yield


app = FastAPI(
    title="AI ERP",
    version=__version__,
    description="AI-powered ERP backend — deterministic ERP core with an AI intelligence layer above it.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "AI ERP",
        "version": __version__,
        "docs": "/docs",
        "ai_provider": settings.ai_provider,
    }


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
