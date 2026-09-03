"""Deterministic hotel search node backed by AMap MCP."""

from typing import Any

from app.core.security import redact_sensitive_text
from app.graph.nodes.poi import parse_amap_pois
from app.graph.state import TripState
from app.models.trip import Hotel
from app.tools.amap_mcp import AMapToolRegistry, get_amap_tool_registry


MAX_HOTEL_CANDIDATES = 8

ACCOMMODATION_KEYWORDS = {
    "economy": "经济型酒店",
    "mid_range": "中档酒店",
    "luxury": "豪华酒店",
    "boutique": "精品酒店",
    "resort": "度假酒店",
    "hostel": "青年旅舍",
    "homestay": "民宿",
}


def build_hotel_keywords(accommodation: str) -> str:
    """Translate canonical accommodation values into AMap search terms."""
    value = accommodation.strip()
    if not value:
        return "酒店"
    if value in ACCOMMODATION_KEYWORDS:
        return ACCOMMODATION_KEYWORDS[value]
    if any(word in value for word in ("酒店", "民宿", "旅舍", "客栈")):
        return value
    return f"{value}酒店"


def parse_hotels(result: Any, hotel_type: str) -> list[Hotel]:
    """Convert AMap POIs into local hotel models."""
    return [
        Hotel(
            poi_id=str(poi.get("id") or "").strip() or None,
            name=str(poi["name"]).strip(),
            address=str(poi.get("address") or "").strip(),
            type_code=str(poi.get("typecode") or "").strip() or None,
            hotel_type=hotel_type,
        )
        for poi in parse_amap_pois(result)[:MAX_HOTEL_CANDIDATES]
    ]


async def run_hotel_search(
    state: TripState,
    registry: AMapToolRegistry,
) -> TripState:
    """Execute hotel search with an injectable registry for testing."""
    request = state["request"]
    keywords = build_hotel_keywords(request.accommodation)
    try:
        result = await registry.search_poi(request.city, keywords)
        hotels = parse_hotels(result, request.accommodation)
        if not hotels:
            return {
                "hotels": [],
                "errors": ["Hotel search returned no POIs."],
            }
        return {"hotels": hotels}
    except Exception as exc:
        return {
            "hotels": [],
            "errors": [f"Hotel search failed: {redact_sensitive_text(exc)}"],
        }


async def hotel_search(state: TripState) -> TripState:
    """LangGraph entry point using the process-wide real AMap registry."""
    return await run_hotel_search(state, get_amap_tool_registry())

# 什么时候使用 async
# 当函数需要等待耗时的异步操作时，例如：
# - 网络请求
# - MCP 工具调用
# - 数据库操作
# - 异步文件操作
# - 调用其他异步函数

# 什么时候不用 async
# 如果函数只是普通计算、字符串处理或数据转换，就不需要。

# 在异步函数内部调用异步函数：
# result = await async_function()
# 在普通入口中调用异步函数：
# import asyncio

# result = asyncio.run(async_function())
