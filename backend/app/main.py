"""FastAPI application entry point for TripPilot."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.services.trip_planner import TripPlanningError
# 所以“开发顺序”推荐从具体接口往外写，而“程序加载顺序”则从 main.py 开始。

def create_app() -> FastAPI:
    """Create and configure the TripPilot FastAPI application."""
    application = FastAPI(
        title="TripPilot API",
        description="基于 AMap、DeepSeek 和 LangGraph 的智能旅行规划接口",
        version="0.1.0",
    )
    settings = get_settings()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix="/api/v1")

    @application.exception_handler(TripPlanningError)
    async def handle_trip_planning_error(
        _request: Request,
        exc: TripPlanningError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": exc.messages},
        )

    @application.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
