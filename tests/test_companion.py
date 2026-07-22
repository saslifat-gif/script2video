from __future__ import annotations

import unittest

from script2video.companion import build_generation_command


class CompanionCommandTests(unittest.TestCase):
    def test_builds_narration_command_without_video(self) -> None:
        command = build_generation_command(
            "python",
            "examples/demo.yaml",
            "builds/demo",
            voice="af_heart",
            fit=False,
            align=True,
        )

        self.assertEqual(
            command,
            [
                "python",
                "-m",
                "script2video",
                "render",
                "examples/demo.yaml",
                "--output",
                "builds/demo",
                "--voice",
                "af_heart",
            ],
        )

    def test_builds_capcut_command_when_video_is_selected(self) -> None:
        command = build_generation_command(
            "python",
            "examples/demo.yaml",
            "builds/demo-capcut",
            video="source.mp4",
            fit=False,
            align=False,
        )

        self.assertEqual(
            command,
            [
                "python",
                "-m",
                "script2video",
                "capcut",
                "examples/demo.yaml",
                "--video",
                "source.mp4",
                "--output",
                "builds/demo-capcut",
                "--no-fit",
                "--no-align",
            ],
        )


if __name__ == "__main__":
    unittest.main()
