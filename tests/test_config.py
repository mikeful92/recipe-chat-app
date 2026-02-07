import pytest

from app.core.config import get_settings


def test_get_settings_fails_when_openai_selected_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("RECIPE_GENERATOR", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        get_settings()


def test_get_settings_fails_on_invalid_generator_value(monkeypatch) -> None:
    monkeypatch.setenv("RECIPE_GENERATOR", "invalid")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="Invalid configuration"):
        get_settings()
