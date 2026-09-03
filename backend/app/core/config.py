"""Application settings loaded from environment variables and the project .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """TripPilot runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    amap_maps_api_key: SecretStr | None = Field(
        default=None,
        description="高德地图 Web Service API Key",
    )
    amap_mcp_command: str = Field(
        default="uvx",
        description="用于启动高德 MCP Server 的命令",
    )
    amap_mcp_package: str = Field(
        default="amap-mcp-server",
        description="高德 MCP Server 的 uvx 包与入口名称",
    )

    llm_provider: str = Field(
        default="deepseek",
        description="LLM Provider: deepseek/openai/openai_compatible",
    )
    llm_model_id: str | None = Field(default=None, description="模型 ID")
    llm_api_key: SecretStr | None = Field(default=None, description="LLM API Key")
    llm_base_url: str | None = Field(
        default=None,
        description="OpenAI-compatible API Base URL",
    )
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_timeout_seconds: float = Field(default=120, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)
    llm_structured_output_method: Literal[
        "function_calling", "json_mode", "json_schema"
    ] = "function_calling"

    def require_amap_api_key(self) -> str:
        """Return the API key or fail before starting the MCP subprocess."""
        if self.amap_maps_api_key is None:
            raise ValueError(
                "AMAP_MAPS_API_KEY is not configured. "
                "Copy .env.example to .env and set your own key."
            )

        value = self.amap_maps_api_key.get_secret_value().strip()
        if not value or value == "your_amap_web_service_api_key":
            raise ValueError("AMAP_MAPS_API_KEY must contain a real API key.")
        return value

    def require_llm_api_key(self) -> str:
        """Return a configured LLM key without exposing it in logs."""
        if self.llm_api_key is None:
            raise ValueError("LLM_API_KEY is not configured.")
        value = self.llm_api_key.get_secret_value().strip()
        if not value or value == "your_llm_api_key":
            raise ValueError("LLM_API_KEY must contain a real API key.")
        return value

    def require_llm_model_id(self) -> str:
        """Return the configured model identifier."""
        value = (self.llm_model_id or "").strip()
        if not value:
            raise ValueError("LLM_MODEL_ID is not configured.")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings object per application process."""
    return Settings()
