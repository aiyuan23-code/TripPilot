import pytest
from pydantic import SecretStr

import app.core.llm as llm_module
from app.core.config import Settings


class FakeChatModel:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


def make_settings(**overrides) -> Settings:
    values = {
        "llm_provider": "deepseek",
        "llm_model_id": "deepseek-v4-flash",
        "llm_api_key": SecretStr("test-llm-key"),
        "llm_temperature": 0.2,
        "llm_timeout_seconds": 60,
        "llm_max_retries": 2,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_create_llm_uses_deepseek_defaults_without_fixing_model(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "ChatOpenAI", FakeChatModel)

    model = llm_module.create_llm(make_settings())

    assert model.kwargs["model"] == "deepseek-v4-flash"
    assert model.kwargs["base_url"] == "https://api.deepseek.com"
    assert model.kwargs["api_key"].get_secret_value() == "test-llm-key"


def test_create_llm_supports_openai_and_custom_model(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "ChatOpenAI", FakeChatModel)
    settings = make_settings(
        llm_provider="openai",
        llm_model_id="custom-openai-model",
    )

    model = llm_module.create_llm(settings)

    assert model.kwargs["model"] == "custom-openai-model"
    assert "base_url" not in model.kwargs


def test_openai_compatible_provider_requires_base_url(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "ChatOpenAI", FakeChatModel)
    settings = make_settings(
        llm_provider="openai_compatible",
        llm_base_url=None,
    )

    with pytest.raises(ValueError, match="LLM_BASE_URL is required"):
        llm_module.create_llm(settings)


def test_unknown_provider_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "ChatOpenAI", FakeChatModel)

    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        llm_module.create_llm(make_settings(llm_provider="unknown"))

