"""Shared parsing for AMap POI text-search results."""

from typing import Any

from app.graph.nodes.mcp_result import decode_mcp_payload
from app.models.trip import Location


class POIDataError(ValueError):
    """Raised when AMap returns unusable POI data."""


def parse_amap_poi_detail(result: Any) -> dict[str, Any]:
    """Extract one POI detail object returned by ``maps_search_detail``."""
    payload = decode_mcp_payload(result)
    if error := payload.get("error"):
        raise POIDataError(str(error))
    return payload


def parse_amap_location(value: Any) -> Location | None:
    """Convert an AMap ``longitude,latitude`` value into ``Location``."""
    if not isinstance(value, str):
        return None

    parts = value.replace("，", ",").split(",")
    if len(parts) != 2:
        return None
    try:
        return Location(
            longitude=float(parts[0].strip()),
            latitude=float(parts[1].strip()),
        )
    except (TypeError, ValueError):
        return None


def parse_amap_rating(value: Any) -> float | None:
    """Convert an optional AMap rating into a validated float."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        rating = float(value)
    except ValueError:
        return None
    return rating if 0 <= rating <= 5 else None


def parse_amap_cost(value: Any) -> float | None:
    """Convert a positive optional AMap cost field into a float."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        cost = float(value)
    except ValueError:
        return None
    return cost if cost > 0 else None


def poi_detail_updates(result: Any) -> dict[str, Any]:
    """Build model updates shared by attractions and hotels."""
    detail = parse_amap_poi_detail(result)
    updates: dict[str, Any] = {}

    if location := parse_amap_location(detail.get("location")):
        updates["location"] = location
    if (rating := parse_amap_rating(detail.get("rating"))) is not None:
        updates["rating"] = rating
    if address := str(detail.get("address") or "").strip():
        updates["address"] = address
    return updates


def parse_amap_pois(result: Any) -> list[dict[str, Any]]:
    """Extract and deduplicate POIs returned by ``maps_text_search``."""
    payload = decode_mcp_payload(result)
    if error := payload.get("error"):
        raise POIDataError(str(error))

    pois = payload.get("pois")
    if not isinstance(pois, list):
        raise POIDataError("AMap POI result does not contain a POI list.")

    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for poi in pois:
        if not isinstance(poi, dict):
            continue
        name = str(poi.get("name") or "").strip()
        if not name:
            continue
        poi_id = str(poi.get("id") or "").strip()
        identity = poi_id or name
        if identity in seen:
            continue
        seen.add(identity)
        parsed.append(poi)
    return parsed
