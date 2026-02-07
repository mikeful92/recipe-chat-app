import asyncio
import json
from pathlib import Path

import httpx

from app.db.sqlite import init_db
from app.main import app


def _set_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RECIPE_DB_PATH", str(tmp_path / "recipes.db"))
    init_db()


def _recipe_payload(recipe_id: str, title: str) -> dict:
    return {
        "id": recipe_id,
        "title": title,
        "servings": 2,
        "time_minutes": 20,
        "difficulty": "easy",
        "ingredients": [
            {"name": "chickpeas", "amount": "1", "unit": "can", "optional": False},
        ],
        "steps": [
            {"step": 1, "text": "Warm chickpeas.", "timer_minutes": 5},
        ],
        "substitutions": ["Use white beans."],
        "cook_mode": {
            "ingredients_checklist": ["chickpeas"],
            "step_cards": ["Warm chickpeas."],
        },
    }


def test_root_includes_multiline_ingredients_placeholder(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
            assert resp.status_code == 200
            assert "placeholder=\"chicken&#10;spinach&#10;lemon\"" in resp.text

    asyncio.run(run())


def test_ui_save_redirects_to_recipe_detail(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            generate_resp = await client.post(
                "/generate",
                json={
                    "theme": "Italian",
                    "ingredients": ["chicken", "spinach"],
                    "healthy": True,
                    "quick_easy": True,
                },
            )
            assert generate_resp.status_code == 200
            recipe = generate_resp.json()

            save_resp = await client.post(
                "/ui/save",
                data={"recipe_json": json.dumps(recipe)},
                follow_redirects=False,
            )
            assert save_resp.status_code == 303
            assert save_resp.headers["location"] == f"/recipes/ui/{recipe['id']}"

            detail_resp = await client.get(save_resp.headers["location"])
            assert detail_resp.status_code == 200
            assert recipe["title"] in detail_resp.text

    asyncio.run(run())


def test_recipes_ui_lists_newest_first(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    older = _recipe_payload("older-ui", "Older UI Recipe")
    newer = _recipe_payload("newer-ui", "Newer UI Recipe")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/recipes", json=older)
            assert first.status_code == 200
            await asyncio.sleep(0.02)
            second = await client.post("/recipes", json=newer)
            assert second.status_code == 200

            list_resp = await client.get("/recipes/ui")
            assert list_resp.status_code == 200
            body = list_resp.text
            assert body.index("Newer UI Recipe") < body.index("Older UI Recipe")

    asyncio.run(run())


def test_recipe_detail_ui_shows_notes_and_add_note_form(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    payload = _recipe_payload("note-ui", "Recipe With Notes")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            save_resp = await client.post("/recipes", json=payload)
            assert save_resp.status_code == 200

            add_note_resp = await client.post(
                "/recipes/ui/note-ui/notes",
                data={"note_text": "Nice with extra lemon"},
                follow_redirects=False,
            )
            assert add_note_resp.status_code == 303
            assert add_note_resp.headers["location"] == "/recipes/ui/note-ui"

            detail_resp = await client.get("/recipes/ui/note-ui")
            assert detail_resp.status_code == 200
            assert "Add note" in detail_resp.text
            assert "Nice with extra lemon" in detail_resp.text

    asyncio.run(run())


def test_cook_mode_missing_recipe_returns_404(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/cook/missing")
            assert resp.status_code == 404

    asyncio.run(run())


def test_ui_save_invalid_recipe_json_returns_400(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/ui/save",
                data={"recipe_json": "{\"id\":"},
                follow_redirects=False,
            )
            assert resp.status_code == 400
            assert resp.json()["detail"] == "Invalid recipe payload"

    asyncio.run(run())


def test_ui_save_duplicate_recipe_redirects_to_existing_detail(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            generate_resp = await client.post(
                "/generate",
                json={
                    "theme": "Duplicate Save",
                    "ingredients": ["tomato"],
                    "healthy": False,
                    "quick_easy": True,
                },
            )
            assert generate_resp.status_code == 200
            recipe = generate_resp.json()
            recipe_json = json.dumps(recipe)

            first_save = await client.post(
                "/ui/save",
                data={"recipe_json": recipe_json},
                follow_redirects=False,
            )
            second_save = await client.post(
                "/ui/save",
                data={"recipe_json": recipe_json},
                follow_redirects=False,
            )

            expected_location = f"/recipes/ui/{recipe['id']}"
            assert first_save.status_code == 303
            assert second_save.status_code == 303
            assert first_save.headers["location"] == expected_location
            assert second_save.headers["location"] == expected_location

    asyncio.run(run())
