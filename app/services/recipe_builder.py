from app.schemas.recipe import Recipe, RecipeRequest
from app.services.generator_stub import StubRecipeGenerator


def build_recipe(request: RecipeRequest) -> Recipe:
    return StubRecipeGenerator().generate(request)
