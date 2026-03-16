from __future__ import annotations

from pathlib import Path
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import AppConfig
from .pipeline import run_pipeline


class RadioDramaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Radio Drama Creator")
        self.root.geometry("760x560")

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

        self._apply_light_theme()
        self._build_ui()

    def _apply_light_theme(self) -> None:
        """Configure a clean light theme for all ttk widgets."""
        style = ttk.Style()

        # Use clam as base - it's cross-platform and styleable
        available = style.theme_names()
        if "aqua" in available:
            style.theme_use("aqua")
        elif "clam" in available:
            style.theme_use("clam")

        # Light palette
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
        style.configure("Status.TLabel", foreground=primary, font=("Segoe UI", 11, "bold"))
        style.configure("Error.TLabel", foreground=danger, font=("Segoe UI", 11, "bold"))
        style.configure("Header.TLabel", foreground=primary, font=("Segoe UI", 13, "bold"), background=bg)
        style.configure("Muted.TLabel", foreground=muted, font=("Segoe UI", 10), background=bg)

        self._colors = {
            "bg": bg, "surface": surface, "primary": primary,
            "text": text_color, "muted": muted, "border": border, "danger": danger,
        }

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Radio Drama Creator", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(frame, text="Source document").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.source_var).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse", command=self._pick_source).grid(row=1, column=2, sticky="ew")

        ttk.Label(frame, text="Output folder").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.output_var).grid(row=2, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(frame, text="Choose", command=self._pick_output).grid(row=2, column=2, sticky="ew", pady=(10, 0))

        ttk.Label(frame, text="Config JSON").grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.config_var).grid(row=3, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(frame, text="Optional", command=self._pick_config).grid(row=3, column=2, sticky="ew", pady=(10, 0))

        controls = ttk.Frame(frame)
        controls.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(18, 0))
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

        ttk.Label(frame, text="Status").grid(row=5, column=0, sticky="w", pady=(18, 0))
        self.status_label = ttk.Label(frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=5, column=1, columnspan=2, sticky="w", pady=(18, 0))

        self.log = tk.Text(
            frame, height=18, wrap="word",
            bg=self._colors["surface"],
            fg=self._colors["text"],
            insertbackground=self._colors["text"],
            relief="solid",
            borderwidth=1,
            font=("Courier New", 10),
        )
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        self.log.tag_configure("error", foreground=self._colors["danger"])
        self.log.tag_configure("success", foreground="#16a34a")
        self.log.tag_configure("info", foreground=self._colors["primary"])
        frame.rowconfigure(6, weight=1)

    def _log_info(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n", "info")
        self.log.see(tk.END)

    def _log_error(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n", "error")
        self.log.see(tk.END)

    def _log_success(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n", "success")
        self.log.see(tk.END)

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
            config.models.script_backend = self.backend_var.get()
            config.style.genre = self.genre_var.get().strip() or config.style.genre

            try:
                config.style.scenes = max(1, int(self.scene_count_var.get()))
            except (ValueError, TypeError):
                config.style.scenes = 3

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
            config.audio.tts_model = preset_map.get(config.audio.tts_preset, config.audio.tts_model)
            if not self.audio_var.get():
                config.audio.renderer = "script"

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
