"""기존 프로필 API와 로컬 목업을 같은 origin에서 실행. DB에 접속하지 않는다."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from api.main import app

@app.get("/", include_in_schema=False)
def demo_home():
    return RedirectResponse("/mockup/")

app.mount("/design-system", StaticFiles(directory=ROOT / "design-system"), name="design-system")
app.mount("/mockup", StaticFiles(directory=ROOT / "mockup", html=True), name="trip-demo")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8129)
