from __future__ import annotations

import json
import sys
from typing import Any

from script2video.alignment import _extract_words


def main() -> None:
    payload: dict[str, Any] = json.load(sys.stdin)
    try:
        from mlx_whisper import transcribe
    except ImportError as exc:
        raise RuntimeError("No module named 'mlx_whisper'") from exc

    result = transcribe(
        payload["audio_path"],
        path_or_hf_repo=payload["repository"],
        language=payload["language"],
        initial_prompt=payload["text"],
        word_timestamps=True,
        verbose=None,
    )
    words = _extract_words(result)
    json.dump(
        {
            "words": [
                {
                    "text": word.text,
                    "start_seconds": word.start_seconds,
                    "end_seconds": word.end_seconds,
                }
                for word in words
            ]
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
