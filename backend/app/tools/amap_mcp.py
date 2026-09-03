"""Reusable LangChain tools provided by the AMap MCP server."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import Settings, get_settings


AMAP_SERVER_NAME = "amap"
POI_DETAIL_TIMEOUT_SECONDS = 15
MAX_POI_DETAIL_CONCURRENCY = 4


class AMapMCPError(RuntimeError):
    """Raised when the AMap MCP server cannot be started or queried."""


class AMapToolNotFoundError(AMapMCPError):
    """Raised when the server does not expose a required capability."""


ClientFactory = Callable[..., MultiServerMCPClient]


class AMapToolRegistry:
    """Load, cache and locate AMap MCP tools for graph nodes."""

    _TOOL_NAMES: dict[str, str] = {
        "weather": "maps_weather",
        "text_search": "maps_text_search",
        "detail": "maps_search_detail",
        "geo": "maps_geo",
    }

    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: ClientFactory = MultiServerMCPClient,
    ) -> None:
        self.settings = settings or get_settings()
        api_key = self.settings.require_amap_api_key()
        self._client = client_factory(
            {
                AMAP_SERVER_NAME: {
                    "transport": "stdio",
                    "command": self.settings.amap_mcp_command,
                    "args": [self.settings.amap_mcp_package],
                    "env": {"AMAP_MAPS_API_KEY": api_key},
                }
            },
            handle_tool_errors=True,
        )
        self._tools: list[BaseTool] | None = None
        self._load_lock = asyncio.Lock()

    async def get_tools(self, *, refresh: bool = False) -> list[BaseTool]:
        """Load AMap tools once and reuse the converted LangChain tool objects."""
        if self._tools is not None and not refresh:
            return list(self._tools)

        async with self._load_lock:
            if self._tools is not None and not refresh:
                return list(self._tools)
            try:
                tools = await self._client.get_tools(server_name=AMAP_SERVER_NAME)
            except Exception as exc:
                raise AMapMCPError(
                    "Unable to load AMap MCP tools. Check uvx, network access, "
                    "the MCP package name and AMAP_MAPS_API_KEY."
                ) from exc

            if not tools:
                raise AMapMCPError("The AMap MCP server returned no tools.")
            self._tools = list(tools)
            return list(self._tools)

    async def get_tool(self, capability: str) -> BaseTool:
        """Resolve a semantic capability to the actual server tool."""
        tool_name = self._TOOL_NAMES.get(capability)
        if tool_name is None:
            supported = ", ".join(sorted(self._TOOL_NAMES))
            raise ValueError(
                f"Unknown AMap capability: {capability}. Supported: {supported}."
            )

        tools = await self.get_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool

        available = ", ".join(sorted(tool.name for tool in tools))
        raise AMapToolNotFoundError(
            f"AMap capability '{capability}' was not found. "
            f"Available tools: {available or '(none)'}."
        )

    async def query_weather(self, city: str) -> Any:
        """Call the server's deterministic city weather tool."""
        tool = await self.get_tool("weather")
        return await tool.ainvoke({"city": city})

    async def search_poi(self, city: str, keywords: str) -> Any:
        """Search AMap POIs using the server's text-search tool."""
        tool = await self.get_tool("text_search")
        return await tool.ainvoke(
            {
                "city": city,
                "keywords": keywords,
                "citylimit": "true",
            }
        )

    async def get_poi_detail(self, poi_id: str) -> Any:
        """Load one AMap POI's detailed fields by its stable ID."""
        tool = await self.get_tool("detail")
        return await tool.ainvoke({"id": poi_id})

    async def get_poi_details(self, poi_ids: list[str]) -> dict[str, Any]:
        """Load multiple POI details through one persistent MCP session."""
        unique_ids = list(dict.fromkeys(poi_ids))
        if not unique_ids:
            return {}

        semaphore = asyncio.Semaphore(MAX_POI_DETAIL_CONCURRENCY)
        tool_name = self._TOOL_NAMES["detail"]
        async with self._client.session(AMAP_SERVER_NAME) as session:

            async def load(poi_id: str) -> tuple[str, Any | None]:
                try:
                    async with semaphore:
                        result = await asyncio.wait_for(
                            session.call_tool(tool_name, arguments={"id": poi_id}),
                            timeout=POI_DETAIL_TIMEOUT_SECONDS,
                        )
                    return poi_id, result
                except Exception:
                    return poi_id, None

            loaded = await asyncio.gather(*(load(poi_id) for poi_id in unique_ids))
        return {poi_id: result for poi_id, result in loaded if result is not None}

    @staticmethod
    def _input_properties(tool: BaseTool) -> dict[str, Any]:
        return tool.args


@lru_cache(maxsize=1)
def get_amap_tool_registry() -> AMapToolRegistry:
    """Return the process-wide AMap tool registry."""
    return AMapToolRegistry()
