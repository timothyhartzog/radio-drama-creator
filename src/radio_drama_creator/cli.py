from __future__ import annotations

import argparse
from pathlib import Path

from .casting import list_available_voices
from .config import AppConfig
from .mlx_registry import available_model_presets, resolve_script_model, resolve_tts_model, resolve_vision_model
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="radio-drama",
        description="Create a local golden-age style radio drama from a document on macOS.",
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Path to a .txt, .md, .pdf, .rtf, .doc, or .docx file.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Directory where script, manifest, and audio will be written.",
    )
    parser.add_argument(
        "--config",
        help="Optional JSON config file.",
    )
    parser.add_argument(
        "--backend",
        choices=["heuristic", "mlx"],
        help="Override the script backend from config.",
    )
    parser.add_argument(
        "--script-only",
        action="store_true",
        help="Write the script and manifest without synthesizing audio.",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Print available macOS voices and exit.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print supported MLX model presets and exit.",
    )
    parser.add_argument(
        "--genre",
        help="Override the dramatic genre, for example mystery, noir, or horror.",
    )
    parser.add_argument(
        "--scenes",
        type=int,
        help="Override the number of scenes to generate.",
    )
    parser.add_argument(
        "--lines-per-scene",
        type=int,
        help="Override the number of dialogue beats per scene.",
    )
    parser.add_argument(
        "--script-preset",
        help="MLX script preset, for example qwen3-8b or qwen3-14b.",
    )
    parser.add_argument(
        "--tts-preset",
        help="MLX TTS preset, for example dia-1.6b, qwen3-tts-0.6b, or kokoro-82m.",
    )
    parser.add_argument(
        "--vision-preset",
        help="MLX vision preset for scanned pages, for example qwen2.5-vl-7b.",
    )
    parser.add_argument(
        "--renderer",
        choices=["say", "mlx_audio", "script"],
        help="Override audio renderer.",
    )
    parser.add_argument(
        "--sfx",
        action="store_true",
        help="Enable sound effects and music beds between scene transitions.",
    )
    parser.add_argument(
        "--sfx-dir",
        help="Path to a directory containing custom SFX WAV files.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_voices:
        for voice in list_available_voices():
            print(voice)
        return
    if args.list_models:
        for role, presets in available_model_presets().items():
            print(role.upper())
            for preset in presets:
                print(f"  {preset.key} -> {preset.repo}")
            print()
        return
    if not args.source:
        parser.error("the following arguments are required: source")

    config = AppConfig.load(args.config)
    if args.backend:
        config.models.script_backend = args.backend
    if args.script_only:
        config.audio.renderer = "script"
    if args.genre:
        config.style.genre = args.genre
    if args.scenes:
        config.style.scenes = args.scenes
    if args.lines_per_scene:
        config.style.lines_per_scene = args.lines_per_scene
    if args.script_preset:
        preset = resolve_script_model(args.script_preset)
        config.models.script_preset = preset.key
        config.models.mlx_model = preset.repo
    if args.tts_preset:
        preset = resolve_tts_model(args.tts_preset)
        config.audio.tts_preset = preset.key
        config.audio.tts_model = preset.repo
        if not config.audio.tts_voice:
            config.audio.tts_voice = preset.default_voice
        if config.audio.sample_rate == 22050:
            config.audio.sample_rate = preset.sample_rate
    if args.vision_preset:
        preset = resolve_vision_model(args.vision_preset)
        config.models.vision_preset = preset.key
        config.models.vision_model = preset.repo
        config.models.vision_backend = "mlx_vlm"
    if args.renderer:
        config.audio.renderer = args.renderer
    if args.sfx:
        config.audio.sfx_enabled = True
    if args.sfx_dir:
        config.audio.sfx_dir = args.sfx_dir
    package = run_pipeline(args.source, args.output, config)

    output_dir = Path(package.output_dir)
    print(f"Created radio drama package in {output_dir}")
    print(f"Script: {output_dir / 'script.txt'}")
    print(f"Manifest: {output_dir / 'production_manifest.json'}")
    print(f"Model stack: {package.model_stack}")
    if (output_dir / 'radio_drama.wav').exists():
        print(f"Audio: {output_dir / 'radio_drama.wav'}")
