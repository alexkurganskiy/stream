import unittest

from app.services.live_playlist import (
    PlaylistConfig,
    PlaylistVideo,
    build_playlist_config,
    render_live_m3u8,
    segment_pointer,
)


class LivePlaylistTests(unittest.TestCase):
    def test_window_wraparound(self) -> None:
        config = PlaylistConfig(
            videos=[PlaylistVideo(id=10, segments_count=2), PlaylistVideo(id=20, segments_count=3)],
            total_segments=5,
            prefix=[0, 2, 5],
        )

        pointers = [segment_pointer(4 + idx, config) for idx in range(6)]
        self.assertEqual(pointers, [(1, 2), (0, 0), (0, 1), (1, 0), (1, 1), (1, 2)])

    def test_media_sequence_monotonic(self) -> None:
        config = PlaylistConfig(
            videos=[PlaylistVideo(id=1, segments_count=2)],
            total_segments=2,
            prefix=[0, 2],
        )

        first = render_live_m3u8(config, sequence=100)
        second = render_live_m3u8(config, sequence=101)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:95", first)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:96", second)

    def test_playlist_text_shape(self) -> None:
        config = PlaylistConfig(
            videos=[PlaylistVideo(id=7, segments_count=2)],
            total_segments=2,
            prefix=[0, 2],
        )

        text = render_live_m3u8(config, sequence=3)
        self.assertTrue(text.startswith("#EXTM3U\n"))
        self.assertIn("#EXT-X-TARGETDURATION:2", text)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:0", text)
        self.assertIn("/live/ts/7/1?v=3", text)


    def test_segment_urls_are_unique_across_loops(self) -> None:
        config = PlaylistConfig(
            videos=[PlaylistVideo(id=9, segments_count=2)],
            total_segments=2,
            prefix=[0, 2],
        )

        first = render_live_m3u8(config, sequence=0)
        second = render_live_m3u8(config, sequence=2)
        self.assertIn("/live/ts/9/0?v=0", first)
        self.assertIn("/live/ts/9/0?v=2", second)

    def test_discontinuity_inserted_between_videos(self) -> None:
        config = PlaylistConfig(
            videos=[PlaylistVideo(id=1, segments_count=1), PlaylistVideo(id=2, segments_count=1)],
            total_segments=2,
            prefix=[0, 1, 2],
        )

        text = render_live_m3u8(config, sequence=0, window_size=2)
        self.assertIn("#EXT-X-INDEPENDENT-SEGMENTS", text)
        self.assertIn("#EXT-X-DISCONTINUITY", text)

    def test_build_playlist_config_skips_untranscoded_videos(self) -> None:
        config = build_playlist_config(
            [
                PlaylistVideo(id=1, segments_count=0),
                PlaylistVideo(id=2, segments_count=3),
                PlaylistVideo(id=3, segments_count=-1),
            ]
        )

        self.assertEqual([video.id for video in config.videos], [2])
        self.assertEqual(config.total_segments, 3)
        self.assertEqual(config.prefix, [0, 3])


if __name__ == "__main__":
    unittest.main()
