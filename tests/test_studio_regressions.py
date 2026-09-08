from __future__ import annotations

import io
import json
import tempfile
import unittest
from dataclasses import replace
from email.message import Message
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from script2video.capcut import create_capcut_package
from script2video.config import ProjectConfig, SceneConfig
from script2video.engines.fake import FakeEngine
from script2video.video import VideoInfo
from script2video.webapp import (
    WebState,
    _WebRequestHandler,
)


class RequestProtectionTests(unittest.TestCase):
    def handler(
        self,
        *,
        host="127.0.0.1:8765",
        origin=None,
        token=True,
        content_type="application/json",
    ):
        handler = object.__new__(_WebRequestHandler)
        handler.server = SimpleNamespace(server_address=("127.0.0.1", 8765))
        handler.web_state = WebState()
        handler.path = "/api/open-output"
        handler.headers = Message()
        handler.headers["Host"] = host
        if origin is not None:
            handler.headers["Origin"] = origin
        if token:
            handler.headers["X-Studio-Token"] = handler.web_state.csrf_token
        handler.headers["Content-Type"] = content_type
        body = json.dumps({"path": "/unused"}).encode()
        handler.headers["Content-Length"] = str(len(body))
        handler.rfile = io.BytesIO(body)
        handler._send_json = Mock()
        handler._open_output = Mock()
        return handler

    def test_rejects_untrusted_requests_before_dispatch(self):
        cases = [
            {"origin": "https://untrusted.example"},
            {"origin": "null"},
            {"origin": "http://127.0.0.1:9999"},
            {"host": "rebinding.example:8765"},
            {"token": False},
        ]
        for case in cases:
            with self.subTest(case=case):
                handler = self.handler(**case)
                handler.do_POST()
                handler._open_output.assert_not_called()
                self.assertEqual(
                    handler._send_json.call_args.kwargs["status"], HTTPStatus.FORBIDDEN
                )

    def test_plain_text_body_is_rejected_even_with_valid_token(self):
        handler = self.handler(content_type="text/plain")
        handler.do_POST()
        handler._open_output.assert_not_called()
        self.assertEqual(
            handler._send_json.call_args.kwargs["status"],
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )

    def test_same_origin_and_native_requests_work(self):
        for host in ("127.0.0.1:8765", "localhost:8765"):
            for origin in (None, f"http://{host}"):
                with self.subTest(host=host, origin=origin):
                    handler = self.handler(host=host, origin=origin)
                    handler.do_POST()
                    handler._open_output.assert_called_once_with({"path": "/unused"})

    def test_bootstrap_token_is_available_only_to_trusted_hosts(self):
        handler = self.handler(token=False)
        handler.path = "/api/bootstrap"
        handler.do_GET()
        payload = handler._send_json.call_args.args[0]
        self.assertEqual(payload["csrf_token"], handler.web_state.csrf_token)
        self.assertNotEqual(WebState().csrf_token, payload["csrf_token"])
        handler = self.handler(host="rebinding.example:8765", token=False)
        handler.path = "/api/bootstrap"
        handler.do_GET()
        self.assertNotIn("csrf_token", handler._send_json.call_args.args[0])

    def test_token_from_another_session_is_rejected(self):
        handler = self.handler()
        handler.headers.replace_header("X-Studio-Token", WebState().csrf_token)
        handler.do_POST()
        handler._open_output.assert_not_called()


class GenerationRegressionTests(unittest.TestCase):
    def project(self, language="en-US"):
        return ProjectConfig(
            title="Test",
            language=language,
            engine="fake",
            voice="test_narrator",
            scenes=[SceneConfig(id="intro", text="x" * 40)],
        )

    def test_nonconverging_fit_warns_and_preserves_usable_files(self):
        class FixedDurationEngine(FakeEngine):
            def synthesize(self, request):
                return super().synthesize(replace(request, speed=1.0))

        for fit in (True, False):
            with self.subTest(fit=fit), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source.txt"
                source.write_text("x" * 40)
                output = root / "output"
                with patch(
                    "script2video.capcut.probe_video",
                    return_value=VideoInfo(root / "video.mp4", 1.1),
                ):
                    manifest = create_capcut_package(
                        self.project(),
                        source,
                        root / "video.mp4",
                        output,
                        FixedDurationEngine(),
                        fit_to_video=fit,
                    )
                self.assertFalse(manifest["capcut"]["fit"]["converged"])
                self.assertEqual(bool(manifest["warnings"]), fit)
                if fit:
                    self.assertIn("0.10 seconds shorter", manifest["warnings"][0])
                    self.assertEqual(manifest["capcut"]["fit"]["iterations"], 3)
                persisted = json.loads((output / "manifest.json").read_text())
                self.assertEqual(persisted["warnings"], manifest["warnings"])
                self.assertTrue((output / "captions.srt").is_file())
                self.assertTrue((output / "narration.wav").is_file())
