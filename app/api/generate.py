from fastapi import APIRouter

from app.schemas.recipe import Recipe, RecipeRequest
from app.services.recipe_builder import build_recipe

router = APIRouter()


@router.post("/generate", response_model=Recipe)
async def generate_recipe(request: RecipeRequest) -> Recipe:
    return build_recipe(request)
