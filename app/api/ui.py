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
from app.schemas.recipe import Recipe, RecipeRequest
from app.services.recipe_builder import build_recipe

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _parse_ingredients(raw: str) -> list[str]:
    chunks = [item.strip() for line in raw.splitlines() for item in line.split(",")]
    return [item for item in chunks if item]


@router.get("/")
async def generate_page(request: Request) -> Any:
    return templates.TemplateResponse(request, "generate.html")


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
    recipe = build_recipe(recipe_request)
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
