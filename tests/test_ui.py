import asyncio
from pathlib import Path

import httpx

from app.db.sqlite import init_db
from app.main import app


def _set_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RECIPE_DB_PATH", str(tmp_path / "recipes.db"))
    init_db()


def test_get_root_renders_generate_page(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
            assert resp.status_code == 200
            assert "Generate Recipe" in resp.text

    asyncio.run(run())


def test_ui_generate_then_api_save_then_cook_page(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            generate_ui_resp = await client.post(
                "/ui/generate",
                data={
                    "theme": "Italian",
                    "ingredients": "chicken\nspinach",
                    "healthy": "on",
                    "quick_easy": "on",
                },
            )
            assert generate_ui_resp.status_code == 200
            assert "Save recipe" in generate_ui_resp.text

            generate_api_resp = await client.post(
                "/generate",
                json={
                    "theme": "Italian",
                    "ingredients": ["chicken", "spinach"],
                    "healthy": True,
                    "quick_easy": True,
                },
            )
            assert generate_api_resp.status_code == 200
            recipe = generate_api_resp.json()

            save_resp = await client.post("/recipes", json=recipe)
            assert save_resp.status_code == 200

            cook_resp = await client.get(f"/cook/{recipe['id']}")
            assert cook_resp.status_code == 200
            assert "Cook Mode" in cook_resp.text

    asyncio.run(run())
