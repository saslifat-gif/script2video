from __future__ import annotations

from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from script2video.errors import ScriptLoadError

SceneId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", min_length=1)]
LanguageCode = Annotated[str, Field(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")]


class SceneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: SceneId
    text: Annotated[str, Field(min_length=1)]
    voice: str | None = None
    speed: Annotated[float, Field(ge=0.5, le=2.0)] = 1.0
    pause_after_ms: Annotated[int, Field(ge=0, le=60_000)] = 0
    notes: str | None = None

    @field_validator("text")
    @classmethod
    def text_must_contain_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain spoken text")
        return value


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Annotated[str, Field(min_length=1)]
    language: LanguageCode
    engine: Annotated[str, Field(min_length=1)]
    voice: Annotated[str, Field(min_length=1)]
    scenes: Annotated[list[SceneConfig], Field(min_length=1)]

    @field_validator("scenes")
    @classmethod
    def scene_ids_must_be_unique(cls, scenes: list[SceneConfig]) -> list[SceneConfig]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for scene in scenes:
            if scene.id in seen:
                duplicates.add(scene.id)
            seen.add(scene.id)
        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise ValueError(f"scene IDs must be unique; duplicated: {names}")
        return scenes


def load_project(path: Path) -> ProjectConfig:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScriptLoadError(f"Could not read script '{path}': {exc}") from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ScriptLoadError(f"Invalid YAML in '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ScriptLoadError(f"Script '{path}' must contain a YAML object at its root")

    try:
        return ProjectConfig.model_validate(data)
    except ValidationError as exc:
        lines = [f"Invalid script '{path}':"]
        for error in exc.errors(include_url=False):
            location = ".".join(str(part) for part in error["loc"])
            lines.append(f"  {location}: {error['msg']}")
        raise ScriptLoadError("\n".join(lines)) from exc
