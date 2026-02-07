import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.sqlite import get_conn
from app.schemas.recipe import Recipe

router = APIRouter()


class RecipeNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_text: str
@router.post("/recipes")
async def save_recipe(recipe: Recipe) -> dict[str, str]:
    created_at = datetime.now(UTC).isoformat()
    recipe_json = recipe.model_dump_json()

    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO recipes (id, title, recipe_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (recipe.id, recipe.title, recipe_json, created_at),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Recipe already exists") from exc

    return {"id": recipe.id}


@router.get("/recipes")
async def list_recipes() -> list[dict[str, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at
            FROM recipes
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        {"id": str(row["id"]), "title": str(row["title"]), "created_at": str(row["created_at"])}
        for row in rows
    ]


@router.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str) -> Recipe:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT recipe_json
            FROM recipes
            WHERE id = ?
            """,
            (recipe_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return Recipe.model_validate_json(str(row["recipe_json"]))


@router.post("/recipes/{recipe_id}/notes")
async def add_note(recipe_id: str, payload: RecipeNoteCreate) -> dict[str, str]:
    note_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()

    with get_conn() as conn:
        recipe_row = conn.execute("SELECT 1 FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
        if recipe_row is None:
            raise HTTPException(status_code=404, detail="Recipe not found")

        conn.execute(
            """
            INSERT INTO notes (id, recipe_id, note_text, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (note_id, recipe_id, payload.note_text, created_at),
        )

    return {"note_id": note_id}


@router.get("/recipes/{recipe_id}/notes")
async def list_notes(recipe_id: str) -> list[dict[str, str]]:
    with get_conn() as conn:
        recipe_row = conn.execute("SELECT 1 FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
        if recipe_row is None:
            raise HTTPException(status_code=404, detail="Recipe not found")

        rows = conn.execute(
            """
            SELECT id, note_text, created_at
            FROM notes
            WHERE recipe_id = ?
            ORDER BY created_at DESC
            """,
            (recipe_id,),
        ).fetchall()

    return [
        {
            "note_id": str(row["id"]),
            "note_text": str(row["note_text"]),
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]
