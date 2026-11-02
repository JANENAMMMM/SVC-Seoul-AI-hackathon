"""반걸음 FastAPI. 실행: uv run uvicorn api.main:app --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="반걸음 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
