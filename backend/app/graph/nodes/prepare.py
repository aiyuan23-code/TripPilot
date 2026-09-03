"""Request preparation node."""

from app.graph.state import TripState


async def prepare_request(state: TripState) -> TripState:
    """Initialize workflow bookkeeping after Pydantic request validation."""
    request = state["request"]
    return {
        "request": request,
        "errors": [],
        "validation_errors": [],
        "repair_count": 0,
    }

