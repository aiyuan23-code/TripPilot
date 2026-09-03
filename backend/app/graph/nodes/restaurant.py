"""Deterministic restaurant search node backed by AMap MCP."""

from typing import Any

from app.core.security import redact_sensitive_text
from app.graph.nodes.poi import parse_amap_pois
from app.graph.state import TripState
from app.models.trip import Meal
from app.tools.amap_mcp import AMapToolRegistry, get_amap_tool_registry


MAX_RESTAURANT_CANDIDATES = 8


def build_restaurant_keywords(preferences: list[str]) -> str:
    """Choose a stable restaurant search term from user preferences."""
    return "特色餐厅" if "美食" in preferences else "餐厅"


def parse_restaurants(result: Any) -> list[Meal]:
    """Convert AMap restaurant POIs into meal candidates."""
    return [
        Meal(
            poi_id=str(poi.get("id") or "").strip() or None,
            type_code=str(poi.get("typecode") or "").strip() or None,
            meal_type="restaurant",
            name=str(poi["name"]).strip(),
            address=str(poi.get("address") or "").strip(),
        )
        for poi in parse_amap_pois(result)[:MAX_RESTAURANT_CANDIDATES]
    ]


async def run_restaurant_search(
    state: TripState,
    registry: AMapToolRegistry,
) -> TripState:
    """Search and enrich real restaurant candidates for the planner."""
    request = state["request"]
    keywords = build_restaurant_keywords(request.preferences)
    try:
        result = await registry.search_poi(request.city, keywords)
        restaurants = parse_restaurants(result)
        if not restaurants:
            return {
                "restaurants": [],
                "errors": ["Restaurant search returned no POIs."],
            }
        return {"restaurants": restaurants}
    except Exception as exc:
        return {
            "restaurants": [],
            "errors": [f"Restaurant search failed: {redact_sensitive_text(exc)}"],
        }


async def restaurant_search(state: TripState) -> TripState:
    """LangGraph entry point using the process-wide real AMap registry."""
    return await run_restaurant_search(state, get_amap_tool_registry())
