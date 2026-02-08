import asyncio
from pathlib import Path

import httpx

from app.core.config import Settings
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


def test_ui_generate_failure_redirects_to_form_with_generic_error(
    monkeypatch, tmp_path: Path
) -> None:
    _set_db(monkeypatch, tmp_path)

    class BrokenGenerator:
        def generate(self, _request):
            raise RuntimeError("boom")

    monkeypatch.setattr("app.api.ui.get_generator", lambda _settings=None: BrokenGenerator())

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/ui/generate",
                data={"theme": "Italian", "ingredients": "chicken"},
                follow_redirects=False,
            )
            assert resp.status_code == 303
            assert resp.headers["location"] == "/?error=1"

            page = await client.get(resp.headers["location"])
            assert page.status_code == 200
            assert "Something went wrong while generating your recipe." in page.text

    asyncio.run(run())


def test_ui_generate_openai_fallback_to_stub_when_enabled(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    class BrokenGenerator:
        def generate(self, _request):
            raise RuntimeError("openai unavailable")

    monkeypatch.setattr("app.api.ui.get_generator", lambda _settings=None: BrokenGenerator())
    monkeypatch.setattr(
        "app.api.ui.get_settings",
        lambda: Settings(
            recipe_generator="openai",
            openai_api_key="test-key",
            openai_fallback_to_stub=True,
        ),
    )

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/ui/generate",
                data={"theme": "Italian", "ingredients": "chicken"},
                follow_redirects=False,
            )
            assert resp.status_code == 200
            assert "Save recipe" in resp.text

    asyncio.run(run())


def test_ui_generate_openai_redirects_when_fallback_disabled(monkeypatch, tmp_path: Path) -> None:
    _set_db(monkeypatch, tmp_path)

    class BrokenGenerator:
        def generate(self, _request):
            raise RuntimeError("openai unavailable")

    monkeypatch.setattr("app.api.ui.get_generator", lambda _settings=None: BrokenGenerator())
    monkeypatch.setattr(
        "app.api.ui.get_settings",
        lambda: Settings(
            recipe_generator="openai",
            openai_api_key="test-key",
            openai_fallback_to_stub=False,
        ),
    )

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/ui/generate",
                data={"theme": "Italian", "ingredients": "chicken"},
                follow_redirects=False,
            )
            assert resp.status_code == 303
            assert resp.headers["location"] == "/?error=1"

    asyncio.run(run())


def test_ui_generate_logs_safe_structured_fields(monkeypatch, tmp_path: Path, caplog) -> None:
    _set_db(monkeypatch, tmp_path)

    class BrokenGenerator:
        def generate(self, _request):
            raise RuntimeError("sensitive backend reason")

    monkeypatch.setattr("app.api.ui.get_generator", lambda _settings=None: BrokenGenerator())
    monkeypatch.setattr(
        "app.api.ui.get_settings",
        lambda: Settings(
            recipe_generator="openai",
            openai_api_key="test-key",
            openai_fallback_to_stub=False,
        ),
    )

    async def run() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with caplog.at_level("WARNING", logger="app.api.ui"):
                resp = await client.post(
                    "/ui/generate",
                    data={"theme": "Italian", "ingredients": "chicken"},
                    follow_redirects=False,
                )
            assert resp.status_code == 303

    asyncio.run(run())

    records = [r for r in caplog.records if r.msg == "ui_recipe_generation"]
    assert records
    record = records[-1]
    assert record.outcome == "failure"
    assert record.generator_mode == "openai"
    assert record.error_class == "RuntimeError"
    assert hasattr(record, "has_theme")
    assert hasattr(record, "ingredients_count")
    assert hasattr(record, "healthy")
    assert hasattr(record, "quick_easy")
    assert "sensitive backend reason" not in caplog.text
    assert "test-key" not in caplog.text
