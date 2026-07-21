from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from script2video.capcut import create_capcut_package
from script2video.config import load_project
from script2video.engines.fake import FakeEngine
from script2video.video import VideoInfo


class CapCutPackageTests(unittest.TestCase):
    def test_fits_narration_and_generates_srt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.yaml"
            video = root / "video.mp4"
            output = root / "package"
            video.touch()
            script.write_text(
                """\
title: Fit Test
language: en-US
engine: fake
voice: test_narrator
scenes:
  - id: intro
    text: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
""",
                encoding="utf-8",
            )
            with patch(
                "script2video.capcut.probe_video",
                return_value=VideoInfo(video.resolve(), 2.0),
            ):
                manifest = create_capcut_package(
                    load_project(script), script, video, output, FakeEngine()
                )

            self.assertTrue((output / "narration.wav").is_file())
            self.assertTrue((output / "captions.srt").is_file())
            self.assertEqual(manifest["audio"]["duration_ms"], 2_000.0)
            self.assertTrue(manifest["capcut"]["fit"]["applied"])
            self.assertTrue(manifest["capcut"]["fit"]["converged"])
            self.assertEqual(manifest["capcut"]["fit"]["iterations"], 1)
            self.assertEqual(manifest["capcut"]["fit"]["speed_factor"], 0.5)
            self.assertEqual(manifest["scenes"][0]["speed"], 0.5)
            persisted = json.loads((output / "manifest.json").read_text())
            self.assertEqual(persisted["capcut"], manifest["capcut"])


if __name__ == "__main__":
    unittest.main()
