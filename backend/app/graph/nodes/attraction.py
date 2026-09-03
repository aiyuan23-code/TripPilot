"""Deterministic attraction search node backed by AMap MCP."""

import asyncio
from typing import Any

from app.core.security import redact_sensitive_text
from app.graph.nodes.poi import parse_amap_pois
from app.graph.state import TripState
from app.models.trip import Attraction
from app.tools.amap_mcp import AMapToolRegistry, get_amap_tool_registry


MAX_ATTRACTION_CANDIDATES = 12
MAX_ATTRACTION_QUERIES = 3

# 美食由 Restaurant Node 单独处理，不再作为景点关键词搜索。
NON_ATTRACTION_PREFERENCES = {"美食"}
ATTRACTION_TYPE_PREFIXES = ("08", "11", "14")

PREFERENCE_KEYWORDS = {
    "历史文化": "历史文化景点",
    "自然风光": "自然风光景区",
    "亲子": "亲子景点",
    "购物": "购物中心",
    "艺术": "美术馆",
}


def build_attraction_keywords(preferences: list[str]) -> list[str]:
    """Build separate AMap queries for attraction-related preferences."""
    keywords: list[str] = []
    for raw_preference in preferences:
        preference = raw_preference.strip()
        if not preference or preference in NON_ATTRACTION_PREFERENCES:
            continue

        keyword = PREFERENCE_KEYWORDS.get(preference, f"{preference}景点")
        if keyword not in keywords:
            keywords.append(keyword)
        if len(keywords) == MAX_ATTRACTION_QUERIES:
            break

    # 即使用户只选择“美食”，行程中也仍然需要真正的游览景点。
    return keywords or ["热门景点"]


def _is_attraction_poi(type_code: str, *, include_shopping: bool) -> bool:
    """Return whether an AMap type code is suitable as an attraction."""
    allowed_prefixes = ATTRACTION_TYPE_PREFIXES
    if include_shopping:
        allowed_prefixes += ("06",)
    return any(
        code.strip().startswith(allowed_prefixes)
        for code in type_code.split("|")
    )


def parse_attractions(
    result: Any,
    *,
    include_shopping: bool = False,
) -> list[Attraction]:
    """Convert suitable AMap POIs into local attraction models."""
    attractions: list[Attraction] = []
    for poi in parse_amap_pois(result):
        type_code = str(poi.get("typecode") or "").strip()
        if not _is_attraction_poi(
            type_code,
            include_shopping=include_shopping,
        ):
            continue
        attractions.append(
            Attraction(
                poi_id=str(poi.get("id") or "").strip() or None,
                name=str(poi["name"]).strip(),
                address=str(poi.get("address") or "").strip(),
                type_code=type_code or None,
            )
        )
    return attractions[:MAX_ATTRACTION_CANDIDATES]


def merge_attraction_groups(
    groups: list[list[Attraction]],
) -> list[Attraction]:
    """Round-robin merge query results, deduplicate them and enforce the limit."""
    merged: list[Attraction] = []
    seen: set[str] = set()
    max_group_size = max((len(group) for group in groups), default=0)

    for index in range(max_group_size):
        for group in groups:
            if index >= len(group):
                continue
            attraction = group[index]
            identity = attraction.poi_id or attraction.name
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(attraction)
            if len(merged) == MAX_ATTRACTION_CANDIDATES:
                return merged
    return merged


async def run_attraction_search(
    state: TripState,
    registry: AMapToolRegistry,
) -> TripState:
    """Execute attraction search with an injectable registry for testing."""
    request = state["request"]
    keywords = build_attraction_keywords(request.preferences)
    try:
        results = await asyncio.gather(
            *(registry.search_poi(request.city, keyword) for keyword in keywords),
            return_exceptions=True,
        )
        groups: list[list[Attraction]] = []
        query_errors: list[str] = []
        for keyword, result in zip(keywords, results, strict=True):
            if isinstance(result, BaseException):
                query_errors.append(
                    f"Attraction query '{keyword}' failed: "
                    f"{redact_sensitive_text(result)}"
                )
                continue
            try:
                groups.append(
                    parse_attractions(
                        result,
                        include_shopping=keyword == PREFERENCE_KEYWORDS["购物"],
                    )
                )
            except Exception as exc:
                query_errors.append(
                    f"Attraction query '{keyword}' failed: "
                    f"{redact_sensitive_text(exc)}"
                )

        attractions = merge_attraction_groups(groups)
        if not attractions:
            return {
                "attractions": [],
                "errors": query_errors
                or ["Attraction search returned no suitable POIs."],
            }
        response: TripState = {"attractions": attractions}
        if query_errors:
            response["errors"] = query_errors
        return response
    except Exception as exc:
        return {
            "attractions": [],
            "errors": [
                f"Attraction search failed: {redact_sensitive_text(exc)}"
            ],
        }


async def attraction_search(state: TripState) -> TripState:
    """LangGraph entry point using the process-wide real AMap registry."""
    return await run_attraction_search(state, get_amap_tool_registry())
