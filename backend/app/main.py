from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin import router as admin_router
from app.core.settings import get_settings
from app.db.session import get_db
from app.services.live import build_live_m3u8

settings = get_settings()
app = FastAPI(title="stream-backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/live.m3u8")
async def live_m3u8(db: AsyncSession = Depends(get_db)) -> Response:
    playlist = await build_live_m3u8(db)
    return Response(content=playlist, media_type="application/vnd.apple.mpegurl")
