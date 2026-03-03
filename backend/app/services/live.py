from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PlaylistItem, StreamState, Video
from app.services.s3 import s3_service


@dataclass
class PlaylistVideo:
    id: int
    duration_sec: int
    segment_len_sec: int
    segments_count: int


async def build_live_m3u8(session: AsyncSession, window_size: int = 6) -> str:
    stmt = (
        select(Video)
        .join(PlaylistItem, PlaylistItem.video_id == Video.id)
        .order_by(PlaylistItem.position.asc())
    )
    videos = [
        PlaylistVideo(
            id=v.id,
            duration_sec=max(v.duration_sec, 1),
            segment_len_sec=max(v.segment_len_sec, 1),
            segments_count=max(v.segments_count, 1),
        )
        for v in (await session.scalars(stmt)).all()
    ]
    if not videos:
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    stream_state = await session.get(StreamState, 1)
    if stream_state is None:
        stream_state = StreamState(id=1, started_at=datetime.now(timezone.utc))
        session.add(stream_state)
        await session.commit()
        await session.refresh(stream_state)

    total_duration = sum(video.duration_sec for video in videos)
    elapsed = (datetime.now(timezone.utc) - stream_state.started_at).total_seconds()
    pos = int(elapsed % total_duration)

    video_idx = 0
    local_pos = pos
    for idx, video in enumerate(videos):
        if local_pos < video.duration_sec:
            video_idx = idx
            break
        local_pos -= video.duration_sec

    current_video = videos[video_idx]
    current_segment = min(current_video.segments_count - 1, local_pos // current_video.segment_len_sec)

    global_sequence = int(elapsed // current_video.segment_len_sec)
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{current_video.segment_len_sec}",
        f"#EXT-X-MEDIA-SEQUENCE:{global_sequence}",
    ]

    idx = video_idx
    seg = current_segment
    for _ in range(window_size):
        video = videos[idx]
        key = f"vod/{video.id}/seg_{seg:05d}.ts"
        url = s3_service.presign_get(key)
        lines.append(f"#EXTINF:{video.segment_len_sec},")
        lines.append(url)

        seg += 1
        if seg >= video.segments_count:
            idx = (idx + 1) % len(videos)
            seg = 0

    return "\n".join(lines) + "\n"
