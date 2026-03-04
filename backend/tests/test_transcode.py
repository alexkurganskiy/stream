import unittest
from pathlib import Path

from app.services.transcode import build_ffmpeg_hls_cmd


class TranscodeCommandTests(unittest.TestCase):
    def test_hls_command_forces_keyframes_for_segment_size(self) -> None:
        cmd = build_ffmpeg_hls_cmd(Path('/tmp/in.mp4'), Path('/tmp/out'), segment_len=2)
        joined = ' '.join(cmd)

        self.assertIn('-hls_time 2', joined)
        self.assertIn('-force_key_frames expr:gte(t,n_forced*2)', joined)
        self.assertIn('keyint=50:min-keyint=50:scenecut=0', joined)
        self.assertIn('-hls_flags independent_segments', joined)


if __name__ == '__main__':
    unittest.main()
