from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from script2video.errors import VideoProbeError
from script2video.video import _find_ffprobe, probe_video


class VideoProbeTests(unittest.TestCase):
    def test_uses_explicit_ffprobe_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "ffprobe.exe"
            executable.touch()
            with (
                patch.dict("os.environ", {"FFPROBE": str(executable)}, clear=False),
                patch("script2video.video.shutil.which", return_value=None),
            ):
                self.assertEqual(_find_ffprobe(), str(executable))

    def test_finds_winget_ffprobe_before_path_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = (
                Path(directory) / "Microsoft" / "WinGet" / "Links" / "ffprobe.exe"
            )
            executable.parent.mkdir(parents=True)
            executable.touch()
            with (
                patch.dict(
                    "os.environ",
                    {"LOCALAPPDATA": directory, "FFPROBE": ""},
                    clear=False,
                ),
                patch("script2video.video.shutil.which", return_value=None),
                patch("script2video.video.sys.platform", "win32"),
            ):
                self.assertEqual(_find_ffprobe(), str(executable))

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
