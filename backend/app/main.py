"""BuildPulse API application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging

setup_logging()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="BuildPulse",
        description="Engineering Intelligence Platform for C++ projects.",
        version=settings.api_version,
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get("/")
    def root() -> dict:
        return {"service": settings.app_name, "docs": "/docs", "version": settings.api_version}

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
