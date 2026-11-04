"""반걸음 FastAPI. 실행: uv run uvicorn api.main:app --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.hitl import router as hitl_router
from api.routes.planner import router as planner_router
from api.routes.profile import router as profile_router
from api.scoring import router as scoring_router
from api.ui import router as ui_router, md_allowed
from fastapi import Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="반걸음 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.include_router(profile_router)
app.include_router(scoring_router)
app.include_router(planner_router)
app.include_router(hitl_router)
app.include_router(ui_router)


@app.middleware("http")
async def ui_security(request: Request, call_next):
    # Legacy HITL routes have no trip ownership. UI customers use owned /api/ui/trips routes.
    if request.url.path.startswith("/api/hitl") and not md_allowed(request):
        return JSONResponse({"detail": "운영자 로그인 또는 여행 소유자 API를 사용하세요."}, status_code=403)
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "다른 사이트에서의 변경 요청은 허용되지 않습니다."}, status_code=403)
    try:
        response = await call_next(request)
    except Exception:
        # Driver/LLM exceptions may contain request details; never send them to the browser.
        return JSONResponse({"detail": "요청을 처리하지 못했습니다. 현재 일정은 유지됩니다."}, status_code=503)
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/ui"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


FRONTEND = Path(__file__).resolve().parents[1] / "frontend/dist"
if FRONTEND.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="ui-assets")

    @app.get("/")
    @app.get("/share/{token}")
    def ui_page(token: str = ""):
        return FileResponse(FRONTEND / "index.html")

    @app.get("/demo.json")
    def demo_fixture():
        return FileResponse(FRONTEND / "demo.json", media_type="application/json")
