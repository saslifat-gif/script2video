from __future__ import annotations

import io
import json
import re
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from script2video.webapp import (
    GenerationJob,
    _bootstrap_payload,
    _default_output_path,
    _generation_output_path,
    _open_path,
    _project_from_text,
    _run_generation_job,
    _run_srt_generation_job,
    _run_text_generation_job,
    _update_payload,
    _version_tuple,
)


class WebAppTests(unittest.TestCase):
    def test_bootstrap_exposes_local_defaults(self) -> None:
        payload = _bootstrap_payload()

        self.assertEqual(payload["version"], "1.0.12")
        self.assertIn("platform", payload)
        self.assertEqual(
            Path(str(payload["default_output"])).parts[-2:],
            ("builds", "studio-output"),
        )
        self.assertEqual(payload["default_language"], "en-US")
        self.assertIn("zh-CN", payload["languages"])
        voices_by_language = payload["voices_by_language"]
        self.assertEqual(set(voices_by_language), set(payload["languages"]))
        self.assertTrue(
            all(
                voices_by_language[language]
                for language in payload["languages"]
            )
        )
        self.assertIn(
            "zf_xiaoxiao",
            {voice["id"] for voice in voices_by_language["zh-CN"]},
        )
        self.assertIn(
            "jf_alpha",
            {voice["id"] for voice in voices_by_language["ja-JP"]},
        )
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

        with (
            patch("script2video.webapp.urlopen", return_value=response),
            patch("script2video.webapp.sys.platform", "win32"),
        ):
            result = _update_payload()

        self.assertTrue(result["checked"])
        self.assertTrue(result["available"])
        self.assertEqual(result["latest_version"], "1.1.0")
        self.assertIn("Windows-x64.exe", str(result["download_url"]))
        self.assertTrue(result["platform_asset"])

    def test_update_check_is_non_blocking_when_offline(self) -> None:
        with patch(
            "script2video.webapp.urlopen",
            side_effect=URLError("offline"),
        ):
            result = _update_payload()

        self.assertFalse(result["checked"])
        self.assertFalse(result["available"])
        self.assertEqual(result["current_version"], "1.0.12")

    def test_generation_gets_a_unique_named_output_folder(self) -> None:
        root = Path("/tmp/studio")
        created = datetime(2026, 7, 30, 9, 8, 7, tzinfo=UTC)
        output = _generation_output_path(
            root,
            {"source_type": "text", "text": "My first scene. More words."},
            "abcdef123456",
            created,
        )

        self.assertEqual(
            output,
            root / "20260730-090807-my-first-scene-more-words-abcdef",
        )

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

    def test_plain_text_sentences_become_scenes(self) -> None:
        project = _project_from_text(
            "First sentence. Second sentence!", "en-US", "fake", "test_low"
        )

        self.assertEqual(project.title, "First sentence.")
        self.assertEqual(project.voice, "test_low")
        self.assertEqual(
            [scene.id for scene in project.scenes],
            ["scene-001", "scene-002"],
        )
        self.assertEqual(project.scenes[1].text, "Second sentence!")

    def test_plain_text_uses_selected_scene_pattern(self) -> None:
        project = _project_from_text(
            "First line\nSecond line\n\nLast paragraph",
            "en-US",
            "fake",
            "test_low",
            split_mode="paragraph",
        )

        self.assertEqual(
            [scene.text for scene in project.scenes],
            ["First line Second line", "Last paragraph"],
        )

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
            self.assertNotIn("script.txt", job.files)
            self.assertIn("narration.wav", job.files)
            self.assertIn("captions.srt", job.files)
            self.assertEqual(len(list((output / "scenes").glob("*.wav"))), 2)
            captions = (output / "captions.srt").read_text(encoding="utf-8")
            self.assertIn("Hello from plain text.", captions)
            self.assertIn("This is another scene.", captions)
            self.assertEqual(
                (output / "metadata" / "source.txt").read_text(encoding="utf-8"),
                "Hello from plain text.\n\nThis is another scene.\n",
            )

    def test_text_subtitle_cards_use_exact_synthesized_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "exact-caption-build"
            job = GenerationJob(id="exact-caption-job")
            text = (
                "This deliberately long sentence contains enough individual words "
                "to create several short and readable subtitle cards for testing."
            )

            _run_text_generation_job(
                job,
                text,
                None,
                output,
                {
                    "engine": "fake",
                    "language": "en-US",
                    "voice": "test_narrator",
                },
            )

            self.assertEqual(job.status, "complete", job.error)
            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )
            segments = manifest["scenes"][0]["segments"]
            self.assertGreaterEqual(len(segments), 2)
            captions = (output / "captions.srt").read_text(encoding="utf-8")
            for segment in segments:
                start_ms = round(segment["start_ms"])
                end_ms = round(segment["end_ms"])
                start = (
                    f"00:00:{start_ms // 1000:02d},{start_ms % 1000:03d}"
                )
                end = f"00:00:{end_ms // 1000:02d},{end_ms % 1000:03d}"
                self.assertIn(f"{start} --> {end}", captions)

    def test_web_job_splits_srt_cues_into_scenes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "episode.srt"
            script.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nFirst cue.\n\n"
                "2\n00:00:01,500 --> 00:00:03,000\nSecond cue.\n",
                encoding="utf-8",
            )
            output = root / "srt-build"
            job = GenerationJob(id="srt-job")

            _run_srt_generation_job(
                job,
                script,
                None,
                output,
                {
                    "engine": "fake",
                    "language": "en-US",
                    "voice": "test_narrator",
                },
            )

            self.assertEqual(job.status, "complete", job.error)
            self.assertIn("source.srt", job.files)
            self.assertIn("narration.wav", job.files)
            self.assertEqual(len(list((output / "scenes").glob("*.wav"))), 2)

    def test_browser_assets_are_packaged_with_the_application(self) -> None:
        static = Path(__file__).parents[1] / "src" / "script2video" / "web_static"
        html = (static / "index.html").read_text(encoding="utf-8")
        javascript = (static / "app.js").read_text(encoding="utf-8")

        self.assertIn("Script2Video Studio", html)
        self.assertIn("narration-text", html)
        self.assertIn("subtitles remain short and readable", html)
        self.assertIn("scene-split-select", html)
        self.assertNotIn('id="srt-mode"', html)
        stylesheet = (static / "app.css").read_text(encoding="utf-8")
        self.assertIn("--accent:", stylesheet)
        self.assertIn("--accent: #0b57d0", stylesheet)
        self.assertIn("v1.0.12 visual system", stylesheet)
        self.assertIn("v1.0.12", html)
        self.assertIn("[hidden]", stylesheet)
        self.assertIn("/api/voices", javascript)
        self.assertIn("/api/preview-voice", javascript)
        self.assertIn("splitTextScenes", javascript)
        self.assertIn("splitCaptionText", javascript)
        self.assertIn("voices_by_language", javascript)
        self.assertNotIn("Intl.Segmenter", javascript)
        self.assertIn("/api/generate", javascript)
        html_ids = set(re.findall(r'id="([^"]+)"', html))
        javascript_ids = set(
            re.findall(r'document\.querySelector\("#([^"]+)"\)', javascript)
        )
        self.assertEqual(javascript_ids - html_ids, set())


if __name__ == "__main__":
    unittest.main()
