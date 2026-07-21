from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable


class CompanionApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Script2Video for CapCut")
        self.root.geometry("620x390")
        self.root.attributes("-topmost", True)

        self.script = tk.StringVar(value="examples/minecraft.yaml")
        self.video = tk.StringVar()
        self.output = tk.StringVar(value="builds/capcut-package")
        self.voice = tk.StringVar()
        self.fit = tk.BooleanVar(value=True)
        self.align = tk.BooleanVar(value=True)
        self.align_model = tk.StringVar(value="tiny.en")
        self.topmost = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Choose a video, then generate the package.")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        self._path_row(frame, 0, "Script", self.script, self._choose_script)
        self._path_row(frame, 1, "Video", self.video, self._choose_video)
        self._path_row(frame, 2, "Output", self.output, self._choose_output)

        ttk.Label(frame, text="Voice override").grid(row=3, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=self.voice).grid(
            row=3, column=1, sticky="ew", padx=8, pady=8
        )
        ttk.Label(frame, text="Leave blank to use the script voice").grid(
            row=3, column=2, sticky="w"
        )

        ttk.Label(frame, text="Alignment model").grid(
            row=4, column=0, sticky="w", pady=8
        )
        ttk.Combobox(
            frame,
            textvariable=self.align_model,
            values=("tiny.en", "base.en", "tiny", "base"),
            state="readonly",
        ).grid(row=4, column=1, sticky="ew", padx=8, pady=8)

        options = ttk.Frame(frame)
        options.grid(row=5, column=1, columnspan=2, sticky="w", pady=8)
        ttk.Checkbutton(options, text="Fit narration to video", variable=self.fit).pack(
            side="left"
        )
        ttk.Checkbutton(options, text="AI word alignment", variable=self.align).pack(
            side="left", padx=18
        )
        ttk.Checkbutton(
            options,
            text="Always on top",
            variable=self.topmost,
            command=self._toggle_topmost,
        ).pack(side="left")

        actions = ttk.Frame(frame)
        actions.grid(row=6, column=0, columnspan=3, sticky="ew", pady=14)
        self.generate_button = ttk.Button(
            actions, text="Generate CapCut Package", command=self._generate
        )
        self.generate_button.pack(side="left")
        ttk.Button(actions, text="Open Output", command=self._open_output).pack(
            side="left", padx=8
        )
        ttk.Button(actions, text="Open CapCut", command=self._open_capcut).pack(
            side="left"
        )

        ttk.Separator(frame).grid(row=7, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Label(frame, textvariable=self.status, wraplength=570).grid(
            row=8, column=0, columnspan=3, sticky="w", pady=8
        )
        ttk.Label(
            frame,
            text=(
                "After generation: import narration.wav into the audio track, then "
                "use CapCut Desktop → Captions → Add Captions for captions.srt."
            ),
            wraplength=570,
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=8)
        frame.columnconfigure(1, weight=1)

    def _path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        command: Callable[[], None],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=8)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky="ew", padx=8, pady=8
        )
        ttk.Button(parent, text="Browse…", command=command).grid(
            row=row, column=2, pady=8
        )

    def _choose_script(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("YAML scripts", "*.yaml *.yml")])
        if selected:
            self.script.set(selected)

    def _choose_video(self) -> None:
        selected = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.mov *.mkv *.webm"), ("All files", "*")]
        )
        if selected:
            self.video.set(selected)

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory()
        if selected:
            self.output.set(selected)

    def _toggle_topmost(self) -> None:
        self.root.attributes("-topmost", self.topmost.get())

    def _generate(self) -> None:
        if not self.script.get() or not self.video.get() or not self.output.get():
            messagebox.showerror("Missing input", "Choose a script, video, and output folder.")
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
        if self.voice.get().strip():
            command.extend(["--voice", self.voice.get().strip()])
        if not self.fit.get():
            command.append("--no-fit")
        if self.align.get():
            command.extend(["--align-model", self.align_model.get()])
        else:
            command.append("--no-align")
        self.generate_button.state(["disabled"])
        self.status.set("Generating narration and subtitles…")
        threading.Thread(target=self._run_generation, args=(command,), daemon=True).start()

    def _run_generation(self, command: list[str]) -> None:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        output = (result.stdout + result.stderr).strip()
        self.root.after(0, self._generation_finished, result.returncode, output)

    def _generation_finished(self, returncode: int, output: str) -> None:
        self.generate_button.state(["!disabled"])
        if returncode == 0:
            self.status.set(output or "CapCut package generated successfully.")
        else:
            self.status.set("Generation failed. See the error dialog.")
            messagebox.showerror("Generation failed", output)

    def _open_output(self) -> None:
        path = Path(self.output.get()).expanduser()
        if path.exists():
            subprocess.run(["open", str(path)], check=False)
        else:
            messagebox.showinfo("Output not found", "Generate the package first.")

    def _open_capcut(self) -> None:
        result = subprocess.run(["open", "-a", "CapCut"], capture_output=True, check=False)
        if result.returncode != 0:
            messagebox.showerror("CapCut not found", "Could not open the CapCut application.")


def run_companion() -> None:
    root = tk.Tk()
    CompanionApp(root)
    root.mainloop()
