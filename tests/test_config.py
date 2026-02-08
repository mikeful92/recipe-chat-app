import pytest

from app.core.config import get_settings


def test_get_settings_allows_openai_without_api_key_when_fallback_enabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("RECIPE_GENERATOR", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_FALLBACK_TO_STUB", "1")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.recipe_generator == "openai"
    assert settings.openai_api_key is None
    assert settings.openai_fallback_to_stub is True


def test_get_settings_fails_when_openai_selected_without_api_key_and_fallback_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("RECIPE_GENERATOR", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_FALLBACK_TO_STUB", "0")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        get_settings()


def test_get_settings_fails_on_invalid_generator_value(monkeypatch) -> None:
    monkeypatch.setenv("RECIPE_GENERATOR", "invalid")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="Invalid configuration"):
        get_settings()
