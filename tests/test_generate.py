import asyncio

import httpx

from app.core.config import Settings
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
        assert isinstance(body["dish_summary"], str)
        assert body["dish_summary"]
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


def test_generate_returns_503_with_stable_error_when_generation_unavailable(
    monkeypatch,
) -> None:
    class BrokenGenerator:
        def generate(self, _request):
            raise RuntimeError("non-retryable backend failure")

    monkeypatch.setattr("app.api.generate.get_generator", lambda _settings=None: BrokenGenerator())
    monkeypatch.setattr(
        "app.api.generate.get_settings",
        lambda: Settings(
            recipe_generator="openai",
            openai_api_key="test-key",
            openai_fallback_to_stub=False,
        ),
    )

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/generate", json={"ingredients": ["chicken"]})
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["code"] == "generation_unavailable"
        assert body["detail"]["message"] == (
            "Recipe generation is temporarily unavailable. Please try again."
        )
        assert "non-retryable backend failure" not in resp.text

    asyncio.run(run())


def test_generate_logs_safe_structured_fields_without_sensitive_data(monkeypatch, caplog) -> None:
    class BrokenGenerator:
        def generate(self, _request):
            raise RuntimeError("backend secret details")

    monkeypatch.setattr("app.api.generate.get_generator", lambda _settings=None: BrokenGenerator())
    monkeypatch.setattr(
        "app.api.generate.get_settings",
        lambda: Settings(
            recipe_generator="openai",
            openai_api_key="test-key",
            openai_fallback_to_stub=False,
        ),
    )

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with caplog.at_level("WARNING", logger="app.api.generate"):
                resp = await client.post("/generate", json={"theme": "Italian", "ingredients": ["chicken"]})
        assert resp.status_code == 503

    asyncio.run(run())

    records = [r for r in caplog.records if r.msg == "api_recipe_generation"]
    assert records
    record = records[-1]
    assert record.outcome == "failure"
    assert record.generator_mode == "openai"
    assert record.error_class == "RuntimeError"
    assert hasattr(record, "has_theme")
    assert hasattr(record, "ingredients_count")
    assert hasattr(record, "healthy")
    assert hasattr(record, "quick_easy")
    assert "backend secret details" not in caplog.text
    assert "test-key" not in caplog.text
