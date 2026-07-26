from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from script2video.cli import app


class CliTests(unittest.TestCase):
    def test_render_allows_engine_and_voice_overrides(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "build"
            result = runner.invoke(
                app,
                [
                    "render",
                    "examples/demo.yaml",
                    "--engine",
                    "fake",
                    "--voice",
                    "test_narrator",
                    "--output",
                    str(output),
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Rendered 2 scenes", result.output)
            self.assertTrue((output / "narration.wav").is_file())
            self.assertTrue((output / "manifest.json").is_file())

    def test_render_srt_command_splits_cues(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.srt"
            script.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nOne.\n\n"
                "2\n00:00:01,200 --> 00:00:02,000\nTwo.\n",
                encoding="utf-8",
            )
            output = root / "build"
            result = runner.invoke(
                app,
                [
                    "render-srt",
                    str(script),
                    "--engine",
                    "fake",
                    "--voice",
                    "test_narrator",
                    "--output",
                    str(output),
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Rendered 2 SRT scenes", result.output)
            self.assertTrue((output / "narration.wav").is_file())


if __name__ == "__main__":
    unittest.main()
