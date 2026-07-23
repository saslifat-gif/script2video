# M3: CapCut companion

## Outcome

M3 turns a source video and structured narration script into two assets that
CapCut Desktop can edit directly: a narration WAV and an SRT caption track.

```text
video + YAML script
    -> ffprobe video duration
    -> Kokoro narration
    -> safe duration fitting
    -> readable caption segmentation
    -> CapCut package
```

## Package contents

```text
output/
  narration.wav
  captions.srt
  manifest.json
  scenes/
    001-*.wav
```

The source video is referenced in the manifest but is not copied.

## Duration fitting

The first narration render establishes its natural duration. When fitting is
enabled, M3 subtracts configured scene pauses from both the narration and target
durations, computes a common speech-speed factor, validates every resulting
scene speed against the safe `0.50` to `2.00` range, and rerenders if needed.
Because Kokoro speed is not perfectly linear, the fitter performs up to three
measured correction passes and accepts a final difference within 0.5 percent.

The manifest records the original duration, target duration, applied factor,
final duration, and residual difference. A fit within one percent is accepted
without regenerating the narration.

## Caption timing

Caption text comes from the supplied script rather than speech recognition.
Long scene text is divided into blocks of at most 16 words or approximately 84
characters. Every block is synthesized independently, and its exact PCM sample
range is written to the manifest and SRT. Display text is balanced across no
more than two lines. Scene pauses are not included in caption display time.

By default, MLX Whisper measures word timestamps in the finished narration on
Apple Silicon. M3 reconciles those measurements to the exact supplied script,
then regroups the words into short one- or two-line cues. Cue changes therefore
follow spoken phrases while names, wording, and punctuation remain intentional.

If AI alignment is disabled or unavailable, M3 falls back to the exact
caption-block PCM boundaries described above.

## Local Studio

The responsive browser interface is served only on localhost and provides:

- YAML script selection;
- source-video selection;
- output-directory selection;
- optional voice override;
- duration-fit toggle;
- package generation;
- live job state;
- output-folder and CapCut launch buttons.

The browser handles high-DPI scaling, typography, and responsive layout
consistently on Windows and macOS. A native file chooser is opened by the local
Python process, so large videos do not need to be uploaded or copied.

It deliberately does not modify CapCut project files. The stable integration
contract is standard WAV and SRT import.
