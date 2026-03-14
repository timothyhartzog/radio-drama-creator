from __future__ import annotations

from pathlib import Path

from .analyze import analyze_document
from .casting import build_cast
from .config import AppConfig
from .dramatize import build_script_generator
from .exports import write_additional_exports
from .ingest import load_document
from .mlx_registry import resolve_script_model, resolve_tts_model, resolve_vision_model
from .models import ProductionPackage
from .render import build_renderer


def run_pipeline(source_path: str, output_dir: str, config: AppConfig) -> ProductionPackage:
    chunks = load_document(source_path)
    analysis = analyze_document(chunks)
    scenes = build_script_generator(config).generate(analysis, config)
    cast = build_cast(analysis, config)

    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    package = ProductionPackage(
        source_path=str(Path(source_path).expanduser().resolve()),
        analysis=analysis,
        scenes=scenes,
        cast=cast,
        output_dir=str(out_dir),
        model_stack={
            "script": _safe_repo(resolve_script_model, config.models.script_preset, config.models.mlx_model),
            "vision": _safe_repo(resolve_vision_model, config.models.vision_preset, config.models.vision_model),
            "tts": _safe_repo(resolve_tts_model, config.audio.tts_preset, config.audio.tts_model),
            "asr": config.models.asr_model,
            "aligner": config.models.aligner_model,
        },
    )
    build_renderer(config).render(package, config)
    write_additional_exports(package)
    return package


def _safe_repo(resolver, preset_name: str, fallback: str) -> str:
    try:
        return resolver(preset_name).repo
    except KeyError:
        return fallback
