from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path

from script2video.config import load_project
from script2video.engines.fake import FakeEngine
from script2video.pipeline import render_project


class RenderPipelineTests(unittest.TestCase):
    def test_renders_scene_files_narration_and_exact_manifest_timing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "project.yaml"
            output = root / "build"
            script.write_text(
                """\
title: Test Project
language: en-US
engine: fake
voice: test_narrator
scenes:
  - id: intro
    text: Hello world.
    pause_after_ms: 250
  - id: ending
    text: Goodbye.
    voice: test_low
""",
                encoding="utf-8",
            )

            manifest = render_project(
                load_project(script), script, output, FakeEngine()
            )

            self.assertTrue((output / "scenes/001-intro.wav").is_file())
            self.assertTrue((output / "scenes/002-ending.wav").is_file())
            self.assertTrue((output / "narration.wav").is_file())
            self.assertTrue((output / "manifest.json").is_file())
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["engine"]["name"], "fake")
            self.assertEqual(
                manifest["scenes"][1]["start_sample"],
                manifest["scenes"][0]["end_sample"],
            )
            self.assertEqual(
                manifest["audio"]["duration_samples"],
                manifest["scenes"][-1]["end_sample"],
            )

            with wave.open(str(output / "narration.wav"), "rb") as audio:
                self.assertEqual(audio.getframerate(), 24_000)
                self.assertEqual(
                    audio.getnframes(), manifest["audio"]["duration_samples"]
                )

            persisted = json.loads((output / "manifest.json").read_text())
            self.assertEqual(persisted["scenes"], manifest["scenes"])


if __name__ == "__main__":
    unittest.main()
