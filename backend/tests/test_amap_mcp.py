import asyncio
from contextlib import asynccontextmanager
from typing import Any

import pytest
from pydantic import BaseModel
from pydantic import SecretStr

from app.core.config import Settings
from app.tools.amap_mcp import AMapToolNotFoundError, AMapToolRegistry


class ToolInput(BaseModel):
    city: str
    keywords: str | None = None
    citylimit: str | None = None


class FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def get_input_schema(self) -> type[BaseModel]:
        return ToolInput

    @property
    def args(self) -> dict[str, Any]:
        return ToolInput.model_json_schema()["properties"]

    async def ainvoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(arguments)
        return {"tool": self.name, "arguments": arguments}


class FakeClient:
    tools: list[FakeTool] = []
    connections: dict[str, Any] = {}
    handle_tool_errors: bool = False
    session_calls: list[tuple[str, dict[str, Any]]] = []

    def __init__(
        self,
        connections: dict[str, Any],
        *,
        handle_tool_errors: bool,
    ) -> None:
        type(self).connections = connections
        type(self).handle_tool_errors = handle_tool_errors

    async def get_tools(self, *, server_name: str | None = None) -> list[FakeTool]:
        assert server_name == "amap"
        return list(type(self).tools)

    @asynccontextmanager
    async def session(self, server_name: str):
        assert server_name == "amap"

        class Session:
            async def call_tool(
                self,
                name: str,
                *,
                arguments: dict[str, Any],
            ) -> dict[str, Any]:
                FakeClient.session_calls.append((name, arguments))
                return {"tool": name, "arguments": arguments}

        yield Session()


def make_registry(*tools: FakeTool) -> AMapToolRegistry:
    FakeClient.tools = list(tools)
    FakeClient.session_calls = []
    settings = Settings(
        amap_maps_api_key=SecretStr("test-secret"),
        amap_mcp_command="uvx",
        amap_mcp_package="amap-mcp-server",
    )
    return AMapToolRegistry(settings=settings, client_factory=FakeClient)


def test_registry_builds_stdio_connection_without_exposing_key() -> None:
    make_registry(FakeTool("maps_weather"))

    connection = FakeClient.connections["amap"]

    assert connection["transport"] == "stdio"
    assert connection["command"] == "uvx"
    assert connection["args"] == ["amap-mcp-server"]
    assert connection["env"]["AMAP_MAPS_API_KEY"] == "test-secret"
    assert FakeClient.handle_tool_errors is True


def test_registry_finds_exact_tool_name_and_caches_load() -> None:
    weather = FakeTool("maps_weather")
    registry = make_registry(weather)

    first = asyncio.run(registry.get_tool("weather"))
    second = asyncio.run(registry.get_tool("weather"))

    assert first is weather
    assert second is weather


def test_registry_invokes_weather_poi_and_detail_with_schema_arguments() -> None:
    weather = FakeTool("maps_weather")
    poi = FakeTool("maps_text_search")
    detail = FakeTool("maps_search_detail")
    registry = make_registry(weather, poi, detail)

    weather_result = asyncio.run(registry.query_weather("成都"))
    poi_result = asyncio.run(registry.search_poi("成都", "景点"))
    detail_result = asyncio.run(registry.get_poi_detail("B001"))

    assert weather_result["arguments"] == {"city": "成都"}
    assert poi_result["arguments"] == {
        "city": "成都",
        "keywords": "景点",
        "citylimit": "true",
    }
    assert detail_result["arguments"] == {"id": "B001"}


def test_registry_reports_available_tools_when_capability_is_missing() -> None:
    registry = make_registry(FakeTool("maps_geo"))

    with pytest.raises(AMapToolNotFoundError, match="maps_geo"):
        asyncio.run(registry.get_tool("weather"))


def test_registry_reuses_one_session_for_multiple_poi_details() -> None:
    registry = make_registry()

    result = asyncio.run(registry.get_poi_details(["B001", "B002", "B001"]))

    assert sorted(result) == ["B001", "B002"]
    assert sorted(FakeClient.session_calls, key=lambda item: item[1]["id"]) == [
        ("maps_search_detail", {"id": "B001"}),
        ("maps_search_detail", {"id": "B002"}),
    ]


def test_registry_requires_api_key_before_starting_server() -> None:
    settings = Settings(amap_maps_api_key=None)

    with pytest.raises(ValueError, match="AMAP_MAPS_API_KEY is not configured"):
        AMapToolRegistry(settings=settings, client_factory=FakeClient)
