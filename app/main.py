from fastapi import FastAPI

app = FastAPI(title="Recipe Chat App", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
