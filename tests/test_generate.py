import asyncio

import httpx

from app.main import app


def test_generate_happy_path_returns_200_and_schema_shape() -> None:
    payload = {
        "theme": "Italian",
        "ingredients": ["tomato", "basil"],
        "healthy": True,
        "quick_easy": False,
        "notes": "No nuts",
    }

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/generate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["id"], str)
        assert isinstance(body["title"], str)
        assert isinstance(body["servings"], int)
        assert isinstance(body["time_minutes"], int)
        assert isinstance(body["difficulty"], str)
        assert isinstance(body["ingredients"], list)
        assert isinstance(body["steps"], list)
        assert isinstance(body["substitutions"], list)
        assert isinstance(body["cook_mode"], dict)
        assert isinstance(body["cook_mode"]["ingredients_checklist"], list)
        assert isinstance(body["cook_mode"]["step_cards"], list)

    asyncio.run(run())


def test_generate_reflects_input_ingredients() -> None:
    payload = {
        "ingredients": ["chicken", "rice", "garlic"],
    }

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/generate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        names = [item["name"] for item in body["ingredients"]]
        assert names == ["chicken", "rice", "garlic"]

    asyncio.run(run())


def test_generate_rejects_invalid_payload_shape() -> None:
    payload = {
        "ingredients": "not-a-list",
    }

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/generate", json=payload)
        assert resp.status_code == 422

    asyncio.run(run())
