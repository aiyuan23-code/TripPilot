"""Service layer connecting HTTP requests to the TripPilot LangGraph."""

from functools import lru_cache
from typing import Any

from pydantic import ValidationError

from app.graph import build_trip_graph
from app.models import TripPlan, TripPlanRequest


class TripPlanningError(RuntimeError):
    """Raised when the graph cannot produce a usable travel plan."""

    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("; ".join(messages))


@lru_cache(maxsize=1)
def get_trip_graph() -> Any:
    """Build the graph once and reuse the compiled workflow across requests."""
    return build_trip_graph()


async def plan_trip(
    request: TripPlanRequest,
    *,
    graph: Any | None = None,
) -> TripPlan:
    """Execute the graph and return only a validated final TripPlan."""
    active_graph = graph if graph is not None else get_trip_graph()
    try:
        result = await active_graph.ainvoke({"request": request})
    except Exception as exc:
        raise TripPlanningError(["旅行规划服务执行失败，请稍后重试。"]) from exc

    graph_errors = [str(error) for error in result.get("errors", []) if error]
    if graph_errors:
        raise TripPlanningError(graph_errors)

    validation_errors = [
        str(error) for error in result.get("validation_errors", []) if error
    ]
    if validation_errors:
        raise TripPlanningError(validation_errors)

    output = result.get("trip_plan")
    if output is None:
        raise TripPlanningError(["旅行规划流程没有生成 TripPlan。"])

    try:
        return TripPlan.model_validate(output)
    except ValidationError as exc:
        raise TripPlanningError(["旅行计划响应结构不合法。"]) from exc
