from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from script2video.webapp import (
    GenerationJob,
    _bootstrap_payload,
    _default_output_path,
    _open_path,
    _project_from_text,
    _run_generation_job,
    _run_text_generation_job,
    _update_payload,
    _version_tuple,
)


class WebAppTests(unittest.TestCase):
    def test_bootstrap_exposes_local_defaults(self) -> None:
        payload = _bootstrap_payload()

        self.assertEqual(payload["version"], "1.0.4")
        self.assertIn(payload["platform"], {"darwin", "linux", "win32"})
        self.assertEqual(
            Path(str(payload["default_output"])).parts[-2:],
            ("builds", "studio-output"),
        )
        self.assertEqual(payload["default_language"], "en-US")
        self.assertIn("zh-CN", payload["languages"])
        self.assertEqual(
            payload["releases_url"],
            "https://github.com/saslifat-gif/script2video/releases",
        )

    def test_packaged_app_defaults_output_to_user_documents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with (
                patch("script2video.webapp.sys.frozen", True, create=True),
                patch("script2video.webapp.Path.home", return_value=home),
            ):
                output = _default_output_path()

        self.assertEqual(
            output,
            (home / "Documents" / "Script2Video Studio").resolve(),
        )

    def test_update_check_finds_new_windows_release(self) -> None:
        release = {
            "tag_name": "v1.1.0",
            "html_url": (
                "https://github.com/saslifat-gif/script2video/releases/tag/v1.1.0"
            ),
            "assets": [
                {
                    "name": "Script2Video-Studio-1.1.0-Windows-x64.exe",
                    "browser_download_url": (
                        "https://github.com/saslifat-gif/script2video/releases/"
                        "download/v1.1.0/Script2Video-Studio-1.1.0-Windows-x64.exe"
                    ),
                }
            ],
        }
        response = MagicMock()
        response.__enter__.return_value = io.BytesIO(json.dumps(release).encode())

        with patch("script2video.webapp.urlopen", return_value=response):
            result = _update_payload()

        self.assertTrue(result["checked"])
        self.assertTrue(result["available"])
        self.assertEqual(result["latest_version"], "1.1.0")
        self.assertIn("Windows-x64.exe", str(result["download_url"]))

    def test_update_check_is_non_blocking_when_offline(self) -> None:
        with patch(
            "script2video.webapp.urlopen",
            side_effect=URLError("offline"),
        ):
            result = _update_payload()

        self.assertFalse(result["checked"])
        self.assertFalse(result["available"])
        self.assertEqual(result["current_version"], "1.0.4")

    def test_semantic_versions_compare_numerically(self) -> None:
        self.assertGreater(_version_tuple("1.10.0"), _version_tuple("1.9.9"))

    def test_output_launcher_returns_readable_error(self) -> None:
        with (
            patch("script2video.webapp.sys.platform", "win32"),
            patch(
                "script2video.webapp.os.startfile",
                side_effect=OSError("launcher unavailable"),
                create=True,
            ),
        ):
            with self.assertRaisesRegex(
                ValueError, "Could not open output folder"
            ):
                _open_path(Path("C:/output"))

    def test_plain_text_paragraphs_become_scenes(self) -> None:
        project = _project_from_text(
            "First paragraph.\n\nSecond paragraph.", "en-US", "fake", "test_low"
        )

        self.assertEqual(project.title, "First paragraph.")
        self.assertEqual(project.voice, "test_low")
        self.assertEqual(
            [scene.id for scene in project.scenes],
            ["paragraph-001", "paragraph-002"],
        )
        self.assertEqual(project.scenes[1].text, "Second paragraph.")

    def test_web_job_can_generate_narration_with_fake_engine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "web-build"
            job = GenerationJob(id="test-job")

            _run_generation_job(
                job,
                Path("examples/demo.yaml").resolve(),
                None,
                output,
                {"engine": "fake", "voice": "test_narrator"},
            )

            self.assertEqual(job.status, "complete", job.error)
            self.assertEqual(job.output, str(output))
            self.assertIn("narration.wav", job.files)
            self.assertIn("manifest.json", job.files)
            self.assertTrue((output / "narration.wav").is_file())

    def test_web_job_generates_voice_directly_from_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "text-build"
            job = GenerationJob(id="text-job")

            _run_text_generation_job(
                job,
                "Hello from plain text.\n\nThis is another scene.",
                None,
                output,
                {
                    "engine": "fake",
                    "language": "en-US",
                    "voice": "test_narrator",
                },
            )

            self.assertEqual(job.status, "complete", job.error)
            self.assertIn("script.txt", job.files)
            self.assertIn("narration.wav", job.files)
            self.assertEqual(len(list((output / "scenes").glob("*.wav"))), 2)
            self.assertEqual(
                (output / "script.txt").read_text(encoding="utf-8"),
                "Hello from plain text.\n\nThis is another scene.\n",
            )

    def test_browser_assets_are_packaged_with_the_application(self) -> None:
        static = Path(__file__).parents[1] / "src" / "script2video" / "web_static"

        self.assertIn("Script2Video Studio", (static / "index.html").read_text())
        self.assertIn("narration-text", (static / "index.html").read_text())
        self.assertIn("--accent:", (static / "app.css").read_text())
        self.assertIn("[hidden]", (static / "app.css").read_text())
        self.assertIn("/api/voices", (static / "app.js").read_text())
        self.assertIn("/api/generate", (static / "app.js").read_text())


if __name__ == "__main__":
    unittest.main()
