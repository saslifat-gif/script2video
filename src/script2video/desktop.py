from __future__ import annotations

import multiprocessing
import sys
import threading
import webbrowser

from script2video.webapp import create_server


def run_desktop_app() -> None:
    """Run Studio in a native window, with the system browser as a fallback."""
    window_holder: dict[str, object] = {}

    def close_window() -> None:
        window = window_holder.get("window")
        if window is not None:
            window.destroy()  # type: ignore[attr-defined]

    server = create_server(port=0, shutdown_callback=close_window)
    host, port = server.server_address
    url = f"http://{host}:{port}"

    try:
        import webview
    except ImportError:
        webbrowser.open(url)
        try:
            server.serve_forever()
        finally:
            server.server_close()
        return

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    window = webview.create_window(
        "Script2Video Studio",
        url,
        width=1280,
        height=860,
        min_size=(920, 680),
        resizable=True,
        background_color="#f5f6f2",
        text_select=True,
    )
    window_holder["window"] = window
    try:
        if sys.platform == "win32":
            webview.start(gui="edgechromium")
        else:
            webview.start()
    except Exception:
        webbrowser.open(url)
        server_thread.join()
    finally:
        server.shutdown()
        server.server_close()


def main() -> None:
    """Launch the packaged desktop application without a console window."""
    multiprocessing.freeze_support()
    try:
        run_desktop_app()
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
