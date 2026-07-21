from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from script2video.config import ProjectConfig, load_project
from script2video.errors import ScriptLoadError


class ProjectConfigTests(unittest.TestCase):
    def test_rejects_duplicate_scene_ids(self) -> None:
        with self.assertRaisesRegex(ValidationError, "scene IDs must be unique"):
            ProjectConfig.model_validate(
                {
                    "title": "Duplicate",
                    "language": "en-US",
                    "engine": "fake",
                    "voice": "test_narrator",
                    "scenes": [
                        {"id": "intro", "text": "One"},
                        {"id": "intro", "text": "Two"},
                    ],
                }
            )

    def test_rejects_unknown_fields_with_readable_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.yaml"
            path.write_text(
                """\
title: Bad
language: en-US
engine: fake
voice: test_narrator
unexpected: true
scenes:
  - id: intro
    text: Hello
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ScriptLoadError, "unexpected"):
                load_project(path)


if __name__ == "__main__":
    unittest.main()
