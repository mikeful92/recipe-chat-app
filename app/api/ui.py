import logging
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api.recipes import (
    RecipeNoteCreate,
    add_note,
    get_recipe,
    list_notes,
    list_recipes,
    save_recipe,
)
from app.core.config import get_settings
from app.schemas.recipe import Recipe, RecipeRequest
from app.services.generator_factory import get_generator
from app.services.generator_stub import StubRecipeGenerator

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


def _parse_ingredients(raw: str) -> list[str]:
    chunks = [item.strip() for line in raw.splitlines() for item in line.split(",")]
    return [item for item in chunks if item]


@router.get("/")
async def generate_page(request: Request) -> Any:
    has_error = request.query_params.get("error") == "1"
    return templates.TemplateResponse(request, "generate.html", {"error_message": has_error})


@router.post("/ui/generate")
async def generate_from_form(
    request: Request,
    theme: str = Form(default=""),
    ingredients: str = Form(default=""),
    healthy: str | None = Form(default=None),
    quick_easy: str | None = Form(default=None),
) -> Any:
    recipe_request = RecipeRequest(
        theme=theme or None,
        ingredients=_parse_ingredients(ingredients),
        healthy=healthy is not None,
        quick_easy=quick_easy is not None,
    )
    settings = get_settings()
    try:
        recipe = get_generator(settings).generate(recipe_request)
    except Exception as exc:
        if settings.recipe_generator == "openai" and settings.openai_fallback_to_stub:
            logger.warning(
                "ui_recipe_generation",
                extra={
                    "outcome": "fallback",
                    "generator_mode": "openai",
                    "error_class": exc.__class__.__name__,
                    "has_theme": recipe_request.theme is not None,
                    "ingredients_count": len(recipe_request.ingredients),
                    "healthy": recipe_request.healthy,
                    "quick_easy": recipe_request.quick_easy,
                },
            )
            recipe = StubRecipeGenerator().generate(recipe_request)
        else:
            logger.warning(
                "ui_recipe_generation",
                extra={
                    "outcome": "failure",
                    "generator_mode": settings.recipe_generator,
                    "error_class": exc.__class__.__name__,
                    "has_theme": recipe_request.theme is not None,
                    "ingredients_count": len(recipe_request.ingredients),
                    "healthy": recipe_request.healthy,
                    "quick_easy": recipe_request.quick_easy,
                },
            )
            return RedirectResponse(url="/?error=1", status_code=303)

    if settings.recipe_generator == "openai":
        logger.info(
            "ui_recipe_generation",
            extra={
                "outcome": "success",
                "generator_mode": "openai",
                "has_theme": recipe_request.theme is not None,
                "ingredients_count": len(recipe_request.ingredients),
                "healthy": recipe_request.healthy,
                "quick_easy": recipe_request.quick_easy,
            },
        )

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "recipe": recipe,
            "recipe_json": recipe.model_dump_json(),
        },
    )


@router.post("/ui/save")
async def save_from_ui(recipe_json: str = Form()) -> RedirectResponse:
    try:
        recipe = Recipe.model_validate_json(recipe_json)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Invalid recipe payload") from exc
    try:
        saved = await save_recipe(recipe)
        recipe_id = saved["id"]
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        recipe_id = recipe.id
    return RedirectResponse(url=f"/recipes/ui/{recipe_id}", status_code=303)


@router.get("/recipes/ui")
async def list_recipes_ui(request: Request) -> Any:
    recipes = await list_recipes()
    return templates.TemplateResponse(request, "recipes_list.html", {"recipes": recipes})


@router.get("/recipes/ui/{recipe_id}")
async def recipe_detail_ui(request: Request, recipe_id: str) -> Any:
    recipe = await get_recipe(recipe_id)
    notes = await list_notes(recipe_id)
    return templates.TemplateResponse(
        request,
        "recipe_detail.html",
        {"recipe": recipe, "notes": notes},
    )


@router.post("/recipes/ui/{recipe_id}/notes")
async def add_note_ui(recipe_id: str, note_text: str = Form()) -> RedirectResponse:
    cleaned = note_text.strip()
    if cleaned:
        await add_note(recipe_id, RecipeNoteCreate(note_text=cleaned))
    return RedirectResponse(url=f"/recipes/ui/{recipe_id}", status_code=303)


@router.get("/cook/{recipe_id}")
async def cook_mode_page(request: Request, recipe_id: str) -> Any:
    recipe = await get_recipe(recipe_id)
    return templates.TemplateResponse(
        request,
        "cook_mode.html",
        {"recipe": recipe},
    )
