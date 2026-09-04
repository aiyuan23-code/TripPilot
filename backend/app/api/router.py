"""Top-level API router that combines all endpoint groups."""

from fastapi import APIRouter

from app.api.routes.trips import router as trips_router


api_router = APIRouter()
api_router.include_router(trips_router)

