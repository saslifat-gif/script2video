from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from platform import machine
from tkinter import filedialog, messagebox, ttk

from script2video.config import ProjectConfig, load_project
from script2video.engines.fake import FakeEngine
from script2video.engines.kokoro import KokoroEngine
from script2video.errors import Script2VideoError
from script2video.video import VideoInfo, probe_video

_USE_SCRIPT_VOICE = "Use script voice"
_AI_ALIGNMENT_AVAILABLE = sys.platform == "darwin" and machine() == "arm64"


class CompanionApp:
    BACKGROUND = "#f5f2fd"
    CARD = "#ffffff"
    TEXT = "#1b1b23"
    MUTED = "#626267"
    BORDER = "#c7c4d6"
    PRIMARY = "#3f3bbd"
    PRIMARY_HOVER = "#3631b4"
    SUCCESS = "#14804a"
    ERROR = "#ba1a1a"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Script2Video")
        self.root.geometry("700x760")
        self.root.minsize(660, 700)
        self.root.configure(background=self.BACKGROUND)
        self.root.attributes("-topmost", True)

        self.script = tk.StringVar(value="examples/minecraft.yaml")
        self.video = tk.StringVar()
        self.output = tk.StringVar(value="builds/capcut-package")
        self.voice = tk.StringVar(value=_USE_SCRIPT_VOICE)
        self.fit = tk.BooleanVar(value=True)
        self.align = tk.BooleanVar(value=_AI_ALIGNMENT_AVAILABLE)
        self.align_model = tk.StringVar(value="tiny.en")
        self.topmost = tk.BooleanVar(value=True)
        self.script_summary = tk.StringVar(value="Choose a valid YAML script")
        self.video_summary = tk.StringVar(value="Choose a source video")
        self.status = tk.StringVar(value="Choose a video to continue")
        self._advanced_visible = False
        self._output_was_suggested = True
        self._script_valid = False
        self._video_valid = False

        self._configure_styles()
        self._build()
        self._bind_validation()
        self.root.after_idle(self._inspect_script)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background=self.BACKGROUND)
        style.configure("Topbar.TFrame", background=self.CARD)
        style.configure("CardBody.TFrame", background=self.CARD)
        style.configure(
            "Card.TFrame",
            background=self.CARD,
            bordercolor=self.BORDER,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Title.TLabel",
            background=self.BACKGROUND,
            foreground=self.TEXT,
            font=("TkDefaultFont", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.BACKGROUND,
            foreground=self.MUTED,
            font=("TkDefaultFont", 13),
        )
        style.configure(
            "Brand.TLabel",
            background=self.CARD,
            foreground=self.TEXT,
            font=("TkDefaultFont", 15, "bold"),
        )
        style.configure(
            "Section.TLabel",
            background=self.CARD,
            foreground=self.MUTED,
            font=("TkDefaultFont", 10, "bold"),
        )
        style.configure(
            "Card.TLabel",
            background=self.CARD,
            foreground=self.TEXT,
            font=("TkDefaultFont", 12),
        )
        style.configure(
            "Metadata.TLabel",
            background=self.CARD,
            foreground=self.MUTED,
            font=("TkDefaultFont", 11),
        )
        style.configure(
            "Status.TLabel",
            background=self.CARD,
            foreground=self.TEXT,
            font=("TkDefaultFont", 10),
        )
        style.configure(
            "Field.TEntry",
            fieldbackground="#f0ecf8",
            foreground=self.TEXT,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            padding=(10, 7),
        )
        style.configure(
            "Field.TCombobox",
            fieldbackground="#f0ecf8",
            background="#f0ecf8",
            foreground=self.TEXT,
            bordercolor=self.BORDER,
            arrowcolor=self.MUTED,
            padding=(10, 6),
        )
        style.map(
            "Field.TCombobox",
            fieldbackground=[("readonly", "#f0ecf8")],
            selectbackground=[("readonly", "#f0ecf8")],
            selectforeground=[("readonly", self.TEXT)],
        )
        style.configure(
            "Secondary.TButton",
            background=self.CARD,
            foreground=self.TEXT,
            bordercolor=self.BORDER,
            padding=(12, 7),
            font=("TkDefaultFont", 11),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#eae6f2")],
        )
        style.configure(
            "Link.TButton",
            background=self.CARD,
            foreground=self.PRIMARY,
            borderwidth=0,
            padding=(0, 4),
            font=("TkDefaultFont", 11),
        )
        style.map(
            "Link.TButton",
            foreground=[("active", self.PRIMARY_HOVER)],
            background=[("active", self.CARD)],
        )
        style.configure(
            "Primary.TButton",
            background=self.PRIMARY,
            foreground="#ffffff",
            bordercolor=self.PRIMARY,
            padding=(16, 11),
            font=("TkDefaultFont", 13, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", self.PRIMARY_HOVER),
                ("disabled", "#c7c4d6"),
            ],
            foreground=[("disabled", "#777585")],
        )
        style.configure(
            "Card.TCheckbutton",
            background=self.CARD,
            foreground=self.TEXT,
            font=("TkDefaultFont", 11),
        )
        style.map("Card.TCheckbutton", background=[("active", self.CARD)])
        style.configure(
            "Indigo.Horizontal.TProgressbar",
            background=self.PRIMARY,
            troughcolor="#e4e1ec",
            borderwidth=0,
        )

    def _build(self) -> None:
        self._build_topbar()

        workspace = ttk.Frame(self.root, style="App.TFrame", padding=(36, 24, 36, 18))
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(0, weight=1)

        ttk.Label(workspace, text="Create a CapCut package", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            workspace,
            text="Turn a structured script and source video into editable assets.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 18))

        source = self._card(workspace, row=2)
        self._section_title(source, "STEP 1  ·  SOURCE")
        self._path_row(
            source,
            row=1,
            label="Script",
            variable=self.script,
            command=self._choose_script,
        )
        self.script_metadata = ttk.Label(
            source, textvariable=self.script_summary, style="Metadata.TLabel"
        )
        self.script_metadata.grid(
            row=2, column=1, columnspan=2, sticky="w", pady=(0, 10)
        )
        self._path_row(
            source,
            row=3,
            label="Video",
            variable=self.video,
            command=self._choose_video,
        )
        self.video_metadata = ttk.Label(
            source, textvariable=self.video_summary, style="Metadata.TLabel"
        )
        self.video_metadata.grid(row=4, column=1, columnspan=2, sticky="w")

        narration = self._card(workspace, row=3)
        self._section_title(narration, "STEP 2  ·  NARRATION")
        ttk.Label(narration, text="Voice", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 14), pady=(0, 10)
        )
        self.voice_menu = ttk.Combobox(
            narration,
            textvariable=self.voice,
            values=(_USE_SCRIPT_VOICE,),
            state="readonly",
            style="Field.TCombobox",
        )
        self.voice_menu.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        options = ttk.Frame(narration, style="CardBody.TFrame")
        options.grid(row=2, column=1, columnspan=2, sticky="w")
        ttk.Checkbutton(
            options,
            text="Fit narration to video",
            variable=self.fit,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=2)
        alignment_label = (
            "AI caption alignment"
            if _AI_ALIGNMENT_AVAILABLE
            else "AI caption alignment (Apple Silicon only)"
        )
        self.alignment_check = ttk.Checkbutton(
            options,
            text=alignment_label,
            variable=self.align,
            command=self._update_alignment_state,
            style="Card.TCheckbutton",
        )
        self.alignment_check.pack(anchor="w", pady=2)
        if not _AI_ALIGNMENT_AVAILABLE:
            self.alignment_check.state(["disabled"])
        self.advanced_button = ttk.Button(
            narration,
            text="Advanced  ▾",
            command=self._toggle_advanced,
            style="Link.TButton",
        )
        self.advanced_button.grid(row=3, column=1, sticky="w", pady=(8, 0))

        self.advanced = ttk.Frame(narration, style="CardBody.TFrame")
        ttk.Label(self.advanced, text="Alignment model", style="Metadata.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        self.alignment_menu = ttk.Combobox(
            self.advanced,
            textvariable=self.align_model,
            values=("tiny.en", "base.en", "tiny", "base"),
            state="readonly",
            width=14,
            style="Field.TCombobox",
        )
        self.alignment_menu.grid(row=0, column=1, sticky="w")
        self._update_alignment_state()
        ttk.Checkbutton(
            self.advanced,
            text="Keep window on top",
            variable=self.topmost,
            command=self._toggle_topmost,
            style="Card.TCheckbutton",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        output = self._card(workspace, row=4)
        self._section_title(output, "STEP 3  ·  OUTPUT")
        self._path_row(
            output,
            row=1,
            label="Folder",
            variable=self.output,
            command=self._choose_output,
        )
        self.generate_button = ttk.Button(
            output,
            text="Generate CapCut Package",
            command=self._generate,
            style="Primary.TButton",
        )
        self.generate_button.grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(12, 0)
        )
        self.progress = ttk.Progressbar(
            output, mode="indeterminate", style="Indigo.Horizontal.TProgressbar"
        )

        self.success_actions = ttk.Frame(output, style="CardBody.TFrame")
        ttk.Button(
            self.success_actions,
            text="Open Output",
            command=self._open_output,
            style="Secondary.TButton",
        ).pack(side="left")
        ttk.Button(
            self.success_actions,
            text="Open CapCut",
            command=self._open_capcut,
            style="Secondary.TButton",
        ).pack(side="left", padx=(8, 0))

        self._build_footer()

    def _build_topbar(self) -> None:
        topbar = ttk.Frame(self.root, style="Topbar.TFrame", padding=(24, 11))
        topbar.pack(fill="x")
        ttk.Label(topbar, text="▣  Script2Video", style="Brand.TLabel").pack(
            side="left"
        )
        ttk.Label(
            topbar,
            text="Local CapCut companion",
            style="Metadata.TLabel",
        ).pack(side="right")

    def _build_footer(self) -> None:
        footer = ttk.Frame(self.root, style="Topbar.TFrame", padding=(24, 9))
        footer.pack(fill="x", side="bottom")
        self.status_dot = ttk.Label(footer, text="●", style="Status.TLabel")
        self.status_dot.pack(side="left")
        ttk.Label(footer, textvariable=self.status, style="Status.TLabel").pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(footer, text="v0.3.0", style="Metadata.TLabel").pack(side="right")

    def _card(self, parent: ttk.Frame, row: int) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(1, weight=1)
        return card

    def _section_title(self, parent: ttk.Frame, text: str) -> None:
        ttk.Label(parent, text=text, style="Section.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )

    def _path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        command: Callable[[], None],
    ) -> None:
        ttk.Label(parent, text=label, style="Card.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 14), pady=(0, 6)
        )
        ttk.Entry(
            parent,
            textvariable=variable,
            state="readonly",
            style="Field.TEntry",
        ).grid(row=row, column=1, sticky="ew", pady=(0, 6))
        ttk.Button(
            parent, text="Choose", command=command, style="Secondary.TButton"
        ).grid(row=row, column=2, padx=(8, 0), pady=(0, 6))

    def _bind_validation(self) -> None:
        self.script.trace_add("write", lambda *_args: self._script_path_changed())
        self.video.trace_add("write", lambda *_args: self._video_path_changed())
        self.output.trace_add("write", lambda *_args: self._update_generate_state())
        self._update_generate_state()

    def _script_path_changed(self) -> None:
        self._script_valid = False
        self.script_summary.set("Inspecting script…")
        self._update_generate_state()

    def _video_path_changed(self) -> None:
        self._video_valid = False
        self.video_summary.set("Inspecting video…")
        self._update_generate_state()

    def _update_generate_state(self) -> None:
        ready = (
            self._script_valid and self._video_valid and bool(self.output.get().strip())
        )
        if ready:
            self.generate_button.state(["!disabled"])
            if self.status.get() == "Choose a video to continue":
                self._set_status("Ready", self.SUCCESS)
        else:
            self.generate_button.state(["disabled"])

    def _choose_script(self) -> None:
        selected = filedialog.askopenfilename(
            filetypes=[("YAML scripts", "*.yaml *.yml")]
        )
        if selected:
            self.script.set(selected)
            self._inspect_script()

    def _inspect_script(self) -> None:
        path = Path(self.script.get()).expanduser()
        try:
            project = load_project(path)
        except Script2VideoError as exc:
            self._script_valid = False
            self.script_summary.set(str(exc).splitlines()[0])
            self.script_metadata.configure(foreground=self.ERROR)
            self._update_generate_state()
            return
        self._script_valid = True
        self.script_metadata.configure(foreground=self.MUTED)
        self.script_summary.set(
            f"✓ {len(project.scenes)} scenes  ·  {project.language}  ·  {project.voice}"
        )
        self._populate_voices(project)
        self._update_generate_state()

    def _populate_voices(self, project: ProjectConfig) -> None:
        engine = KokoroEngine() if project.engine == "kokoro" else FakeEngine()
        voices = [
            voice.id
            for voice in engine.list_voices()
            if project.language in voice.languages
        ]
        self.voice_menu.configure(values=(_USE_SCRIPT_VOICE, *voices))
        self.voice.set(_USE_SCRIPT_VOICE)

    def _choose_video(self) -> None:
        selected = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.mov *.mkv *.webm"), ("All files", "*")]
        )
        if selected:
            self.video.set(selected)
            if self._output_was_suggested:
                stem = Path(selected).stem
                self.output.set(str(Path("builds") / f"{stem}-capcut"))
            self._inspect_video(Path(selected))

    def _inspect_video(self, path: Path) -> None:
        self.video_summary.set("Inspecting video…")
        self.video_metadata.configure(foreground=self.MUTED)
        self._set_status("Inspecting video…", self.PRIMARY)
        threading.Thread(
            target=self._probe_video_worker, args=(path,), daemon=True
        ).start()

    def _probe_video_worker(self, path: Path) -> None:
        try:
            info = probe_video(path)
        except Script2VideoError as exc:
            self.root.after(0, self._video_probe_failed, str(exc))
            return
        self.root.after(0, self._video_probe_finished, info)

    def _video_probe_finished(self, info: VideoInfo) -> None:
        minutes, seconds = divmod(round(info.duration_seconds), 60)
        dimensions = (
            f"  ·  {info.width}×{info.height}"
            if info.width is not None and info.height is not None
            else ""
        )
        self.video_metadata.configure(foreground=self.MUTED)
        self.video_summary.set(f"{minutes:02d}:{seconds:02d}{dimensions}")
        self._video_valid = True
        self._update_generate_state()
        self._set_status("Ready", self.SUCCESS)

    def _video_probe_failed(self, error: str) -> None:
        self._video_valid = False
        self.video_metadata.configure(foreground=self.ERROR)
        self.video_summary.set(error)
        self._update_generate_state()
        self._set_status("Video inspection failed", self.ERROR)

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory()
        if selected:
            self._output_was_suggested = False
            self.output.set(selected)

    def _toggle_advanced(self) -> None:
        self._advanced_visible = not self._advanced_visible
        if self._advanced_visible:
            self.advanced.grid(row=4, column=1, columnspan=2, sticky="w", pady=(8, 0))
            self.advanced_button.configure(text="Advanced  ▴")
        else:
            self.advanced.grid_remove()
            self.advanced_button.configure(text="Advanced  ▾")

    def _toggle_topmost(self) -> None:
        self.root.attributes("-topmost", self.topmost.get())

    def _update_alignment_state(self) -> None:
        self.alignment_menu.configure(
            state=(
                "readonly"
                if self.align.get() and _AI_ALIGNMENT_AVAILABLE
                else "disabled"
            )
        )

    def _set_status(self, message: str, color: str) -> None:
        self.status.set(message)
        self.status_dot.configure(foreground=color)

    def _generate(self) -> None:
        if not self.script.get() or not self.video.get() or not self.output.get():
            messagebox.showerror(
                "Missing input", "Choose a script, video, and output folder."
            )
            return
        command = [
            sys.executable,
            "-m",
            "script2video",
            "capcut",
            self.script.get(),
            "--video",
            self.video.get(),
            "--output",
            self.output.get(),
        ]
        if self.voice.get() != _USE_SCRIPT_VOICE:
            command.extend(["--voice", self.voice.get()])
        if not self.fit.get():
            command.append("--no-fit")
        if self.align.get():
            command.extend(["--align-model", self.align_model.get()])
        else:
            command.append("--no-align")

        self.generate_button.state(["disabled"])
        self.success_actions.grid_remove()
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.progress.start(12)
        self._set_status("Generating narration and captions…", self.PRIMARY)
        threading.Thread(
            target=self._run_generation, args=(command,), daemon=True
        ).start()

    def _run_generation(self, command: list[str]) -> None:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        output = (result.stdout + result.stderr).strip()
        self.root.after(0, self._generation_finished, result.returncode, output)

    def _generation_finished(self, returncode: int, output: str) -> None:
        self.progress.stop()
        self.progress.grid_remove()
        self.generate_button.state(["!disabled"])
        if returncode == 0:
            self._set_status(output or "CapCut package generated", self.SUCCESS)
            self.success_actions.grid(
                row=4, column=0, columnspan=3, sticky="w", pady=(10, 0)
            )
        else:
            self._set_status("Generation failed", self.ERROR)
            messagebox.showerror("Generation failed", output)

    def _open_output(self) -> None:
        path = Path(self.output.get()).expanduser()
        if not path.exists():
            messagebox.showinfo("Output not found", "Generate the package first.")
            return
        if sys.platform == "win32":
            subprocess.run(["explorer", str(path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)

    def _open_capcut(self) -> None:
        if sys.platform == "darwin":
            command = ["open", "-a", "CapCut"]
        elif sys.platform == "win32":
            command = ["cmd", "/c", "start", "", "CapCut"]
        else:
            messagebox.showerror(
                "CapCut unavailable",
                "Open CapCut manually on this operating system.",
            )
            return
        result = subprocess.run(command, capture_output=True, check=False)
        if result.returncode != 0:
            messagebox.showerror(
                "CapCut not found", "Could not open the CapCut application."
            )


def run_companion() -> None:
    root = tk.Tk()
    CompanionApp(root)
    root.mainloop()
