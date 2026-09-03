"""Provider-aware factory for TripPilot chat models."""

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings


DEFAULT_PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": None,
}
SUPPORTED_LLM_PROVIDERS = {*DEFAULT_PROVIDER_BASE_URLS, "openai_compatible"}


def create_llm(settings: Settings) -> BaseChatModel:
    """Create a chat model from configuration without fixing one provider."""
    provider = settings.llm_provider.strip().lower()
    if provider not in SUPPORTED_LLM_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. "
            f"Supported: {supported}."
        )

    settings.require_llm_api_key()
    model_id = settings.require_llm_model_id()
    base_url = settings.llm_base_url or DEFAULT_PROVIDER_BASE_URLS.get(provider)
    if provider == "openai_compatible" and not base_url:
        raise ValueError("LLM_BASE_URL is required for openai_compatible provider.")

    kwargs = {
        "model": model_id,
        "api_key": settings.llm_api_key,
        "temperature": settings.llm_temperature,
        "timeout": settings.llm_timeout_seconds,
        "max_retries": settings.llm_max_retries,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Return one reusable model client per application process."""
    return create_llm(get_settings())

