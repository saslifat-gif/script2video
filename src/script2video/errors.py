class Script2VideoError(Exception):
    """Base class for expected, user-facing application errors."""


class ScriptLoadError(Script2VideoError):
    """The script could not be read or parsed."""


class EngineUnavailableError(Script2VideoError):
    """The requested TTS engine is not installed or registered."""


class RenderError(Script2VideoError):
    """Narration rendering failed."""


class VideoProbeError(Script2VideoError):
    """Video metadata could not be read."""


class PackageError(Script2VideoError):
    """A CapCut import package could not be created."""


class AlignmentError(Script2VideoError):
    """AI forced alignment could not produce usable word timing."""
