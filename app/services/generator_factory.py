from app.core.config import Settings, get_settings
from app.services.generator_base import RecipeGenerator
from app.services.generator_openai import OpenAIRecipeGenerator
from app.services.generator_stub import StubRecipeGenerator


def get_generator(settings: Settings | None = None) -> RecipeGenerator:
    config = settings or get_settings()

    if config.recipe_generator == "openai":
        return OpenAIRecipeGenerator(
            api_key=config.openai_api_key or "",
            model=config.openai_model,
        )

    return StubRecipeGenerator()
