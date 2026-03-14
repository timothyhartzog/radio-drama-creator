from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MLXModelPreset:
    key: str
    repo: str
    family: str
    role: str
    notes: str
    default_voice: str = ""
    default_language: str = "English"
    default_lang_code: str = "a"
    sample_rate: int = 24000


SCRIPT_MODEL_PRESETS: dict[str, MLXModelPreset] = {
    "qwen3-8b": MLXModelPreset(
        key="qwen3-8b",
        repo="mlx-community/Qwen3-8B-4bit",
        family="qwen3",
        role="script",
        notes="Balanced default for local radio-drama script generation.",
    ),
    "qwen3-14b": MLXModelPreset(
        key="qwen3-14b",
        repo="mlx-community/Qwen3-14B-4bit",
        family="qwen3",
        role="script",
        notes="Higher quality script model for Macs with more unified memory.",
    ),
}

VISION_MODEL_PRESETS: dict[str, MLXModelPreset] = {
    "qwen2.5-vl-7b": MLXModelPreset(
        key="qwen2.5-vl-7b",
        repo="mlx-community/Qwen2.5-VL-7B-Instruct-4bit",
        family="qwen-vl",
        role="vision",
        notes="Best default for scanned PDFs, page screenshots, and document images.",
    ),
    "qwen3-vl-8b": MLXModelPreset(
        key="qwen3-vl-8b",
        repo="mlx-community/Qwen3-VL-8B-Instruct-4bit",
        family="qwen-vl",
        role="vision",
        notes="Stronger multimodal reasoning for complex page layouts.",
    ),
}

TTS_MODEL_PRESETS: dict[str, MLXModelPreset] = {
    "dia-1.6b": MLXModelPreset(
        key="dia-1.6b",
        repo="mlx-community/Dia-1.6B-fp16",
        family="dia",
        role="tts",
        notes="Dialogue-focused TTS with [S1]/[S2] style speaker tags.",
        sample_rate=44100,
    ),
    "qwen3-tts-0.6b": MLXModelPreset(
        key="qwen3-tts-0.6b",
        repo="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16",
        family="qwen3-tts",
        role="tts",
        notes="Good general-purpose expressive TTS for local character rendering.",
        default_voice="Chelsie",
        default_language="English",
        sample_rate=24000,
    ),
    "qwen3-tts-1.7b": MLXModelPreset(
        key="qwen3-tts-1.7b",
        repo="mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
        family="qwen3-tts",
        role="tts",
        notes="Higher quality expressive TTS and voice design.",
        default_voice="Chelsie",
        default_language="English",
        sample_rate=24000,
    ),
    "kokoro-82m": MLXModelPreset(
        key="kokoro-82m",
        repo="mlx-community/Kokoro-82M-bf16",
        family="kokoro",
        role="tts",
        notes="Fastest lightweight TTS for fast iteration.",
        default_voice="af_heart",
        default_lang_code="a",
        sample_rate=24000,
    ),
}

ASR_MODEL_PRESETS: dict[str, MLXModelPreset] = {
    "whisper-large-v3-turbo": MLXModelPreset(
        key="whisper-large-v3-turbo",
        repo="mlx-community/whisper-large-v3-turbo-asr-fp16",
        family="whisper",
        role="asr",
        notes="Robust transcription for local QA.",
    ),
    "qwen3-aligner-0.6b": MLXModelPreset(
        key="qwen3-aligner-0.6b",
        repo="mlx-community/Qwen3-ForcedAligner-0.6B-8bit",
        family="qwen3-aligner",
        role="aligner",
        notes="Word-level alignment for subtitles and timing checks.",
    ),
}


def resolve_script_model(name: str) -> MLXModelPreset:
    return _resolve_preset(name, SCRIPT_MODEL_PRESETS)


def resolve_vision_model(name: str) -> MLXModelPreset:
    return _resolve_preset(name, VISION_MODEL_PRESETS)


def resolve_tts_model(name: str) -> MLXModelPreset:
    return _resolve_preset(name, TTS_MODEL_PRESETS)


def resolve_asr_model(name: str) -> MLXModelPreset:
    return _resolve_preset(name, ASR_MODEL_PRESETS)


def available_model_presets() -> dict[str, list[MLXModelPreset]]:
    return {
        "script": list(SCRIPT_MODEL_PRESETS.values()),
        "vision": list(VISION_MODEL_PRESETS.values()),
        "tts": list(TTS_MODEL_PRESETS.values()),
        "asr": list(ASR_MODEL_PRESETS.values()),
    }


def _resolve_preset(name: str, presets: dict[str, MLXModelPreset]) -> MLXModelPreset:
    if name in presets:
        return presets[name]
    for preset in presets.values():
        if name == preset.repo:
            return preset
    raise KeyError(f"Unknown MLX model preset: {name}")
