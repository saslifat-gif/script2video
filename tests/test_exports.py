from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from script2video.webapp import GenerationJob, WebState, _WebRequestHandler


class ExportTests(unittest.TestCase):
    def handler(self, root, headers=None, command="GET"):
        h = object.__new__(_WebRequestHandler)
        h.web_state = WebState()
        h.web_state.jobs["test"] = GenerationJob(
            id="test", status="complete", output=str(root)
        )
        h.headers = headers or {}
        h.command = command
        h.wfile = io.BytesIO()
        h.send_response = Mock()
        h.send_header = Mock()
        h.end_headers = Mock()
        h._send_error = Mock()
        return h

    def test_audio_can_be_played_downloaded_and_seeked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "narration.wav").write_bytes(b"0123456789")
            for headers, expected in [
                ({}, b"0123456789"),
                ({"Range": "bytes=2-4"}, b"234"),
                ({"Range": "bytes=-3"}, b"789"),
                ({"Range": "bytes=8-"}, b"89"),
            ]:
                h = self.handler(root, headers)
                h._serve_export("test", "narration.wav")
                self.assertEqual(h.wfile.getvalue(), expected)
            h = self.handler(root, {"Range": "bytes=99-"})
            h._serve_export("test", "narration.wav")
            h.send_response.assert_called_once_with(416)
            h = self.handler(root, command="HEAD")
            h._serve_export("test", "narration.wav")
            self.assertEqual(h.wfile.getvalue(), b"")
            h.send_header.assert_any_call("Content-Length", "10")

    def test_script_export_cannot_escape_the_completed_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "metadata").mkdir()
            (root / "metadata/source.txt").write_text("The complete script")
            h = self.handler(root)
            h._serve_export("test", "script.txt")
            self.assertEqual(h.wfile.getvalue(), b"The complete script")
            for job, name in [
                ("missing", "script.txt"),
                ("test", "../secret.txt"),
                ("test", "secret.txt"),
            ]:
                h = self.handler(root)
                h._serve_export(job, name)
                h._send_error.assert_called_once()
            outside = root / "outside"
            outside.mkdir()
            try:
                (outside / "narration.wav").symlink_to(root / "metadata/source.txt")
            except (OSError, NotImplementedError):
                return  # Some Windows hosts do not allow creating symlinks.
            h = self.handler(outside)
            h._serve_export("test", "narration.wav")
            h._send_error.assert_called_once()
