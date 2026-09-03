"""Deterministic weather node backed by the real AMap MCP tool."""

from typing import Any

from app.core.security import redact_sensitive_text
from app.graph.nodes.mcp_result import decode_mcp_payload
from app.graph.state import TripState
from app.models.request import TripPlanRequest
from app.models.trip import WeatherInfo
from app.tools.amap_mcp import AMapToolRegistry, get_amap_tool_registry


class WeatherDataError(ValueError):
    """Raised when AMap returns unusable weather data."""


def parse_amap_weather(
    result: Any,
    request: TripPlanRequest,
) -> list[WeatherInfo]:
    """Convert the AMap MCP response into local weather models.

    Only forecasts covering the requested trip dates are returned. We deliberately
    do not attach near-term weather to a future trip whose dates are not covered.
    """
    payload = decode_mcp_payload(result)
    if error := payload.get("error"):
        raise WeatherDataError(str(error))

    forecasts = payload.get("forecasts")
    if not isinstance(forecasts, list) or not forecasts:
        raise WeatherDataError("AMap returned no weather forecasts.")

    parsed: list[WeatherInfo] = []
    for forecast in forecasts:
        if not isinstance(forecast, dict):
            continue
        parsed.append(
            WeatherInfo(
                date=forecast.get("date"),
                day_weather=forecast.get("dayweather", ""),
                night_weather=forecast.get("nightweather"),
                day_temp=forecast.get("daytemp"),
                night_temp=forecast.get("nighttemp"),
                wind_direction=forecast.get("daywind") or forecast.get("nightwind"),
                wind_power=forecast.get("daypower") or forecast.get("nightpower"),
            )
        )

    return [
        weather
        for weather in parsed
        if request.start_date <= weather.date <= request.end_date
    ]


async def run_weather_query(
    state: TripState,
    registry: AMapToolRegistry,
) -> TripState:
    """Execute the weather node with an injectable registry for testing."""
    request = state["request"]
    try:
        result = await registry.query_weather(request.city)
        weather_info = parse_amap_weather(result, request)
        if not weather_info:
            return {
                "weather_info": [],
                "errors": [
                    "Weather forecast does not cover the requested trip dates."
                ],
            }
        return {"weather_info": weather_info}
    except Exception as exc:
        return {
            "weather_info": [],
            "errors": [f"Weather query failed: {redact_sensitive_text(exc)}"],
        }


async def weather_query(state: TripState) -> TripState:
    """LangGraph entry point using the process-wide real AMap registry."""
    return await run_weather_query(state, get_amap_tool_registry())
