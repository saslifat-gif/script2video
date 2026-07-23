from __future__ import annotations

import multiprocessing
import sys

from script2video.webapp import run_web_app


def main() -> None:
    """Launch the packaged desktop application without a console window."""
    multiprocessing.freeze_support()
    try:
        run_web_app(port=0, open_browser=True)
    except Exception as exc:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                str(exc),
                "Script2Video Studio could not start",
                0x10,
            )
        else:
            raise


if __name__ == "__main__":
    main()
