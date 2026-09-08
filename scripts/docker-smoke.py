"""Run inside the image: verify its normal startup, API protection and exports."""

import json
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

process = subprocess.Popen(["script2video", "companion"])
base = "http://127.0.0.1:8765"


def request(path, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    with urlopen(
        Request(base + path, data=data, headers=headers or {}), timeout=5
    ) as r:
        return json.load(r)


try:
    for _attempt in range(60):
        try:
            bootstrap = request("/api/bootstrap")
            break
        except URLError:
            if process.poll() is not None:
                raise RuntimeError("Studio exited during startup") from None
            time.sleep(0.5)
    else:
        raise RuntimeError("Studio did not start")
    assert bootstrap["container_mode"]
    assert not bootstrap["desktop_actions"]
    assert bootstrap["default_output"] == "/data/output"
    headers = {
        "Content-Type": "application/json",
        "X-Studio-Token": bootstrap["csrf_token"],
    }
    for bad in [
        {"Content-Type": "application/json"},
        {**headers, "Origin": "https://untrusted.example"},
    ]:
        try:
            request("/api/generate", {}, bad)
            raise AssertionError("Untrusted request was accepted")
        except HTTPError as error:
            assert error.code == 403
    job = request(
        "/api/generate",
        {
            "source_type": "text",
            "text": "Docker narration test. Second sentence.",
            "engine": "fake",
            "language": "en-US",
            "voice": "test_narrator",
            "output": "/data/output",
        },
        headers,
    )
    for _attempt in range(100):
        job = request("/api/jobs/" + job["id"])
        if job["status"] in {"complete", "failed"}:
            break
        time.sleep(0.1)
    assert job["status"] == "complete", job
    output = Path(job["output"])
    assert (output / "narration.wav").stat().st_size > 44
    assert "-->" in (output / "captions.srt").read_text()
    assert json.loads((output / "manifest.json").read_text())["status"] == "success"
    assert job["duration_ms"] > 0
    for name in ("captions.srt", "script.txt"):
        with urlopen(base + job["downloads"][name], timeout=5) as response:
            assert response.read()
    with urlopen(
        Request(
            base + job["downloads"]["narration.wav"], headers={"Range": "bytes=0-3"}
        ),
        timeout=5,
    ) as response:
        assert response.status == 206
        assert response.read() == b"RIFF"
    print("Docker startup, API protection, narration and caption checks passed")
finally:
    process.terminate()
    process.wait(timeout=10)
