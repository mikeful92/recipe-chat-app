from app.core.config import Settings, get_settings
from app.services.generator_factory import generator_factory_counters, get_generator
from app.services.generator_stub import StubRecipeGenerator


def test_generator_factory_selects_stub_by_default(monkeypatch) -> None:
    monkeypatch.delenv("RECIPE_GENERATOR", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    generator = get_generator()

    assert isinstance(generator, StubRecipeGenerator)


def test_generator_factory_selects_openai_when_configured_with_key(monkeypatch) -> None:
    class FakeOpenAIGenerator:
        def __init__(self, api_key: str, model: str) -> None:
            self.api_key = api_key
            self.model = model

    monkeypatch.setattr("app.services.generator_factory.OpenAIRecipeGenerator", FakeOpenAIGenerator)
    settings = Settings(
        recipe_generator="openai",
        openai_api_key="test-key",
        openai_model="gpt-4.1-mini",
    )

    generator = get_generator(settings)

    assert isinstance(generator, FakeOpenAIGenerator)
    assert generator.api_key == "test-key"
    assert generator.model == "gpt-4.1-mini"


def test_generator_factory_falls_back_to_stub_when_openai_key_missing() -> None:
    settings = Settings(
        recipe_generator="openai",
        openai_api_key=None,
        openai_fallback_to_stub=True,
    )
    generator_factory_counters["fallback"] = 0

    generator = get_generator(settings)

    assert isinstance(generator, StubRecipeGenerator)
    assert generator_factory_counters["fallback"] == 1
