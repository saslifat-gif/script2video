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


if __name__ == "__main__":
    unittest.main()
