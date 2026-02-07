from typing import Protocol

from app.schemas.recipe import Recipe, RecipeRequest


class RecipeGenerator(Protocol):
    def generate(self, request: RecipeRequest) -> Recipe: ...
