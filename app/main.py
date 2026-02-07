from fastapi import FastAPI

from app.api.generate import router as generate_router

app = FastAPI(title="Recipe Chat App", version="0.1.0")
app.include_router(generate_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
