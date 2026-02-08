import logging

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas.recipe import Recipe, RecipeRequest
from app.services.generator_factory import get_generator
from app.services.generator_stub import StubRecipeGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

generate_api_counters = {
    "success": 0,
    "failure": 0,
    "fallback": 0,
}

_GENERATION_UNAVAILABLE = {
    "code": "generation_unavailable",
    "message": "Recipe generation is temporarily unavailable. Please try again.",
}


@router.post("/generate", response_model=Recipe)
async def generate_recipe(request: RecipeRequest) -> Recipe:
    settings = get_settings()
    try:
        generator = get_generator(settings)
        recipe = generator.generate(request)
        generate_api_counters["success"] += 1
        logger.info(
            "api_recipe_generation",
            extra={
                "outcome": "success",
                "generator_mode": settings.recipe_generator,
                "has_theme": request.theme is not None,
                "ingredients_count": len(request.ingredients),
                "healthy": request.healthy,
                "quick_easy": request.quick_easy,
            },
        )
        return recipe
    except Exception as exc:
        if settings.recipe_generator == "openai" and settings.openai_fallback_to_stub:
            generate_api_counters["fallback"] += 1
            logger.warning(
                "api_recipe_generation",
                extra={
                    "outcome": "fallback",
                    "generator_mode": "openai",
                    "error_class": exc.__class__.__name__,
                    "has_theme": request.theme is not None,
                    "ingredients_count": len(request.ingredients),
                    "healthy": request.healthy,
                    "quick_easy": request.quick_easy,
                },
            )
            return StubRecipeGenerator().generate(request)

        generate_api_counters["failure"] += 1
        logger.warning(
            "api_recipe_generation",
            extra={
                "outcome": "failure",
                "generator_mode": settings.recipe_generator,
                "error_class": exc.__class__.__name__,
                "has_theme": request.theme is not None,
                "ingredients_count": len(request.ingredients),
                "healthy": request.healthy,
                "quick_easy": request.quick_easy,
            },
        )
        raise HTTPException(status_code=503, detail=_GENERATION_UNAVAILABLE) from exc
