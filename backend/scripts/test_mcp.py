"""Manually verify the real AMap MCP server before graph integration."""

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

# Allow both `python scripts/test_mcp.py` and `python -m scripts.test_mcp`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import redact_sensitive_text
from app.tools.amap_mcp import AMapMCPError, AMapToolRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test the real AMap MCP tools")
    parser.add_argument("--city", default="成都", help="City used for live queries")
    parser.add_argument(
        "--keywords",
        default="景点",
        help="POI keywords used for text search",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only connect and print available tool schemas",
    )
    return parser.parse_args()


def render(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    try:
        serialized = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        return redact_sensitive_text(serialized)
    except TypeError:
        return redact_sensitive_text(value)


async def run(city: str, keywords: str, *, list_only: bool) -> None:
    registry = AMapToolRegistry()
    tools = await registry.get_tools()

    print(f"Connected to AMap MCP. Loaded {len(tools)} tools:")
    for tool in sorted(tools, key=lambda item: item.name):
        fields = ", ".join(registry._input_properties(tool))
        print(f"- {tool.name}({fields})")

    if list_only:
        return

    print(f"\nWeather result for {city}:")
    print(render(await registry.query_weather(city)))

    print(f"\nPOI result for {city} / {keywords}:")
    print(render(await registry.search_poi(city, keywords)))


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(
            run(args.city, args.keywords, list_only=args.list_only)
        )
    except (ValueError, AMapMCPError) as exc:
        message = redact_sensitive_text(exc)
        raise SystemExit(f"MCP check failed: {message}") from exc


if __name__ == "__main__":
    main()
