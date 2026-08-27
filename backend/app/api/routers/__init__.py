"""API router registry."""

from fastapi import APIRouter

from app.api.routers import analytics, builds, projects

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(builds.router)
api_router.include_router(analytics.router)
