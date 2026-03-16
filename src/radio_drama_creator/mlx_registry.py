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


# ---------------------------------------------------------------------------
# Script / LLM presets (document -> radio drama script)
# ---------------------------------------------------------------------------

SCRIPT_MODEL_PRESETS: dict[str, MLXModelPreset] = {
    # --- Qwen3 family (best creative writing + structured JSON output) ---
    "qwen3-8b": MLXModelPreset(
        key="qwen3-8b",
        repo="mlx-community/Qwen3-8B-4bit",
        family="qwen3",
        role="script",
        notes="Balanced default for local radio-drama script generation. Strong dialogue and roleplay.",
    ),
    "qwen3-14b": MLXModelPreset(
        key="qwen3-14b",
        repo="mlx-community/Qwen3-14B-4bit",
        family="qwen3",
        role="script",
        notes="Higher quality script model. Best creative writing in the Qwen3 family for Macs with 32GB+.",
    ),
    "qwen3-30b-a3b": MLXModelPreset(
        key="qwen3-30b-a3b",
        repo="mlx-community/Qwen3-30B-A3B-4bit",
        family="qwen3",
        role="script",
        notes="MoE model: 30B total, 3B active. Fast inference with strong quality. Good for 16GB Macs.",
    ),
    # --- Llama family (excellent all-around, strong narrative) ---
    "llama-3.3-8b": MLXModelPreset(
        key="llama-3.3-8b",
        repo="mlx-community/Llama-3.3-8B-Instruct-4bit",
        family="llama",
        role="script",
        notes="Meta's best 8B model. Excellent narrative structure and dialogue. Runs on 8GB+ Macs.",
    ),
    "llama-3.1-70b": MLXModelPreset(
        key="llama-3.1-70b",
        repo="mlx-community/Meta-Llama-3.1-70B-Instruct-4bit",
        family="llama",
        role="script",
        notes="Top-tier creative output. Requires 48GB+ unified memory (M2/M3/M4 Max or Ultra).",
    ),
    # --- Mistral family (fast, good structured output) ---
    "mistral-small-3-8b": MLXModelPreset(
        key="mistral-small-3-8b",
        repo="mlx-community/Mistral-Small-3.1-24B-Instruct-2503-4bit",
        family="mistral",
        role="script",
        notes="Fastest tokens/sec on mid-range hardware. Well-structured creative output.",
    ),
    # --- Gemma family (Google, strong creative writing) ---
    "gemma-3-12b": MLXModelPreset(
        key="gemma-3-12b",
        repo="mlx-community/gemma-3-12b-it-4bit",
        family="gemma",
        role="script",
        notes="Google's best mid-size model. Strong storytelling with good JSON adherence.",
    ),
    # --- Phi family (Microsoft, tiny but capable) ---
    "phi-4-14b": MLXModelPreset(
        key="phi-4-14b",
        repo="mlx-community/phi-4-4bit",
        family="phi",
        role="script",
        notes="Microsoft's compact model with strong instruction following and creative output.",
    ),
}

# ---------------------------------------------------------------------------
# Vision presets (scanned PDFs, page images)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# TTS presets (script -> audio)
# ---------------------------------------------------------------------------

TTS_MODEL_PRESETS: dict[str, MLXModelPreset] = {
    # --- Dia: built for multi-speaker dialogue with emotion tags ---
    "dia-1.6b": MLXModelPreset(
        key="dia-1.6b",
        repo="mlx-community/Dia-1.6B-fp16",
        family="dia",
        role="tts",
        notes="Best for radio drama. Built-in [S1]/[S2] multi-speaker + emotion tags (laughs, gasps). English only.",
        sample_rate=44100,
    ),
    # --- Qwen3-TTS: multilingual, voice cloning, emotion control ---
    "qwen3-tts-0.6b": MLXModelPreset(
        key="qwen3-tts-0.6b",
        repo="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16",
        family="qwen3-tts",
        role="tts",
        notes="Lightweight expressive TTS. 3-second voice cloning, 10 languages, natural emotion control.",
        default_voice="Chelsie",
        default_language="English",
        sample_rate=24000,
    ),
    "qwen3-tts-1.7b": MLXModelPreset(
        key="qwen3-tts-1.7b",
        repo="mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
        family="qwen3-tts",
        role="tts",
        notes="Higher quality TTS with voice design. Best for audiobook-quality character voices.",
        default_voice="Chelsie",
        default_language="English",
        sample_rate=24000,
    ),
    # --- Kokoro: fastest, lowest resource usage ---
    "kokoro-82m": MLXModelPreset(
        key="kokoro-82m",
        repo="mlx-community/Kokoro-82M-bf16",
        family="kokoro",
        role="tts",
        notes="Fastest TTS (36x real-time). 82M params, runs on any Mac. Good for fast iteration.",
        default_voice="af_heart",
        default_lang_code="a",
        sample_rate=24000,
    ),
    # --- F5-TTS: high fidelity with zero-shot voice cloning ---
    "f5-tts": MLXModelPreset(
        key="f5-tts",
        repo="mlx-community/F5-TTS-bf16",
        family="f5-tts",
        role="tts",
        notes="Diffusion-based TTS. Zero-shot voice cloning from reference audio. 7x real-time.",
        sample_rate=24000,
    ),
}

# ---------------------------------------------------------------------------
# ASR / Alignment presets (QA and subtitle timing)
# ---------------------------------------------------------------------------

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
