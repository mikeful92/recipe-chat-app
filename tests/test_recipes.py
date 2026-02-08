import asyncio
from pathlib import Path

import httpx

from app.db.sqlite import init_db
from app.main import app


def _recipe_payload(recipe_id: str = "recipe-1") -> dict:
    return {
        "id": recipe_id,
        "title": "Lemon Chickpea Bowl",
        "servings": 2,
        "time_minutes": 20,
        "difficulty": "easy",
        "dish_summary": "A bright, quick bowl with lemony chickpeas for a fast meal.",
        "ingredients": [
            {"name": "chickpeas", "amount": "1", "unit": "can", "optional": False},
            {"name": "lemon", "amount": "1", "unit": "item", "optional": False},
        ],
        "steps": [
            {"step": 1, "text": "Warm chickpeas.", "timer_minutes": 5},
            {"step": 2, "text": "Add lemon zest and serve.", "timer_minutes": None},
        ],
        "substitutions": ["Use white beans instead of chickpeas."],
        "cook_mode": {
            "ingredients_checklist": [
                {"name": "chickpeas", "amount": "1", "unit": "can", "optional": False},
                {"name": "lemon", "amount": "1", "unit": "item", "optional": False},
            ],
            "step_cards": ["Warm chickpeas.", "Add lemon zest and serve."],
        },
    }


def _set_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RECIPE_DB_PATH", str(tmp_path / "recipes.db"))
    init_db()


def test_save_then_list_includes_recipe(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)
    payload = _recipe_payload("list-me")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            save_resp = await client.post("/recipes", json=payload)
            assert save_resp.status_code == 200

            list_resp = await client.get("/recipes")
            assert list_resp.status_code == 200
            body = list_resp.json()
            assert len(body) == 1
            assert body[0]["id"] == "list-me"
            assert body[0]["title"] == payload["title"]
            assert "created_at" in body[0]

    asyncio.run(run())


def test_db_initialized_on_startup_uses_env_path(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "recipes.db"
    monkeypatch.setenv("RECIPE_DB_PATH", str(db_path))
    assert not db_path.exists()

    async def run() -> None:
        async with app.router.lifespan_context(app):
            pass

    asyncio.run(run())
    assert db_path.parent.exists()
    assert db_path.exists()


def test_save_then_get_returns_recipe_with_cook_mode(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)
    payload = _recipe_payload("fetch-me")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            save_resp = await client.post("/recipes", json=payload)
            assert save_resp.status_code == 200

            get_resp = await client.get("/recipes/fetch-me")
            assert get_resp.status_code == 200
            body = get_resp.json()
            assert body["title"] == payload["title"]
            assert body["dish_summary"] == payload["dish_summary"]
            assert "cook_mode" in body
            assert "ingredients_checklist" in body["cook_mode"]

    asyncio.run(run())


def test_save_recipe_without_summary_returns_422(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)
    payload = _recipe_payload("missing-summary")
    payload.pop("dish_summary")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            save_resp = await client.post("/recipes", json=payload)
            assert save_resp.status_code == 422

    asyncio.run(run())


def test_saving_same_recipe_id_twice_returns_409(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)
    payload = _recipe_payload("duplicate-id")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/recipes", json=payload)
            second = await client.post("/recipes", json=payload)

            assert first.status_code == 200
            assert second.status_code == 409

    asyncio.run(run())


def test_list_recipes_returns_newest_first(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)
    first = _recipe_payload("older")
    second = _recipe_payload("newer")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/recipes", json=first)
            await asyncio.sleep(0.02)
            await client.post("/recipes", json=second)

            list_resp = await client.get("/recipes")
            assert list_resp.status_code == 200
            body = list_resp.json()
            assert [item["id"] for item in body] == ["newer", "older"]

    asyncio.run(run())


def test_add_note_then_list_notes_returns_it(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)
    payload = _recipe_payload("note-parent")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            save_resp = await client.post("/recipes", json=payload)
            assert save_resp.status_code == 200

            note_resp = await client.post(
                "/recipes/note-parent/notes",
                json={"note_text": "Great with extra herbs"},
            )
            assert note_resp.status_code == 200
            note_body = note_resp.json()
            assert "note_id" in note_body

            list_resp = await client.get("/recipes/note-parent/notes")
            assert list_resp.status_code == 200
            list_body = list_resp.json()
            assert len(list_body) == 1
            assert list_body[0]["note_id"] == note_body["note_id"]
            assert list_body[0]["note_text"] == "Great with extra herbs"
            assert "created_at" in list_body[0]

    asyncio.run(run())


def test_list_notes_returns_newest_first(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)
    payload = _recipe_payload("note-order")

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            save_resp = await client.post("/recipes", json=payload)
            assert save_resp.status_code == 200

            first_note_resp = await client.post(
                "/recipes/note-order/notes",
                json={"note_text": "older note"},
            )
            assert first_note_resp.status_code == 200
            await asyncio.sleep(0.02)
            second_note_resp = await client.post(
                "/recipes/note-order/notes",
                json={"note_text": "newer note"},
            )
            assert second_note_resp.status_code == 200

            list_resp = await client.get("/recipes/note-order/notes")
            assert list_resp.status_code == 200
            list_body = list_resp.json()
            assert [item["note_text"] for item in list_body] == ["newer note", "older note"]

    asyncio.run(run())


def test_unknown_recipe_id_returns_404_for_get_and_notes(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            get_resp = await client.get("/recipes/missing")
            notes_resp = await client.get("/recipes/missing/notes")
            add_note_resp = await client.post("/recipes/missing/notes", json={"note_text": "x"})

            assert get_resp.status_code == 404
            assert notes_resp.status_code == 404
            assert add_note_resp.status_code == 404

    asyncio.run(run())
