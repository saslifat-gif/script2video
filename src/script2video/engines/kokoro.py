from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from script2video.engines.base import (
    AudioChunk,
    AudioFormat,
    EngineIdentity,
    SynthesisRequest,
    Voice,
)
from script2video.errors import EngineUnavailableError

PipelineFactory = Callable[..., Any]
_REPO_ID = "hexgrad/Kokoro-82M"

_LANG_CODES = {
    "en-US": "a",
    "en-GB": "b",
    "es-ES": "e",
    "fr-FR": "f",
    "hi-IN": "h",
    "it-IT": "i",
    "ja-JP": "j",
    "pt-BR": "p",
    "zh-CN": "z",
}

_VOICE_IDS = {
    "en-US": (
        "af_heart",
        "af_alloy",
        "af_aoede",
        "af_bella",
        "af_jessica",
        "af_kore",
        "af_nicole",
        "af_nova",
        "af_river",
        "af_sarah",
        "af_sky",
        "am_adam",
        "am_echo",
        "am_eric",
        "am_fenrir",
        "am_liam",
        "am_michael",
        "am_onyx",
        "am_puck",
        "am_santa",
    ),
    "en-GB": (
        "bf_alice",
        "bf_emma",
        "bf_isabella",
        "bf_lily",
        "bm_daniel",
        "bm_fable",
        "bm_george",
        "bm_lewis",
    ),
    "ja-JP": (
        "jf_alpha",
        "jf_gongitsune",
        "jf_nezumi",
        "jf_tebukuro",
        "jm_kumo",
    ),
    "zh-CN": (
        "zf_xiaobei",
        "zf_xiaoni",
        "zf_xiaoxiao",
        "zf_xiaoyi",
        "zm_yunjian",
        "zm_yunxi",
        "zm_yunxia",
        "zm_yunyang",
    ),
    "es-ES": ("ef_dora", "em_alex", "em_santa"),
    "fr-FR": ("ff_siwis",),
    "hi-IN": ("hf_alpha", "hf_beta", "hm_omega", "hm_psi"),
    "it-IT": ("if_sara", "im_nicola"),
    "pt-BR": ("pf_dora", "pm_alex", "pm_santa"),
}


class KokoroEngine:
    """Adapter for the official hexgrad Kokoro inference package."""

    _format = AudioFormat(sample_rate=24_000, channels=1, sample_width=2)

    def __init__(self, pipeline_factory: PipelineFactory | None = None) -> None:
        self._pipeline_factory = pipeline_factory
        self._pipelines: dict[str, Any] = {}

    def list_voices(self) -> list[Voice]:
        return [
            Voice(id=voice_id, name=voice_id, languages=(language,))
            for language, voice_ids in _VOICE_IDS.items()
            for voice_id in voice_ids
        ]

    def identity(self) -> EngineIdentity:
        try:
            package_version = version("kokoro")
        except PackageNotFoundError:
            package_version = "not-installed"
        return EngineIdentity(
            name="kokoro",
            version=package_version,
            model=f"{_REPO_ID}-v1.0",
        )

    def synthesize(self, request: SynthesisRequest) -> AudioChunk:
        lang_code = _LANG_CODES.get(request.language)
        if lang_code is None:
            supported = ", ".join(_LANG_CODES)
            raise ValueError(
                f"Kokoro does not support language '{request.language}'. "
                f"Supported project languages: {supported}"
            )

        voices = _VOICE_IDS[request.language]
        if request.voice not in voices:
            available = ", ".join(voices)
            raise ValueError(
                f"Voice '{request.voice}' does not match language "
                f"'{request.language}'. Available voices: {available}"
            )

        pipeline = self._get_pipeline(lang_code)
        audio_parts: list[Any] = []
        for _graphemes, _phonemes, audio in pipeline(
            request.text,
            voice=request.voice,
            speed=request.speed,
            split_pattern=r"\n+",
        ):
            audio_parts.append(_to_numpy(audio))

        if not audio_parts:
            raise RuntimeError("Kokoro returned no audio")

        try:
            import numpy as np
        except ImportError as exc:
            raise EngineUnavailableError(
                "NumPy is required by the Kokoro engine. Install the project "
                "with: pip install -e '.[kokoro]'"
            ) from exc

        samples = np.concatenate(audio_parts).reshape(-1)
        samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
        pcm = (np.clip(samples, -1.0, 1.0) * 32_767).astype("<i2").tobytes()
        return AudioChunk(pcm=pcm, format=self._format)

    def _get_pipeline(self, lang_code: str) -> Any:
        if lang_code in self._pipelines:
            return self._pipelines[lang_code]

        factory = self._pipeline_factory
        if factory is None:
            try:
                from kokoro import KPipeline
            except ImportError as exc:
                raise EngineUnavailableError(
                    "The Kokoro engine is not installed. Install the project "
                    "with: pip install -e '.[kokoro]'"
                ) from exc
            factory = KPipeline

        pipeline = factory(lang_code=lang_code, repo_id=_REPO_ID)
        self._pipelines[lang_code] = pipeline
        return pipeline


def _to_numpy(audio: Any) -> Any:
    if hasattr(audio, "detach"):
        audio = audio.detach()
    if hasattr(audio, "cpu"):
        audio = audio.cpu()
    if hasattr(audio, "numpy"):
        return audio.numpy()
    try:
        import numpy as np
    except ImportError as exc:
        raise EngineUnavailableError(
            "NumPy is required by the Kokoro engine. Install the project "
            "with: pip install -e '.[kokoro]'"
        ) from exc
    return np.asarray(audio)
