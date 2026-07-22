from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from script2video.errors import VideoProbeError
from script2video.video import probe_video


class VideoProbeTests(unittest.TestCase):
    def test_reads_duration_from_ffprobe_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.touch()

            def runner(
                *args: object, **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout=(
                        '{"format":{"duration":"12.5"},'
                        '"streams":[{"width":1920,"height":1080}]}'
                    ),
                )

            info = probe_video(video, runner=runner)

            self.assertEqual(info.duration_seconds, 12.5)
            self.assertEqual(info.path, video.resolve())
            self.assertEqual(info.width, 1920)
            self.assertEqual(info.height, 1080)

    def test_rejects_unreadable_video(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "bad.mp4"
            video.touch()

            def runner(
                *args: object, **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args=args, returncode=1, stdout="", stderr="invalid data"
                )

            with self.assertRaisesRegex(VideoProbeError, "invalid data"):
                probe_video(video, runner=runner)


if __name__ == "__main__":
    unittest.main()
