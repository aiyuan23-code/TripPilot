"""Join node for the parallel research branches."""

from app.graph.state import TripState


async def collect_results(state: TripState) -> TripState:
    """Wait for all research branches without changing their merged state."""
    return {}

