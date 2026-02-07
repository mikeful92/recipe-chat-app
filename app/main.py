from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.generate import router as generate_router
from app.api.recipes import router as recipes_router
from app.api.ui import router as ui_router
from app.core.config import get_settings
from app.db.sqlite import init_db
from app.services.generator_factory import get_generator


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    get_generator(settings)
    init_db()
    yield


app = FastAPI(title="Recipe Chat App", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(ui_router)
app.include_router(generate_router)
app.include_router(recipes_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
