"""Shared decoding helpers for LangChain MCP tool results."""

import json
from typing import Any


class MCPResultError(ValueError):
    """Raised when an MCP result contains no usable JSON object."""


def decode_mcp_payload(result: Any) -> dict[str, Any]:
    """Extract one structured JSON object from an MCP/LangChain result."""
    if isinstance(result, dict):
        if result.get("type") == "text" and "text" in result:
            return decode_mcp_payload(result["text"])
        return result

    if isinstance(result, str):
        try:
            decoded = json.loads(result)
        except json.JSONDecodeError as exc:
            raise MCPResultError("MCP result is not valid JSON.") from exc
        return decode_mcp_payload(decoded)

    if isinstance(result, list):
        for item in result:
            try:
                return decode_mcp_payload(item)
            except MCPResultError:
                continue
        raise MCPResultError("MCP result contains no JSON payload.")

    if hasattr(result, "content"):
        return decode_mcp_payload(result.content)
    if hasattr(result, "model_dump"):
        return decode_mcp_payload(result.model_dump(mode="json"))

    raise MCPResultError(f"Unsupported MCP result type: {type(result).__name__}.")

