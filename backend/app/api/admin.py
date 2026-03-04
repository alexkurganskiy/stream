from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_redis
from app.models.models import PlaylistItem, Video
from app.services.live import LIVE_EPOCH0_KEY, LIVE_M3U8_KEY, LIVE_SEQ_KEY
from app.services.live_playlist import SEGMENT_LEN_SEC
from app.services.s3 import s3_service
from app.services.transcode import run_ffmpeg_to_hls

router = APIRouter(prefix="/admin", tags=["admin"])


class PlaylistUpdate(BaseModel):
    video_ids: list[int]


@router.post("/videos/upload")
async def upload_video(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)) -> dict[str, int]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="file name is required")

    video = Video(title=file.filename, s3_prefix="")
    db.add(video)
    await db.commit()
    await db.refresh(video)

    content = await file.read()
    source_key = f"vod/{video.id}/source.mp4"
    s3_service.put_object(source_key, content, content_type=file.content_type or "video/mp4")

    video.s3_prefix = f"vod/{video.id}/"
    await db.commit()
    return {"video_id": video.id}


@router.post("/videos/{video_id}/transcode_hls")
async def transcode_hls(video_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, int]:
    video = await db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_file = temp_path / "source.mp4"
        output_dir = temp_path / "hls"

        s3_service.download_file(f"vod/{video_id}/source.mp4", str(source_file))
        duration = await run_ffmpeg_to_hls(source_file, output_dir, segment_len=SEGMENT_LEN_SEC)

        index_path = output_dir / "index.m3u8"
        s3_service.put_object(f"vod/{video_id}/index.m3u8", index_path.read_bytes(), "application/vnd.apple.mpegurl")

        segments = sorted(output_dir.glob("seg_*.ts"))
        for segment in segments:
            s3_service.put_object(f"vod/{video_id}/{segment.name}", segment.read_bytes(), "video/mp2t")

    video.duration_sec = duration
    video.segment_len_sec = SEGMENT_LEN_SEC
    video.segments_count = len(segments)
    video.s3_prefix = f"vod/{video_id}/"
    await db.commit()

    return {"video_id": video_id, "segments_count": len(segments)}


@router.post("/playlist")
async def set_playlist(payload: PlaylistUpdate, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    rows = (await db.scalars(select(Video.id).where(Video.id.in_(payload.video_ids)))).all()
    if len(rows) != len(payload.video_ids):
        raise HTTPException(status_code=400, detail="some video_ids do not exist")

    await db.execute(delete(PlaylistItem))
    for position, video_id in enumerate(payload.video_ids):
        db.add(PlaylistItem(position=position, video_id=video_id))
    await db.commit()
    return {"status": "ok"}


@router.post("/stream/reset")
async def reset_stream(redis: Redis = Depends(get_redis)) -> dict[str, str]:
    await redis.delete(LIVE_M3U8_KEY)
    await redis.delete(LIVE_SEQ_KEY)
    await redis.delete(LIVE_EPOCH0_KEY)
    return {"status": "ok"}
