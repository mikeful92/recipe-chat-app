from app.core.config import get_settings
from app.services.generator_factory import get_generator
from app.services.generator_stub import StubRecipeGenerator


def test_generator_factory_selects_stub_by_default(monkeypatch) -> None:
    monkeypatch.delenv("RECIPE_GENERATOR", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    generator = get_generator()

    assert isinstance(generator, StubRecipeGenerator)
