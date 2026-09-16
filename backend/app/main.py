import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import router
from app.config import ROOT, settings
from app.db.session import init_db
from app.telegram.bot import run_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = None
    if settings.telegram_bot_token:
        task = asyncio.create_task(run_bot())
    yield
    if task:
        task.cancel()


app = FastAPI(title="AI Personal Development Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

dist = ROOT / "frontend" / "dist"


@app.get("/health")
def health():
    return {"ok": True}


if dist.exists():
    @app.get("/")
    def index():
        return FileResponse(dist / "index.html")
