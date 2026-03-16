from __future__ import annotations

from pathlib import Path
import subprocess
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import AppConfig
from .pipeline import run_pipeline


# Characters used in the cast panel
_CAST_ROLES = ["Narrator", "Lead", "Confidant", "Rival", "Witness", "Shadow"]

# Genre choices for the combobox
_GENRES = [
    "mystery", "thriller", "romance", "sci-fi", "horror",
    "comedy", "drama", "noir", "western", "fantasy",
]


class RadioDramaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Radio Drama Creator")
        self.root.geometry("920x700")

        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path.cwd() / "output_gui"))
        self.config_var = tk.StringVar()
        self.backend_var = tk.StringVar(value="heuristic")
        self.audio_var = tk.BooleanVar(value=True)
        self.genre_var = tk.StringVar(value="mystery")
        self.scene_count_var = tk.IntVar(value=3)
        self.lines_per_scene_var = tk.IntVar(value=8)
        self.narration_ratio_var = tk.DoubleVar(value=0.25)
        self.tone_var = tk.StringVar(value="suspenseful, theatrical, intimate")
        self.decade_var = tk.StringVar(value="1930s golden-age radio")
        self.script_preset_var = tk.StringVar(value="qwen3-8b")
        self.tts_preset_var = tk.StringVar(value="dia-1.6b")
        self.music_beds_var = tk.BooleanVar(value=False)
        self.sound_effects_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Choose a document or drag-and-drop to begin.")

        # Per-character voice override vars
        self._voice_vars: dict[str, tk.StringVar] = {}
        self._pace_vars: dict[str, tk.IntVar] = {}
        for role in _CAST_ROLES:
            self._voice_vars[role] = tk.StringVar()
            self._pace_vars[role] = tk.IntVar(value=165 if role == "Narrator" else 185)

        self._apply_light_theme()
        self._build_ui()
        self._setup_drag_and_drop()

    def _apply_light_theme(self) -> None:
        style = ttk.Style()

        available = style.theme_names()
        if "aqua" in available:
            style.theme_use("aqua")
        elif "clam" in available:
            style.theme_use("clam")

        bg = "#f8f9fa"
        surface = "#ffffff"
        primary = "#2563eb"
        text_color = "#1e293b"
        muted = "#64748b"
        border = "#e2e8f0"
        danger = "#dc2626"

        self.root.configure(bg=bg)

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=text_color, font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 11))
        style.configure("TCheckbutton", background=bg, foreground=text_color, font=("Segoe UI", 11))
        style.configure("TCombobox", font=("Segoe UI", 11))
        style.configure("TSpinbox", font=("Segoe UI", 11))
        style.configure("TEntry", font=("Segoe UI", 11))
        style.configure("TScale", background=bg)
        style.configure("Status.TLabel", foreground=primary, font=("Segoe UI", 11, "bold"))
        style.configure("Error.TLabel", foreground=danger, font=("Segoe UI", 11, "bold"))
        style.configure("Header.TLabel", foreground=primary, font=("Segoe UI", 13, "bold"), background=bg)
        style.configure("Section.TLabel", foreground=text_color, font=("Segoe UI", 11, "bold"), background=bg)
        style.configure("Muted.TLabel", foreground=muted, font=("Segoe UI", 10), background=bg)
        style.configure("DropZone.TLabel", background=surface, foreground=muted,
                        font=("Segoe UI", 11), relief="solid", borderwidth=2)

        self._colors = {
            "bg": bg, "surface": surface, "primary": primary,
            "text": text_color, "muted": muted, "border": border, "danger": danger,
        }

    def _build_ui(self) -> None:
        # Use a notebook for tabbed layout
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Tab 1: Main production tab ---
        main_tab = ttk.Frame(notebook, padding=14)
        notebook.add(main_tab, text="Production")
        main_tab.columnconfigure(1, weight=1)

        ttk.Label(main_tab, text="Radio Drama Creator", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        # Drop zone / source row
        self.drop_label = ttk.Label(
            main_tab,
            text="Drop a document here or click Browse",
            style="DropZone.TLabel",
            anchor="center",
        )
        self.drop_label.grid(row=1, column=0, columnspan=3, sticky="ew", ipady=14, pady=(0, 6))

        ttk.Label(main_tab, text="Source document").grid(row=2, column=0, sticky="w")
        ttk.Entry(main_tab, textvariable=self.source_var).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(main_tab, text="Browse", command=self._pick_source).grid(row=2, column=2, sticky="ew")

        ttk.Label(main_tab, text="Output folder").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(main_tab, textvariable=self.output_var).grid(row=3, column=1, sticky="ew", padx=8, pady=(8, 0))
        ttk.Button(main_tab, text="Choose", command=self._pick_output).grid(row=3, column=2, sticky="ew", pady=(8, 0))

        ttk.Label(main_tab, text="Config JSON").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(main_tab, textvariable=self.config_var).grid(row=4, column=1, sticky="ew", padx=8, pady=(8, 0))
        ttk.Button(main_tab, text="Optional", command=self._pick_config).grid(row=4, column=2, sticky="ew", pady=(8, 0))

        # Controls row
        controls = ttk.Frame(main_tab)
        controls.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        ttk.Label(controls, text="Script backend").pack(side="left")
        ttk.Combobox(
            controls, textvariable=self.backend_var,
            values=("heuristic", "mlx"), width=14, state="readonly",
        ).pack(side="left", padx=(10, 18))
        ttk.Checkbutton(controls, text="Render audio", variable=self.audio_var).pack(side="left")
        ttk.Checkbutton(controls, text="Music beds", variable=self.music_beds_var).pack(side="left", padx=(12, 0))
        ttk.Checkbutton(controls, text="Sound FX", variable=self.sound_effects_var).pack(side="left", padx=(8, 0))

        ttk.Label(controls, text="Script MLX").pack(side="left", padx=(18, 6))
        ttk.Combobox(
            controls, textvariable=self.script_preset_var,
            values=("qwen3-8b", "qwen3-14b"), width=12, state="readonly",
        ).pack(side="left")
        ttk.Label(controls, text="TTS MLX").pack(side="left", padx=(18, 6))
        ttk.Combobox(
            controls, textvariable=self.tts_preset_var,
            values=("dia-1.6b", "qwen3-tts-0.6b", "qwen3-tts-1.7b", "kokoro-82m"),
            width=14, state="readonly",
        ).pack(side="left")

        # Action buttons
        btn_row = ttk.Frame(main_tab)
        btn_row.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(btn_row, text="Create drama", command=self._start_run).pack(side="right")
        ttk.Button(btn_row, text="Audition line", command=self._audition_line).pack(side="right", padx=(0, 8))
        ttk.Button(btn_row, text="Show voices", command=self._show_voices).pack(side="right", padx=(0, 8))

        # Status
        ttk.Label(main_tab, text="Status").grid(row=7, column=0, sticky="w", pady=(12, 0))
        self.status_label = ttk.Label(main_tab, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=7, column=1, columnspan=2, sticky="w", pady=(12, 0))

        # Log
        self.log = tk.Text(
            main_tab, height=14, wrap="word",
            bg=self._colors["surface"], fg=self._colors["text"],
            insertbackground=self._colors["text"],
            relief="solid", borderwidth=1, font=("Courier New", 10),
        )
        self.log.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        self.log.tag_configure("error", foreground=self._colors["danger"])
        self.log.tag_configure("success", foreground="#16a34a")
        self.log.tag_configure("info", foreground=self._colors["primary"])
        main_tab.rowconfigure(8, weight=1)

        # --- Tab 2: Style & Pacing config ---
        style_tab = ttk.Frame(notebook, padding=14)
        notebook.add(style_tab, text="Style & Pacing")
        style_tab.columnconfigure(1, weight=1)

        ttk.Label(style_tab, text="Style & Pacing Settings", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(style_tab, text="Genre").grid(row=1, column=0, sticky="w")
        ttk.Combobox(
            style_tab, textvariable=self.genre_var, values=_GENRES, width=20,
        ).grid(row=1, column=1, sticky="w", padx=8)

        ttk.Label(style_tab, text="Tone").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(style_tab, textvariable=self.tone_var, width=50).grid(
            row=2, column=1, sticky="ew", padx=8, pady=(8, 0)
        )

        ttk.Label(style_tab, text="Decade flavor").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(style_tab, textvariable=self.decade_var, width=30).grid(
            row=3, column=1, sticky="w", padx=8, pady=(8, 0)
        )

        ttk.Label(style_tab, text="Scenes").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(style_tab, from_=1, to=12, textvariable=self.scene_count_var, width=6).grid(
            row=4, column=1, sticky="w", padx=8, pady=(8, 0)
        )

        ttk.Label(style_tab, text="Lines per scene").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(style_tab, from_=2, to=30, textvariable=self.lines_per_scene_var, width=6).grid(
            row=5, column=1, sticky="w", padx=8, pady=(8, 0)
        )

        ttk.Label(style_tab, text="Narration ratio").grid(row=6, column=0, sticky="w", pady=(8, 0))
        ratio_frame = ttk.Frame(style_tab)
        ratio_frame.grid(row=6, column=1, sticky="ew", padx=8, pady=(8, 0))
        self._ratio_label = ttk.Label(ratio_frame, text="0.25", width=5)
        self._ratio_label.pack(side="right")
        ttk.Scale(
            ratio_frame, from_=0.0, to=1.0, variable=self.narration_ratio_var,
            orient="horizontal", command=self._on_ratio_change,
        ).pack(side="left", fill="x", expand=True)

        ttk.Label(style_tab, text="", style="Muted.TLabel").grid(row=7, column=0, columnspan=2, pady=(16, 0))
        ttk.Label(
            style_tab,
            text="These settings control the dramatic structure: how many scenes are generated,\n"
                 "how many dialogue beats per scene, and the balance between narration and dialogue.",
            style="Muted.TLabel",
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # --- Tab 3: Cast & Voice Overrides ---
        cast_tab = ttk.Frame(notebook, padding=14)
        notebook.add(cast_tab, text="Cast & Voices")
        cast_tab.columnconfigure(2, weight=1)

        ttk.Label(cast_tab, text="Per-Character Voice Overrides", style="Header.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 12)
        )

        ttk.Label(cast_tab, text="Character", style="Section.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(cast_tab, text="Voice", style="Section.TLabel").grid(row=1, column=1, sticky="w", padx=(16, 0))
        ttk.Label(cast_tab, text="Pace (WPM)", style="Section.TLabel").grid(row=1, column=2, sticky="w", padx=(16, 0))
        ttk.Label(cast_tab, text="Audition", style="Section.TLabel").grid(row=1, column=3, sticky="w", padx=(16, 0))

        for idx, role in enumerate(_CAST_ROLES):
            row = idx + 2
            ttk.Label(cast_tab, text=role).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(cast_tab, textvariable=self._voice_vars[role], width=16).grid(
                row=row, column=1, sticky="w", padx=(16, 0), pady=4
            )
            ttk.Spinbox(
                cast_tab, from_=100, to=250, textvariable=self._pace_vars[role], width=6,
            ).grid(row=row, column=2, sticky="w", padx=(16, 0), pady=4)
            ttk.Button(
                cast_tab, text="Play",
                command=lambda r=role: self._audition_voice(r),
            ).grid(row=row, column=3, sticky="w", padx=(16, 0), pady=4)

        ttk.Label(
            cast_tab,
            text="Leave voice blank to use defaults. Enter a macOS voice name (e.g. Tom, Samantha)\n"
                 "or an MLX TTS voice identifier. Click Play to audition the voice.",
            style="Muted.TLabel",
        ).grid(row=len(_CAST_ROLES) + 2, column=0, columnspan=4, sticky="w", pady=(16, 0))

    def _setup_drag_and_drop(self) -> None:
        """Set up file drag-and-drop on the drop zone label.

        Uses tkinterdnd2 if available, otherwise falls back to
        binding a keyboard shortcut hint.
        """
        try:
            # tkinterdnd2 provides native DnD if installed
            self.root.tk.call("package", "require", "tkdnd")
            self.drop_label.drop_target_register("DND_Files")  # type: ignore[attr-defined]
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]
        except (tk.TclError, AttributeError):
            # tkdnd not available — allow clicking the drop zone as fallback
            self.drop_label.bind("<Button-1>", lambda _: self._pick_source())

    def _on_drop(self, event) -> None:
        """Handle a file dropped onto the drop zone."""
        raw = event.data if hasattr(event, "data") else ""
        # tkdnd wraps paths with spaces in braces
        path = raw.strip().strip("{}")
        if path and Path(path).is_file():
            self.source_var.set(path)
            self.drop_label.configure(text=f"Loaded: {Path(path).name}")
            self._log_info(f"File dropped: {path}")

    def _on_ratio_change(self, value: str) -> None:
        try:
            self._ratio_label.configure(text=f"{float(value):.2f}")
        except (ValueError, TypeError):
            pass

    # ------------------------------------------------------------------
    # Audition
    # ------------------------------------------------------------------

    def _audition_voice(self, role: str) -> None:
        """Speak a short test phrase with the voice configured for *role*."""
        voice = self._voice_vars[role].get().strip()
        if not voice:
            from .casting import DEFAULT_VOICES
            idx = _CAST_ROLES.index(role) if role in _CAST_ROLES else 0
            voice = DEFAULT_VOICES[idx % len(DEFAULT_VOICES)][1]
        pace = self._pace_vars[role].get()
        phrase = f"Hello, I am {role}. This is my voice."
        self._log_info(f"Auditioning {role} with voice '{voice}' at {pace} wpm...")
        threading.Thread(
            target=self._speak_audition, args=(voice, pace, phrase), daemon=True,
        ).start()

    def _audition_line(self) -> None:
        """Speak a generic dramatic audition line using the Narrator voice."""
        voice = self._voice_vars["Narrator"].get().strip() or "Tom"
        pace = self._pace_vars["Narrator"].get()
        phrase = (
            "From the velvet hush of the broadcast booth, "
            "our story begins on a rain-soaked evening."
        )
        self._log_info(f"Auditioning narrator line with voice '{voice}'...")
        threading.Thread(
            target=self._speak_audition, args=(voice, pace, phrase), daemon=True,
        ).start()

    @staticmethod
    def _speak_audition(voice: str, pace: int, text: str) -> None:
        try:
            subprocess.run(
                ["/usr/bin/say", "-v", voice, "-r", str(pace), text],
                check=False, capture_output=True,
            )
        except FileNotFoundError:
            pass  # say not available on this platform

    # ------------------------------------------------------------------
    # File pickers
    # ------------------------------------------------------------------

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
            self.drop_label.configure(text=f"Loaded: {Path(path).name}")

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

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def _start_run(self) -> None:
        source = self.source_var.get().strip()
        if not source:
            messagebox.showerror("Missing source", "Choose a document before running the pipeline.")
            return
        if not Path(source).exists():
            messagebox.showerror("File not found", f"Source document does not exist:\n{source}")
            return
        output = self.output_var.get().strip()
        if not output:
            messagebox.showerror("Missing output", "Choose an output folder.")
            return

        self.status_var.set("Rendering in progress...")
        self.status_label.configure(style="Status.TLabel")
        self.log.delete("1.0", tk.END)
        self._log_info("Starting pipeline...")
        thread = threading.Thread(target=self._run_pipeline, daemon=True)
        thread.start()

    def _run_pipeline(self) -> None:
        try:
            config_path = self.config_var.get().strip() or None
            if config_path and not Path(config_path).exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

            config = AppConfig.load(config_path)

            # Script settings
            config.models.script_backend = self.backend_var.get()
            config.models.script_preset = self.script_preset_var.get()
            if config.models.script_preset == "qwen3-14b":
                config.models.mlx_model = "mlx-community/Qwen3-14B-4bit"
            else:
                config.models.mlx_model = "mlx-community/Qwen3-8B-4bit"

            # Style settings from the Style & Pacing tab
            config.style.genre = self.genre_var.get().strip() or config.style.genre
            config.style.tone = self.tone_var.get().strip() or config.style.tone
            config.style.decade_flavor = self.decade_var.get().strip() or config.style.decade_flavor
            try:
                config.style.scenes = max(1, int(self.scene_count_var.get()))
            except (ValueError, TypeError):
                config.style.scenes = 3
            try:
                config.style.lines_per_scene = max(2, int(self.lines_per_scene_var.get()))
            except (ValueError, TypeError):
                config.style.lines_per_scene = 8
            try:
                config.style.narration_ratio = max(0.0, min(1.0, float(self.narration_ratio_var.get())))
            except (ValueError, TypeError):
                config.style.narration_ratio = 0.25

            # Audio settings
            config.audio.tts_preset = self.tts_preset_var.get()
            preset_map = {
                "dia-1.6b": "mlx-community/Dia-1.6B-fp16",
                "qwen3-tts-0.6b": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16",
                "qwen3-tts-1.7b": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
                "kokoro-82m": "mlx-community/Kokoro-82M-bf16",
            }
            config.audio.tts_model = preset_map.get(config.audio.tts_preset, config.audio.tts_model)
            config.audio.music_beds = self.music_beds_var.get()
            config.audio.sound_effects = self.sound_effects_var.get()
            if not self.audio_var.get():
                config.audio.renderer = "script"

            # Cast voice overrides from the Cast & Voices tab
            for role in _CAST_ROLES:
                voice = self._voice_vars[role].get().strip()
                if voice:
                    config.casting.voice_overrides[role] = voice
                pace = self._pace_vars[role].get()
                if pace and pace != (165 if role == "Narrator" else 185):
                    config.casting.pace_overrides[role] = pace

            package = run_pipeline(self.source_var.get(), self.output_var.get(), config)
        except FileNotFoundError as exc:
            self.root.after(0, lambda: self._handle_error(exc, "File Error"))
            return
        except ValueError as exc:
            self.root.after(0, lambda: self._handle_error(exc, "Validation Error"))
            return
        except RuntimeError as exc:
            self.root.after(0, lambda: self._handle_error(exc, "Runtime Error"))
            return
        except Exception as exc:
            self.root.after(0, lambda: self._handle_error(exc, "Unexpected Error"))
            return

        self.root.after(0, lambda: self._handle_success(package.output_dir))

    def _handle_error(self, exc: Exception, category: str = "Error") -> None:
        self.status_var.set(f"{category}: {type(exc).__name__}")
        self.status_label.configure(style="Error.TLabel")
        self._log_error(f"[{category}] {type(exc).__name__}: {exc}")
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        for line in tb[-3:]:
            self._log_error(line.rstrip())
        messagebox.showerror("Radio Drama Creator", f"{category}:\n{exc}")

    def _handle_success(self, output_dir: str) -> None:
        self.status_var.set("Radio drama complete!")
        self.status_label.configure(style="Status.TLabel")
        self._log_success("Finished successfully.")
        self._log_info(f"Output: {output_dir}")
        for name in ("script.txt", "production_manifest.json", "cue_sheet.csv", "subtitles.srt", "radio_drama.wav"):
            path = Path(output_dir) / name
            if path.exists():
                self._log_success(f"  {name} ({path.stat().st_size / 1024:.1f} KB)")

    # ------------------------------------------------------------------
    # Logging & voices
    # ------------------------------------------------------------------

    def _log_info(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n", "info")
        self.log.see(tk.END)

    def _log_error(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n", "error")
        self.log.see(tk.END)

    def _log_success(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n", "success")
        self.log.see(tk.END)

    def _show_voices(self) -> None:
        try:
            from .casting import list_available_voices
            voices = list_available_voices()
        except Exception as exc:
            self._log_error(f"Could not list voices: {exc}")
            return

        preview = "\n".join(voices[:40])
        if len(voices) > 40:
            preview += "\n..."
        self.log.delete("1.0", tk.END)
        self._log_info(f"Available macOS voices ({len(voices)} total):")
        self.log.insert(tk.END, preview + "\n")


def main() -> None:
    root = tk.Tk()
    RadioDramaApp(root)
    root.mainloop()
