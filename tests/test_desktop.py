from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from script2video.desktop import run_desktop_app


class DesktopAppTests(unittest.TestCase):
    def test_windows_app_uses_embedded_edge_window(self) -> None:
        server = MagicMock()
        server.server_address = ("127.0.0.1", 43210)
        window = MagicMock()
        webview = SimpleNamespace(
            create_window=MagicMock(return_value=window),
            start=MagicMock(),
        )

        with (
            patch("script2video.desktop.create_server", return_value=server),
            patch.dict(sys.modules, {"webview": webview}),
            patch("script2video.desktop.sys.platform", "win32"),
        ):
            run_desktop_app()

        webview.create_window.assert_called_once()
        self.assertEqual(
            webview.create_window.call_args.args,
            ("Script2Video Studio", "http://127.0.0.1:43210"),
        )
        webview.start.assert_called_once_with(gui="edgechromium")
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
