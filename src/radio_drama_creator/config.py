from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass(slots=True)
class ModelSettings:
    script_backend: str = "heuristic"
    mlx_model: str = "mlx-community/Qwen3-8B-4bit"
    script_preset: str = "qwen3-8b"
    vision_backend: str = "none"
    vision_model: str = "mlx-community/Qwen2.5-VL-7B-Instruct-4bit"
    vision_preset: str = "qwen2.5-vl-7b"
    asr_model: str = "mlx-community/whisper-large-v3-turbo-asr-fp16"
    aligner_model: str = "mlx-community/Qwen3-ForcedAligner-0.6B-8bit"
    max_new_tokens: int = 1400
    temperature: float = 0.8


@dataclass(slots=True)
class AudioSettings:
    renderer: str = "say"
    tts_model: str = "mlx-community/Dia-1.6B-fp16"
    tts_preset: str = "dia-1.6b"
    tts_voice: str = ""
    tts_language: str = "English"
    tts_lang_code: str = "a"
    sample_rate: int = 22050
    line_gap_ms: int = 350
    scene_gap_ms: int = 1200
    master_volume: float = 1.0
    include_closing_scene_gap: bool = False
    music_beds: bool = False
    sound_effects: bool = False


@dataclass(slots=True)
class StyleSettings:
    scenes: int = 3
    lines_per_scene: int = 8
    narration_ratio: float = 0.25
    decade_flavor: str = "1930s golden-age radio"
    tone: str = "suspenseful, theatrical, intimate"
    genre: str = "mystery"
    announcer_name: str = "Narrator"


@dataclass(slots=True)
class CastingSettings:
    voice_overrides: dict[str, str] = field(default_factory=dict)
    pace_overrides: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class AppConfig:
    models: ModelSettings = field(default_factory=ModelSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    style: StyleSettings = field(default_factory=StyleSettings)
    casting: CastingSettings = field(default_factory=CastingSettings)

    @classmethod
    def load(cls, path: str | None) -> "AppConfig":
        if not path:
            return cls()

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            models=ModelSettings(**data.get("models", {})),
            audio=AudioSettings(**data.get("audio", {})),
            style=StyleSettings(**data.get("style", {})),
            casting=CastingSettings(**data.get("casting", {})),
        )
