from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import uuid
import webbrowser
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from platform import machine
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from script2video import __version__
from script2video.alignment import MLXWhisperAligner
from script2video.capcut import create_capcut_package
from script2video.captions import build_srt, write_srt
from script2video.config import ProjectConfig, SceneConfig, load_project
from script2video.engines.fake import FakeEngine
from script2video.engines.kokoro import KokoroEngine
from script2video.errors import Script2VideoError
from script2video.pipeline import render_project
from script2video.srt import load_srt_cues, load_srt_project
from script2video.text import SceneSplitMode, split_text_scenes
from script2video.video import probe_video

_STATIC_ROOT = Path(__file__).with_name("web_static")
_AI_ALIGNMENT_AVAILABLE = sys.platform == "darwin" and machine() == "arm64"
_MAX_REQUEST_BYTES = 1_000_000
_RELEASES_URL = "https://github.com/saslifat-gif/script2video/releases"
_LATEST_RELEASE_API = (
    "https://api.github.com/repos/saslifat-gif/script2video/releases/latest"
)


@dataclass
class GenerationJob:
    id: str
    status: str = "queued"
    message: str = "Preparing generation"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    output: str | None = None
    files: list[str] = field(default_factory=list)
    error: str | None = None


class WebState:
    def __init__(self, shutdown_callback: Callable[[], None] | None = None) -> None:
        self.jobs: dict[str, GenerationJob] = {}
        self.lock = threading.Lock()
        self.shutdown_callback = shutdown_callback

    def create_job(self) -> GenerationJob:
        job = GenerationJob(id=uuid.uuid4().hex)
        with self.lock:
            self.jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> GenerationJob | None:
        with self.lock:
            return self.jobs.get(job_id)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    shutdown_callback: Callable[[], None] | None = None,
) -> ThreadingHTTPServer:
    state = WebState(shutdown_callback)

    class RequestHandler(_WebRequestHandler):
        web_state = state

    return ThreadingHTTPServer((host, port), RequestHandler)


def run_web_app(
    host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True
) -> None:
    server = create_server(host, port)
    actual_port = server.server_address[1]
    url = f"http://{host}:{actual_port}"
    print(f"Script2Video Studio is running at {url}")
    print("Press Ctrl+C to stop it.")
    if open_browser:
        threading.Timer(0.35, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Script2Video Studio.")
    finally:
        server.server_close()


class _WebRequestHandler(BaseHTTPRequestHandler):
    web_state: WebState

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/bootstrap":
            self._send_json(_bootstrap_payload())
            return
        if path == "/api/update":
            self._send_json(_update_payload())
            return
        if path.startswith("/api/jobs/"):
            job_id = path.removeprefix("/api/jobs/")
            job = self.web_state.get_job(job_id)
            if job is None:
                self._send_error(HTTPStatus.NOT_FOUND, "Generation job not found")
                return
            self._send_json(asdict(job))
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/inspect-script":
                self._inspect_script(payload)
            elif path == "/api/inspect-srt":
                self._inspect_srt(payload)
            elif path == "/api/inspect-video":
                self._inspect_video(payload)
            elif path == "/api/pick":
                self._pick_path(payload)
            elif path == "/api/voices":
                self._list_voices(payload)
            elif path == "/api/generate":
                self._start_generation(payload)
            elif path == "/api/open-output":
                self._open_output(payload)
            elif path == "/api/open-capcut":
                self._open_capcut()
            elif path == "/api/open-url":
                self._open_url(payload)
            elif path == "/api/shutdown":
                self._shutdown()
            else:
                self._send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
        except (KeyError, OSError, TypeError, ValueError) as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Script2VideoError as exc:
            self._send_error(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc))
        except Exception as exc:
            self._send_error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                f"Unexpected application error: {exc}",
            )

    def log_message(self, format: str, *args: object) -> None:
        if self.path.startswith("/api/"):
            super().log_message(format, *args)

    def _serve_static(self, request_path: str) -> None:
        files = {
            "/": "index.html",
            "/index.html": "index.html",
            "/app.css": "app.css",
            "/app.js": "app.js",
        }
        filename = files.get(request_path)
        if filename is None:
            self._send_error(HTTPStatus.NOT_FOUND, "Page not found")
            return
        path = _STATIC_ROOT / filename
        if not path.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "UI asset not found")
            return
        content = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > _MAX_REQUEST_BYTES:
            raise ValueError("Request body is missing or too large")
        raw = self.rfile.read(length)
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("Request must be a JSON object")
        return payload

    def _inspect_script(self, payload: dict[str, Any]) -> None:
        path = _required_path(payload, "path")
        project = load_project(path)
        engine = _get_engine(project.engine)
        voices = [
            {"id": voice.id, "name": voice.name}
            for voice in engine.list_voices()
            if project.language in voice.languages
        ]
        self._send_json(
            {
                "path": str(path),
                "title": project.title,
                "language": project.language,
                "engine": project.engine,
                "voice": project.voice,
                "scene_count": len(project.scenes),
                "word_count": sum(len(scene.text.split()) for scene in project.scenes),
                "voices": voices,
            }
        )

    def _inspect_video(self, payload: dict[str, Any]) -> None:
        info = probe_video(_required_path(payload, "path"))
        self._send_json(
            {
                "path": str(info.path),
                "duration_seconds": round(info.duration_seconds, 3),
                "width": info.width,
                "height": info.height,
            }
        )

    def _inspect_srt(self, payload: dict[str, Any]) -> None:
        path = _required_path(payload, "path")
        cues = load_srt_cues(path)
        self._send_json(
            {
                "path": str(path),
                "title": path.stem,
                "scene_count": len(cues),
                "word_count": sum(len(cue.text.split()) for cue in cues),
                "duration_ms": cues[-1].end_ms,
            }
        )

    def _pick_path(self, payload: dict[str, Any]) -> None:
        kind = str(payload["kind"])
        if kind not in {"script", "subtitle", "video", "folder"}:
            raise ValueError("Picker kind must be script, subtitle, video, or folder")
        selected = _choose_local_path(kind)
        self._send_json({"path": selected})

    def _list_voices(self, payload: dict[str, Any]) -> None:
        engine_name = str(payload.get("engine", "kokoro")).strip()
        language = str(payload.get("language", "en-US")).strip()
        engine = _get_engine(engine_name)
        voices = [
            {"id": voice.id, "name": voice.name}
            for voice in engine.list_voices()
            if language in voice.languages
        ]
        if not voices:
            raise ValueError(
                f"No {engine_name} voices are available for language '{language}'"
            )
        self._send_json(
            {"engine": engine_name, "language": language, "voices": voices}
        )

    def _start_generation(self, payload: dict[str, Any]) -> None:
        output = _required_path(payload, "output", must_exist=False)
        video_value = str(payload.get("video", "")).strip()
        video = Path(video_value).expanduser().resolve() if video_value else None
        job = self.web_state.create_job()
        source_type = str(payload.get("source_type", "yaml")).strip()
        if source_type == "text":
            text = str(payload.get("text", "")).strip()
            if not text:
                raise ValueError("Narration text is required")
            target = _run_text_generation_job
            args = (job, text, video, output, payload)
        elif source_type == "srt":
            script = _required_path(payload, "script")
            target = _run_srt_generation_job
            args = (job, script, video, output, payload)
        elif source_type == "yaml":
            script = _required_path(payload, "script")
            target = _run_generation_job
            args = (job, script, video, output, payload)
        else:
            raise ValueError("Source type must be text, srt, or yaml")
        thread = threading.Thread(
            target=target,
            args=args,
            daemon=True,
        )
        thread.start()
        self._send_json(asdict(job), status=HTTPStatus.ACCEPTED)

    def _open_output(self, payload: dict[str, Any]) -> None:
        path = _required_path(payload, "path")
        _open_path(path)
        self._send_json({"opened": str(path)})

    def _open_capcut(self) -> None:
        if sys.platform == "darwin":
            command = ["open", "-a", "CapCut"]
        elif sys.platform == "win32":
            command = ["cmd", "/c", "start", "", "CapCut"]
        else:
            raise ValueError("Open CapCut manually on this operating system")
        completed = subprocess.run(command, capture_output=True, check=False)
        if completed.returncode != 0:
            raise ValueError("CapCut could not be opened")
        self._send_json({"opened": True})

    def _open_url(self, payload: dict[str, Any]) -> None:
        url = str(payload["url"]).strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "github.com":
            raise ValueError("Only Script2Video GitHub links can be opened")
        if not parsed.path.startswith("/saslifat-gif/script2video/"):
            raise ValueError("Only Script2Video GitHub links can be opened")
        if not webbrowser.open(url):
            raise ValueError("The update page could not be opened")
        self._send_json({"opened": url})

    def _shutdown(self) -> None:
        self._send_json({"stopping": True})
        if self.web_state.shutdown_callback is not None:
            threading.Thread(
                target=self.web_state.shutdown_callback, daemon=True
            ).start()
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _send_json(
        self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message}, status=status)


def _bootstrap_payload() -> dict[str, Any]:
    example = Path.cwd() / "examples" / "minecraft.yaml"
    languages = sorted(
        {
            language
            for voice in KokoroEngine().list_voices()
            for language in voice.languages
        }
    )
    return {
        "platform": sys.platform,
        "alignment_available": _AI_ALIGNMENT_AVAILABLE,
        "default_script": str(example.resolve()) if example.is_file() else "",
        "default_output": str(_default_output_path()),
        "default_language": "en-US",
        "languages": languages,
        "version": __version__,
        "releases_url": _RELEASES_URL,
    }


def _default_output_path() -> Path:
    if getattr(sys, "frozen", False):
        return (Path.home() / "Documents" / "Script2Video Studio").resolve()
    return (Path.cwd() / "builds" / "studio-output").resolve()


def _update_payload() -> dict[str, Any]:
    request = Request(
        _LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Script2Video-Studio/{__version__}",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )
    try:
        with urlopen(request, timeout=4) as response:  # noqa: S310
            release = json.load(response)
        latest_version = str(release["tag_name"]).lstrip("v")
        release_url = str(release.get("html_url") or _RELEASES_URL)
        download_url = release_url
        for asset in release.get("assets", []):
            name = str(asset.get("name", ""))
            if name.endswith("-Windows-x64.exe"):
                download_url = str(asset.get("browser_download_url") or release_url)
                break
        return {
            "checked": True,
            "available": _version_tuple(latest_version)
            > _version_tuple(__version__),
            "current_version": __version__,
            "latest_version": latest_version,
            "release_url": release_url,
            "download_url": download_url,
        }
    except (HTTPError, KeyError, TypeError, URLError, ValueError) as exc:
        return {
            "checked": False,
            "available": False,
            "current_version": __version__,
            "latest_version": None,
            "release_url": _RELEASES_URL,
            "download_url": _RELEASES_URL,
            "error": str(exc),
        }


def _version_tuple(value: str) -> tuple[int, int, int]:
    numbers = re.findall(r"\d+", value)
    if not numbers:
        raise ValueError(f"Invalid release version: {value}")
    parts = [int(part) for part in numbers[:3]]
    parts.extend([0] * (3 - len(parts)))
    return (parts[0], parts[1], parts[2])


def _get_engine(name: str) -> FakeEngine | KokoroEngine:
    if name == "fake":
        return FakeEngine()
    if name == "kokoro":
        return KokoroEngine()
    raise ValueError(f"Unsupported engine: {name}")


def _run_generation_job(
    job: GenerationJob,
    script_path: Path,
    video_path: Path | None,
    output_path: Path,
    options: dict[str, Any],
) -> None:
    try:
        job.status = "running"
        job.message = "Reading script and preparing the voice"
        project = load_project(script_path)
        voice = str(options.get("voice", "")).strip()
        if voice:
            project = project.model_copy(update={"voice": voice})
        engine_name = str(options.get("engine", project.engine))
        engine = _get_engine(engine_name)
        _render_generation(
            job, project, script_path, video_path, output_path, options, engine
        )
    except Exception as exc:
        _fail_job(job, exc)


def _run_text_generation_job(
    job: GenerationJob,
    text: str,
    video_path: Path | None,
    output_path: Path,
    options: dict[str, Any],
) -> None:
    try:
        job.status = "running"
        job.message = "Preparing your text and voice"
        engine_name = str(options.get("engine", "kokoro")).strip()
        language = str(options.get("language", "en-US")).strip()
        voice = str(options.get("voice", "")).strip()
        split_mode = cast(
            SceneSplitMode, str(options.get("split_mode", "sentence")).strip()
        )
        if not voice:
            raise ValueError("Voice is required")
        project = _project_from_text(
            text, language, engine_name, voice, split_mode=split_mode
        )
        output_path.mkdir(parents=True, exist_ok=True)
        input_path = output_path / "metadata" / "source.txt"
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(f"{text.strip()}\n", encoding="utf-8")
        _render_generation(
            job,
            project,
            input_path,
            video_path,
            output_path,
            options,
            _get_engine(engine_name),
        )
    except Exception as exc:
        _fail_job(job, exc)


def _run_srt_generation_job(
    job: GenerationJob,
    script_path: Path,
    video_path: Path | None,
    output_path: Path,
    options: dict[str, Any],
) -> None:
    try:
        job.status = "running"
        job.message = "Splitting subtitle cues into narration scenes"
        engine_name = str(options.get("engine", "kokoro")).strip()
        language = str(options.get("language", "en-US")).strip()
        voice = str(options.get("voice", "")).strip()
        if not voice:
            raise ValueError("Voice is required")
        project = load_srt_project(
            script_path,
            language=language,
            engine=engine_name,
            voice=voice,
        )
        output_path.mkdir(parents=True, exist_ok=True)
        input_path = output_path / "source.srt"
        input_path.write_text(
            script_path.read_text(encoding="utf-8-sig"),
            encoding="utf-8",
        )
        _render_generation(
            job,
            project,
            input_path,
            video_path,
            output_path,
            options,
            _get_engine(engine_name),
        )
    except Exception as exc:
        _fail_job(job, exc)


def _project_from_text(
    text: str,
    language: str,
    engine: str,
    voice: str,
    split_mode: SceneSplitMode = "sentence",
) -> ProjectConfig:
    scene_texts = split_text_scenes(text, mode=split_mode)
    if not scene_texts:
        raise ValueError("Narration text is required")
    first_line = scene_texts[0]
    title = first_line[:57] + "..." if len(first_line) > 60 else first_line
    return ProjectConfig(
        title=title,
        language=language,
        engine=engine,
        voice=voice,
        scenes=[
            SceneConfig(id=f"scene-{index:03d}", text=scene_text)
            for index, scene_text in enumerate(scene_texts, start=1)
        ],
    )


def _render_generation(
    job: GenerationJob,
    project: ProjectConfig,
    input_path: Path,
    video_path: Path | None,
    output_path: Path,
    options: dict[str, Any],
    engine: FakeEngine | KokoroEngine,
) -> None:
    if video_path is None:
        job.message = "Rendering narration scene by scene"
        manifest = render_project(project, input_path, output_path, engine)
        job.message = "Creating subtitles from the voice timing"
        write_srt(output_path / "captions.srt", build_srt(project, manifest))
    else:
        job.message = "Matching narration and captions to the video"
        use_alignment = bool(options.get("align", True))
        aligner = (
            MLXWhisperAligner(str(options.get("align_model", "tiny.en")))
            if use_alignment and _AI_ALIGNMENT_AVAILABLE
            else None
        )
        create_capcut_package(
            project,
            input_path,
            video_path,
            output_path,
            engine,
            fit_to_video=bool(options.get("fit", True)),
            aligner=aligner,
        )

    job.status = "complete"
    job.message = (
        "CapCut package is ready"
        if video_path is not None
        else "Narration, scenes, and subtitles are ready"
    )
    job.output = str(output_path)
    job.files = sorted(path.name for path in output_path.iterdir() if path.is_file())


def _fail_job(job: GenerationJob, error: Exception) -> None:
    job.status = "failed"
    job.message = "Generation failed"
    job.error = str(error)


def _required_path(payload: dict[str, Any], key: str, must_exist: bool = True) -> Path:
    value = str(payload[key]).strip()
    if not value:
        raise ValueError(f"{key.replace('_', ' ').title()} is required")
    path = Path(value).expanduser().resolve()
    if must_exist and not path.exists():
        raise ValueError(f"{key.replace('_', ' ').title()} does not exist: {path}")
    return path


def _choose_local_path(kind: str) -> str:
    if sys.platform == "darwin":
        kind_clause = "folder" if kind == "folder" else "file"
        prompt = {
            "script": "Choose a YAML script",
            "subtitle": "Choose an SRT subtitle script",
            "video": "Choose a source video",
            "folder": "Choose an output folder",
        }[kind]
        command = [
            "osascript",
            "-e",
            f'POSIX path of (choose {kind_clause} with prompt "{prompt}")',
        ]
    elif sys.platform == "win32":
        if kind == "folder":
            script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d=New-Object System.Windows.Forms.FolderBrowserDialog; "
                "if($d.ShowDialog() -eq 'OK'){[Console]::OutputEncoding="
                "[Text.Encoding]::UTF8;Write-Output $d.SelectedPath}"
            )
        else:
            file_filter = (
                "YAML scripts|*.yaml;*.yml|All files|*.*"
                if kind == "script"
                else "SRT subtitles|*.srt|All files|*.*"
                if kind == "subtitle"
                else "Video files|*.mp4;*.mov;*.mkv;*.webm|All files|*.*"
            )
            script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d=New-Object System.Windows.Forms.OpenFileDialog; "
                f"$d.Filter='{file_filter}'; "
                "if($d.ShowDialog() -eq 'OK'){[Console]::OutputEncoding="
                "[Text.Encoding]::UTF8;Write-Output $d.FileName}"
            )
        command = ["powershell", "-NoProfile", "-STA", "-Command", script]
    else:
        command = ["zenity", "--file-selection"]
        if kind == "folder":
            command.append("--directory")
        elif kind == "script":
            command.extend(["--file-filter", "YAML scripts | *.yaml *.yml"])
        elif kind == "subtitle":
            command.extend(["--file-filter", "SRT subtitles | *.srt"])
        else:
            command.extend(["--file-filter", "Video files | *.mp4 *.mov *.mkv *.webm"])

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _open_path(path: Path) -> None:
    if sys.platform == "win32":
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError as exc:
            raise ValueError(f"Could not open output folder: {exc}") from exc
        return
    elif sys.platform == "darwin":
        command = ["open", str(path)]
    else:
        command = ["xdg-open", str(path)]
    try:
        subprocess.Popen(command)
    except OSError as exc:
        raise ValueError(f"Could not open output folder: {exc}") from exc
