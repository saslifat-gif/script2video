from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from script2video.errors import ScriptLoadError
from script2video.srt import load_srt_project, parse_srt, project_from_srt

SAMPLE_SRT = """\
1
00:00:01,000 --> 00:00:03,200
<i>Welcome to the story.</i>

2
00:00:04.000 --> 00:00:06.500 position:50%
This subtitle uses
two lines.
"""


class SrtTests(unittest.TestCase):
    def test_parses_multiline_cues_and_formatting(self) -> None:
        cues = parse_srt("\ufeff" + SAMPLE_SRT.replace("\n", "\r\n"))

        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].end_ms, 3200)
        self.assertEqual(cues[0].text, "Welcome to the story.")
        self.assertEqual(cues[1].text, "This subtitle uses two lines.")

    def test_each_srt_cue_becomes_a_scene_and_preserves_gap(self) -> None:
        project = project_from_srt(
            SAMPLE_SRT,
            language="en-US",
            engine="fake",
            voice="test_narrator",
            title="Whole script",
        )

        self.assertEqual(project.title, "Whole script")
        self.assertEqual(
            [scene.id for scene in project.scenes],
            ["subtitle-001", "subtitle-002"],
        )
        self.assertEqual(project.scenes[0].pause_after_ms, 800)
        self.assertEqual(project.scenes[1].pause_after_ms, 0)
        self.assertIn("1000ms-3200ms", project.scenes[0].notes or "")

    def test_loads_utf8_srt_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episode.srt"
            path.write_text(SAMPLE_SRT, encoding="utf-8-sig")

            project = load_srt_project(path, "en-US", "fake", "test_narrator")

        self.assertEqual(project.title, "episode")
        self.assertEqual(len(project.scenes), 2)

    def test_rejects_invalid_timing(self) -> None:
        with self.assertRaisesRegex(ScriptLoadError, "end time must be after"):
            parse_srt(
                "1\n00:00:03,000 --> 00:00:02,000\nInvalid timing\n"
            )


if __name__ == "__main__":
    unittest.main()
