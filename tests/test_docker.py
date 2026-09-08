from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from script2video.webapp import _bootstrap_payload, _choose_local_path, _open_path


class DockerModeTests(unittest.TestCase):
    def test_container_bootstrap_uses_mounted_output_without_desktop_actions(self):
        with patch("script2video.webapp._CONTAINER_MODE", True):
            payload = _bootstrap_payload()
        self.assertEqual(payload["default_output"], "/data/output")
        self.assertTrue(payload["container_mode"])
        self.assertFalse(payload["desktop_actions"])
        self.assertFalse(payload["alignment_available"])

    def test_container_actions_do_not_launch_host_programs(self):
        with (
            patch("script2video.webapp._CONTAINER_MODE", True),
            patch("script2video.webapp.subprocess.run") as run,
            patch("script2video.webapp.subprocess.Popen") as popen,
        ):
            with self.assertRaisesRegex(ValueError, "mounted path"):
                _choose_local_path("video")
            with self.assertRaisesRegex(ValueError, "data/output"):
                _open_path(Path("/data/output"))
        run.assert_not_called()
        popen.assert_not_called()

    def test_windows_keeps_desktop_actions(self):
        with (
            patch("script2video.webapp._CONTAINER_MODE", False),
            patch("script2video.webapp.sys.platform", "win32"),
        ):
            self.assertTrue(_bootstrap_payload()["desktop_actions"])
