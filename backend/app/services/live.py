import asyncio
import logging
import time

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.models import PlaylistItem, Video
from app.services.live_playlist import (
    PlaylistConfig,
    PlaylistVideo,
    SEGMENT_LEN_SEC,
    WINDOW_SIZE,
    render_live_m3u8,
    segment_pointer,
)

logger = logging.getLogger(__name__)

LIVE_EPOCH0_KEY = "live:epoch0"
LIVE_SEQ_KEY = "live:seq"
LIVE_M3U8_KEY = "live:m3u8"
LIVE_LOCK_KEY = "live:lock"

LOCK_TTL_SEC = 3
M3U8_TTL_SEC = 5
CONFIG_CACHE_TTL_SEC = 15
LOG_EVERY_SEC = 20


class PlaylistConfigCache:
    def __init__(self, ttl_sec: int = CONFIG_CACHE_TTL_SEC) -> None:
        self.ttl_sec = ttl_sec
        self._config: PlaylistConfig | None = None
        self._expires_at = 0.0

    async def get(self, session: AsyncSession) -> PlaylistConfig:
        now = time.monotonic()
        if self._config is not None and now < self._expires_at:
            return self._config

        stmt = (
            select(Video)
            .join(PlaylistItem, PlaylistItem.video_id == Video.id)
            .order_by(PlaylistItem.position.asc())
        )
        videos = [
            PlaylistVideo(
                id=video.id,
                segments_count=max(video.segments_count, 1),
            )
            for video in (await session.scalars(stmt)).all()
        ]

        prefix = [0]
        for video in videos:
            prefix.append(prefix[-1] + video.segments_count)

        config = PlaylistConfig(videos=videos, total_segments=prefix[-1] if videos else 0, prefix=prefix)
        self._config = config
        self._expires_at = now + self.ttl_sec
        return config


async def get_or_init_epoch0(redis: Redis) -> int:
    epoch0 = await redis.get(LIVE_EPOCH0_KEY)
    if epoch0 is not None:
        return int(epoch0)

    now_ts = int(time.time())
    was_set = await redis.set(LIVE_EPOCH0_KEY, now_ts, nx=True)
    if was_set:
        return now_ts

    stored = await redis.get(LIVE_EPOCH0_KEY)
    return int(stored) if stored is not None else now_ts


async def build_live_m3u8(session: AsyncSession, redis: Redis, cache: PlaylistConfigCache, window_size: int = WINDOW_SIZE) -> str:
    config = await cache.get(session)
    if not config.videos:
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    epoch0 = await get_or_init_epoch0(redis)
    now_ts = int(time.time())
    sequence = max((now_ts - epoch0) // SEGMENT_LEN_SEC, 0)
    return render_live_m3u8(config=config, sequence=sequence, window_size=window_size)


async def live_playlist_loop(session_factory: async_sessionmaker[AsyncSession], redis: Redis) -> None:
    cache = PlaylistConfigCache()
    worker_id = f"worker-{id(cache)}"
    last_log_at = 0.0

    while True:
        try:
            lock_acquired = await redis.set(LIVE_LOCK_KEY, worker_id, ex=LOCK_TTL_SEC, nx=True)
            if not lock_acquired:
                await asyncio.sleep(1)
                continue

            async with session_factory() as session:
                config = await cache.get(session)

            if config.videos:
                epoch0 = await get_or_init_epoch0(redis)
                now_ts = int(time.time())
                sequence = max((now_ts - epoch0) // SEGMENT_LEN_SEC, 0)
                playlist = render_live_m3u8(config=config, sequence=sequence, window_size=WINDOW_SIZE)
                await redis.set(LIVE_SEQ_KEY, sequence)
                await redis.set(LIVE_M3U8_KEY, playlist, ex=M3U8_TTL_SEC)

                now_mono = time.monotonic()
                if now_mono - last_log_at >= LOG_EVERY_SEC:
                    first_video_idx, first_seg = segment_pointer(sequence, config)
                    first_url = f"/live/ts/{config.videos[first_video_idx].id}/{first_seg}"
                    logger.info("live playlist updated seq=%s first_url=%s", sequence, first_url)
                    last_log_at = now_mono

            await redis.expire(LIVE_LOCK_KEY, LOCK_TTL_SEC)
        except Exception:
            logger.exception("live playlist loop iteration failed")

        await asyncio.sleep(1)
