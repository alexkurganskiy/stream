import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from botocore.exceptions import ClientError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin import router as admin_router
from app.core.settings import get_settings
from app.db.session import SessionLocal, get_db
from app.services.live import LIVE_M3U8_KEY, PlaylistConfigCache, build_live_m3u8, live_playlist_loop
from app.services.s3 import s3_service

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis
    app.state.playlist_cache = PlaylistConfigCache()
    app.state.live_task = asyncio.create_task(live_playlist_loop(SessionLocal, redis))

    try:
        yield
    finally:
        app.state.live_task.cancel()
        try:
            await app.state.live_task
        except asyncio.CancelledError:
            pass
        await redis.close()


app = FastAPI(title="stream-backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)


@app.middleware("http")
async def request_time_logger(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "request_at=%s method=%s path=%s query=%s status=%s duration_ms=%.1f",
        datetime.now(timezone.utc).isoformat(),
        request.method,
        request.url.path,
        request.url.query,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/live/index.m3u8")
@app.get("/live.m3u8")
async def live_m3u8(db: AsyncSession = Depends(get_db)) -> Response:
    redis: Redis = app.state.redis
    text = await redis.get(LIVE_M3U8_KEY)

    if not text:
        logger.warning("live:m3u8 missing in redis, generating fallback")
        cache: PlaylistConfigCache = app.state.playlist_cache
        text = await build_live_m3u8(db, redis=redis, cache=cache)

    if not text:
        return Response(
            content="live playlist is not ready\n",
            media_type="text/plain",
            status_code=503,
            headers={"Cache-Control": "private, max-age=1, must-revalidate", "Retry-After": "2"},
        )

    return Response(
        content=text,
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "private, max-age=1, must-revalidate"},
    )


@app.get("/live/ts/{video_id}/{segment_idx}")
async def live_segment(video_id: int, segment_idx: int, v: int | None = None) -> Response:
    _ = v
    key = f"vod/{video_id}/seg_{segment_idx:05d}.ts"
    try:
        body = s3_service.get_object(key)
    except ClientError as exc:
        error = exc.response.get("Error", {})
        if error.get("Code") in {"NoSuchKey", "404"}:
            logger.warning("live segment missing key=%s", key)
            return Response(content="segment is not ready\n", media_type="text/plain", status_code=404)
        raise
    return Response(content=body, media_type="video/mp2t", headers={"Cache-Control": "public, max-age=31536000, immutable"})
