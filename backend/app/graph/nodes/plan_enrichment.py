"""Enrich only POIs selected in the final itinerary."""

from typing import Any

from app.graph.nodes.poi import (
    parse_amap_cost,
    parse_amap_poi_detail,
    poi_detail_updates,
)
from app.graph.state import TripState
from app.models.trip import Attraction, DayPlan, Hotel, Meal
from app.tools.amap_mcp import AMapToolRegistry, get_amap_tool_registry


async def _load_selected_details(
    poi_ids: set[str],
    registry: AMapToolRegistry,
) -> dict[str, dict[str, Any]]:
    """Load each selected POI at most once and tolerate missing details."""
    loaded = await registry.get_poi_details(sorted(poi_ids))
    parsed: dict[str, dict[str, Any]] = {}
    for poi_id, result in loaded.items():
        try:
            parsed[poi_id] = parse_amap_poi_detail(result)
        except Exception:
            continue
    return parsed


def _enrich_attraction(
    attraction: Attraction,
    details: dict[str, dict[str, Any]],
) -> Attraction:
    detail = details.get(attraction.poi_id or "")
    if detail is None:
        return attraction

    updates = poi_detail_updates(detail)
    if (attraction.type_code or "").startswith(("11", "14")):
        if cost := parse_amap_cost(detail.get("cost")):
            updates["ticket_price"] = cost
    return attraction.model_copy(update=updates)


def _enrich_hotel(
    hotel: Hotel | None,
    details: dict[str, dict[str, Any]],
) -> Hotel | None:
    if hotel is None:
        return None
    detail = details.get(hotel.poi_id or "")
    if detail is None:
        return hotel

    updates = poi_detail_updates(detail)
    cost = parse_amap_cost(detail.get("lowest_price"))
    if cost is None:
        cost = parse_amap_cost(detail.get("cost"))
    if cost is not None:
        updates["estimated_cost_per_night"] = cost
    return hotel.model_copy(update=updates)


def _enrich_meal(
    meal: Meal,
    details: dict[str, dict[str, Any]],
) -> Meal:
    detail = details.get(meal.poi_id or "")
    if detail is None:
        return meal

    updates = poi_detail_updates(detail)
    if cost := parse_amap_cost(detail.get("cost")):
        updates["estimated_cost"] = cost
    return meal.model_copy(update=updates)


async def run_plan_detail_enrichment(
    state: TripState,
    registry: AMapToolRegistry,
) -> TripState:
    """Attach real AMap details to POIs selected by the planner."""
    trip_plan = state.get("trip_plan")
    if trip_plan is None:
        return {}

    poi_ids = {
        poi_id
        for day in trip_plan.days
        for poi_id in [
            *(item.poi_id for item in day.attractions),
            day.hotel.poi_id if day.hotel else None,
            *(item.poi_id for item in day.meals),
        ]
        if poi_id
    }
    if not poi_ids:
        return {"trip_plan": trip_plan}

    details = await _load_selected_details(poi_ids, registry)
    updated_days: list[DayPlan] = []
    for day in trip_plan.days:
        updated_days.append(
            day.model_copy(
                update={
                    "attractions": [
                        _enrich_attraction(item, details)
                        for item in day.attractions
                    ],
                    "hotel": _enrich_hotel(day.hotel, details),
                    "meals": [_enrich_meal(item, details) for item in day.meals],
                }
            )
        )
    return {"trip_plan": trip_plan.model_copy(update={"days": updated_days})}


async def enrich_plan_details(state: TripState) -> TripState:
    """LangGraph entry point using the process-wide real AMap registry."""
    if state.get("trip_plan") is None:
        return {}
    return await run_plan_detail_enrichment(state, get_amap_tool_registry())
