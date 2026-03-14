from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import AppConfig
from .pipeline import run_pipeline


class RadioDramaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Radio Drama Creator")
        self.root.geometry("760x520")

        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.cwd() / "output_gui"))
        self.config_var = tk.StringVar()
        self.backend_var = tk.StringVar(value="heuristic")
        self.audio_var = tk.BooleanVar(value=True)
        self.genre_var = tk.StringVar(value="mystery")
        self.scene_count_var = tk.IntVar(value=3)
        self.script_preset_var = tk.StringVar(value="qwen3-8b")
        self.tts_preset_var = tk.StringVar(value="dia-1.6b")
        self.status_var = tk.StringVar(value="Choose a document to begin.")

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Source document").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse", command=self._pick_source).grid(row=0, column=2, sticky="ew")

        ttk.Label(frame, text="Output folder").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(frame, text="Choose", command=self._pick_output).grid(row=1, column=2, sticky="ew", pady=(10, 0))

        ttk.Label(frame, text="Config JSON").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.config_var).grid(row=2, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(frame, text="Optional", command=self._pick_config).grid(row=2, column=2, sticky="ew", pady=(10, 0))

        controls = ttk.Frame(frame)
        controls.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(18, 0))
        ttk.Label(controls, text="Script backend").pack(side="left")
        ttk.Combobox(
            controls,
            textvariable=self.backend_var,
            values=("heuristic", "mlx"),
            width=14,
            state="readonly",
        ).pack(side="left", padx=(10, 18))
        ttk.Checkbutton(controls, text="Render audio", variable=self.audio_var).pack(side="left")
        ttk.Label(controls, text="Genre").pack(side="left", padx=(18, 6))
        ttk.Entry(controls, textvariable=self.genre_var, width=14).pack(side="left")
        ttk.Label(controls, text="Scenes").pack(side="left", padx=(18, 6))
        ttk.Spinbox(controls, from_=1, to=8, textvariable=self.scene_count_var, width=5).pack(side="left")
        ttk.Label(controls, text="Script MLX").pack(side="left", padx=(18, 6))
        ttk.Combobox(
            controls,
            textvariable=self.script_preset_var,
            values=("qwen3-8b", "qwen3-14b"),
            width=12,
            state="readonly",
        ).pack(side="left")
        ttk.Label(controls, text="TTS MLX").pack(side="left", padx=(18, 6))
        ttk.Combobox(
            controls,
            textvariable=self.tts_preset_var,
            values=("dia-1.6b", "qwen3-tts-0.6b", "qwen3-tts-1.7b", "kokoro-82m"),
            width=14,
            state="readonly",
        ).pack(side="left")
        ttk.Button(controls, text="Show voices", command=self._show_voices).pack(side="right", padx=(0, 8))
        ttk.Button(controls, text="Create drama", command=self._start_run).pack(side="right")

        ttk.Label(frame, text="Status").grid(row=4, column=0, sticky="w", pady=(18, 0))
        ttk.Label(frame, textvariable=self.status_var).grid(row=4, column=1, columnspan=2, sticky="w", pady=(18, 0))

        self.log = tk.Text(frame, height=18, wrap="word")
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        frame.rowconfigure(5, weight=1)

    def _pick_source(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose source document",
            filetypes=[
                ("Supported documents", "*.txt *.md *.pdf *.rtf *.doc *.docx"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.source_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            self.output_var.set(path)

    def _pick_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose config JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.config_var.set(path)

    def _start_run(self) -> None:
        if not self.source_var.get().strip():
            messagebox.showerror("Missing source", "Choose a document before running the pipeline.")
            return

        self.status_var.set("Rendering in progress...")
        self.log.delete("1.0", tk.END)
        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self) -> None:
        try:
            config = AppConfig.load(self.config_var.get().strip() or None)
            config.models.script_backend = self.backend_var.get()
            config.style.genre = self.genre_var.get().strip() or config.style.genre
            config.style.scenes = max(1, int(self.scene_count_var.get()))
            config.models.script_preset = self.script_preset_var.get()
            if config.models.script_preset == "qwen3-14b":
                config.models.mlx_model = "mlx-community/Qwen3-14B-4bit"
            else:
                config.models.mlx_model = "mlx-community/Qwen3-8B-4bit"
            config.audio.tts_preset = self.tts_preset_var.get()
            preset_map = {
                "dia-1.6b": "mlx-community/Dia-1.6B-fp16",
                "qwen3-tts-0.6b": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16",
                "qwen3-tts-1.7b": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
                "kokoro-82m": "mlx-community/Kokoro-82M-bf16",
            }
            config.audio.tts_model = preset_map[config.audio.tts_preset]
            if not self.audio_var.get():
                config.audio.renderer = "script"

            package = run_pipeline(self.source_var.get(), self.output_var.get(), config)
        except Exception as exc:
            self.root.after(0, lambda: self._handle_error(exc))
            return

        self.root.after(0, lambda: self._handle_success(package.output_dir))

    def _handle_error(self, exc: Exception) -> None:
        self.status_var.set("Run failed.")
        self.log.insert(tk.END, f"{type(exc).__name__}: {exc}\n")
        messagebox.showerror("Radio Drama Creator", str(exc))

    def _handle_success(self, output_dir: str) -> None:
        self.status_var.set("Radio drama complete.")
        self.log.insert(tk.END, f"Finished.\nOutput: {output_dir}\n")
        self.log.insert(tk.END, f"Script: {Path(output_dir) / 'script.txt'}\n")
        manifest = Path(output_dir) / "production_manifest.json"
        if manifest.exists():
            self.log.insert(tk.END, f"Manifest: {manifest}\n")
        cue_sheet = Path(output_dir) / "cue_sheet.csv"
        if cue_sheet.exists():
            self.log.insert(tk.END, f"Cue sheet: {cue_sheet}\n")
        subtitles = Path(output_dir) / "subtitles.srt"
        if subtitles.exists():
            self.log.insert(tk.END, f"Subtitles: {subtitles}\n")
        audio = Path(output_dir) / "radio_drama.wav"
        if audio.exists():
            self.log.insert(tk.END, f"Audio: {audio}\n")

    def _show_voices(self) -> None:
        from .casting import list_available_voices

        voices = list_available_voices()
        preview = "\n".join(voices[:40])
        if len(voices) > 40:
            preview += "\n..."
        self.log.delete("1.0", tk.END)
        self.log.insert(tk.END, f"Available macOS voices ({len(voices)} total):\n{preview}\n")


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "aqua" in style.theme_names():
        style.theme_use("aqua")
    RadioDramaApp(root)
    root.mainloop()
