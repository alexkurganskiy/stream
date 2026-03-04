import bisect
from dataclasses import dataclass

SEGMENT_LEN_SEC = 2
WINDOW_SIZE = 6


@dataclass
class PlaylistVideo:
    id: int
    segments_count: int


@dataclass
class PlaylistConfig:
    videos: list[PlaylistVideo]
    total_segments: int
    prefix: list[int]


def build_playlist_config(videos: list[PlaylistVideo]) -> PlaylistConfig:
    playable_videos = [video for video in videos if video.segments_count > 0]

    prefix = [0]
    for video in playable_videos:
        prefix.append(prefix[-1] + video.segments_count)

    return PlaylistConfig(
        videos=playable_videos,
        total_segments=prefix[-1] if playable_videos else 0,
        prefix=prefix,
    )


def segment_pointer(global_segment: int, config: PlaylistConfig) -> tuple[int, int]:
    if not config.videos or config.total_segments <= 0:
        raise ValueError("playlist config is empty")

    offset = global_segment % config.total_segments
    video_idx = bisect.bisect_right(config.prefix, offset) - 1
    segment_idx = offset - config.prefix[video_idx]
    return video_idx, segment_idx


def render_live_m3u8(config: PlaylistConfig, sequence: int, window_size: int = WINDOW_SIZE) -> str:
    if not config.videos:
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    window_start = max(sequence - window_size + 1, 0)

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-INDEPENDENT-SEGMENTS",
        f"#EXT-X-TARGETDURATION:{SEGMENT_LEN_SEC}",
        f"#EXT-X-MEDIA-SEQUENCE:{window_start}",
    ]

    previous_video_id: int | None = None
    for idx in range(window_size):
        pointer = window_start + idx
        video_idx, segment_idx = segment_pointer(pointer, config)
        video = config.videos[video_idx]

        if previous_video_id is not None and previous_video_id != video.id:
            lines.append("#EXT-X-DISCONTINUITY")

        lines.append(f"#EXTINF:{SEGMENT_LEN_SEC},")
        lines.append(f"/live/ts/{video.id}/{segment_idx}?v={pointer}")
        previous_video_id = video.id

    return "\n".join(lines) + "\n"
