import asyncio
import json
from pathlib import Path


def build_ffmpeg_hls_cmd(source_file: Path, output_dir: Path, segment_len: int) -> list[str]:
    segment_expr = f"expr:gte(t,n_forced*{segment_len})"
    gop = segment_len * 25

    return [
        "ffmpeg",
        "-y",
        "-i",
        str(source_file),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-profile:v",
        "main",
        "-x264-params",
        f"keyint={gop}:min-keyint={gop}:scenecut=0",
        "-force_key_frames",
        segment_expr,
        "-c:a",
        "aac",
        "-hls_time",
        str(segment_len),
        "-hls_playlist_type",
        "vod",
        "-hls_flags",
        "independent_segments",
        "-hls_segment_filename",
        str(output_dir / "seg_%05d.ts"),
        str(output_dir / "index.m3u8"),
    ]


async def run_ffmpeg_to_hls(source_file: Path, output_dir: Path, segment_len: int = 2) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_hls_cmd(source_file, output_dir, segment_len)

    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    return await probe_duration(source_file)


async def probe_duration(source_file: Path) -> int:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        str(source_file),
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

    payload = json.loads(stdout.decode())
    return max(1, round(float(payload["format"]["duration"])))
