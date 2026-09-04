"""Trip-planning HTTP endpoints."""

from fastapi import APIRouter

from app.models import TripPlan, TripPlanRequest
from app.services.trip_planner import plan_trip


router = APIRouter(prefix="/trips", tags=["trips"])


@router.post(
    "/plan",
    response_model=TripPlan,
    summary="生成旅行计划",
)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    """Run the complete TripPilot graph and return its validated plan."""
    return await plan_trip(request)

