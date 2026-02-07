from fastapi import APIRouter

from app.schemas.recipe import Recipe, RecipeRequest
from app.services.generator_factory import get_generator

router = APIRouter()


@router.post("/generate", response_model=Recipe)
async def generate_recipe(request: RecipeRequest) -> Recipe:
    generator = get_generator()
    return generator.generate(request)
