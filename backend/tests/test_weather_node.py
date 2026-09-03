import asyncio
from typing import Any

from app.graph.nodes.weather import parse_amap_weather, run_weather_query
from app.models import TripPlanRequest


def make_request(
    start_date: str = "2026-09-01",
    end_date: str = "2026-09-02",
) -> TripPlanRequest:
    return TripPlanRequest(
        city="成都",
        start_date=start_date,
        end_date=end_date,
    )


def amap_weather_payload() -> dict[str, Any]:
    return {
        "city": "成都市",
        "forecasts": [
            {
                "date": "2026-09-01",
                "dayweather": "晴",
                "nightweather": "多云",
                "daytemp": "30",
                "nighttemp": "21",
                "daywind": "南",
                "daypower": "≤3",
            },
            {
                "date": "2026-09-02",
                "dayweather": "小雨",
                "nightweather": "阴",
                "daytemp": "26°C",
                "nighttemp": "19℃",
                "daywind": "北",
                "daypower": "4",
            },
            {
                "date": "2026-09-03",
                "dayweather": "多云",
                "nightweather": "晴",
                "daytemp": "28",
                "nighttemp": "20",
            },
        ],
    }


class FakeWeatherRegistry:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.requested_city: str | None = None

    async def query_weather(self, city: str) -> Any:
        self.requested_city = city
        if self.error is not None:
            raise self.error
        return self.result


def test_parse_amap_weather_handles_langchain_text_blocks() -> None:
    result = [{"type": "text", "text": __import__("json").dumps(amap_weather_payload())}]

    weather = parse_amap_weather(result, make_request())

    assert len(weather) == 2
    assert weather[0].date.isoformat() == "2026-09-01"
    assert weather[0].wind_direction == "南"
    assert weather[1].day_temp == 26
    assert weather[1].night_temp == 19


def test_weather_node_calls_city_and_returns_typed_weather() -> None:
    request = make_request()
    registry = FakeWeatherRegistry(result=amap_weather_payload())

    result = asyncio.run(
        run_weather_query({"request": request}, registry)  # type: ignore[arg-type]
    )

    assert registry.requested_city == "成都"
    assert len(result["weather_info"]) == 2
    assert "errors" not in result


def test_weather_node_falls_back_when_mcp_fails() -> None:
    request = make_request()
    registry = FakeWeatherRegistry(error=RuntimeError("connection lost"))

    result = asyncio.run(
        run_weather_query({"request": request}, registry)  # type: ignore[arg-type]
    )

    assert result["weather_info"] == []
    assert result["errors"] == ["Weather query failed: connection lost"]


def test_weather_node_does_not_use_forecast_for_uncovered_dates() -> None:
    request = make_request("2026-10-01", "2026-10-03")
    registry = FakeWeatherRegistry(result=amap_weather_payload())

    result = asyncio.run(
        run_weather_query({"request": request}, registry)  # type: ignore[arg-type]
    )

    assert result["weather_info"] == []
    assert result["errors"] == [
        "Weather forecast does not cover the requested trip dates."
    ]

