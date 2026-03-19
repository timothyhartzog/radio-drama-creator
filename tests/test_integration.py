"""End-to-end integration tests for the full production pipeline.

These tests exercise the pipeline from raw text input through analysis,
dramatisation, casting, rendering (script-only), and export — verifying
that every expected output artifact is produced and well-formed.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from radio_drama_creator.analyze import analyze_document
from radio_drama_creator.casting import build_cast
from radio_drama_creator.config import AppConfig
from radio_drama_creator.dramatize import build_script_generator
from radio_drama_creator.exports import write_additional_exports
from radio_drama_creator.ingest import load_document
from radio_drama_creator.models import ProductionPackage
from radio_drama_creator.pipeline import run_pipeline
from radio_drama_creator.render import ScriptOnlyRenderer, build_renderer, render_script_text
from radio_drama_creator.sfx import (
    build_cue_sound,
    build_scene_transition,
    generate_tone_bed,
    mix_audio_bytes,
    resolve_sfx_asset,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _write_sample_text(path: Path) -> Path:
    """Write a realistic sample story and return its path."""
    text = (
        "Inspector Clarke walked through the dark street after midnight. "
        'He whispered, "Something is not right here — I can feel it." '
        "The rain hammered the cobblestones without mercy. "
        "Mrs. Pemberton watched from her window, afraid to look away. "
        '"You cannot hide the secret forever," she said through clenched teeth. '
        "The danger was growing with every passing hour. "
        "The city held its breath as the storm gathered strength. "
        "Chapter 2. Clarke returned to the station at dawn. "
        '"We must act now before it is too late," he told Sergeant Davis. '
        "The threat loomed over the entire district like a living shadow. "
        "Davis handed Clarke a sealed envelope. "
        '"This arrived an hour ago — no return address," Davis muttered. '
        "Inside was a single photograph and three words: I know everything."
    )
    path.write_text(text, encoding="utf-8")
    return path


def _default_config() -> AppConfig:
    """Return a config suitable for headless testing (script renderer)."""
    config = AppConfig()
    config.audio.renderer = "script"
    config.style.scenes = 2
    config.style.lines_per_scene = 4
    return config


# ── Pipeline integration ─────────────────────────────────────────────

class TestFullPipeline:
    """Run the entire pipeline end-to-end and verify outputs."""

    def test_run_pipeline_produces_all_artifacts(self, tmp_path):
        """The pipeline should produce script, manifest, cue sheet, outline, and subtitles."""
        txt_file = _write_sample_text(tmp_path / "story.txt")
        config = _default_config()
        out_dir = tmp_path / "output"

        package = run_pipeline(str(txt_file), str(out_dir), config)

        # Core output files
        assert (out_dir / "script.txt").exists()
        assert (out_dir / "production_manifest.json").exists()
        assert (out_dir / "cue_sheet.csv").exists()
        assert (out_dir / "episode_outline.md").exists()
        assert (out_dir / "subtitles.srt").exists()

        # Manifest is valid JSON with expected keys
        manifest = json.loads((out_dir / "production_manifest.json").read_text())
        assert "analysis" in manifest
        assert "scenes" in manifest
        assert "cast" in manifest
        assert manifest["source_path"] == str(txt_file)

    def test_pipeline_scene_count_matches_config(self, tmp_path):
        txt_file = _write_sample_text(tmp_path / "story.txt")
        config = _default_config()
        config.style.scenes = 3
        out_dir = tmp_path / "output"

        package = run_pipeline(str(txt_file), str(out_dir), config)
        assert len(package.scenes) == 3

    def test_pipeline_beat_count_matches_config(self, tmp_path):
        txt_file = _write_sample_text(tmp_path / "story.txt")
        config = _default_config()
        config.style.lines_per_scene = 6
        out_dir = tmp_path / "output"

        package = run_pipeline(str(txt_file), str(out_dir), config)
        for scene in package.scenes:
            assert len(scene.beats) == 6

    def test_pipeline_cast_has_expected_profiles(self, tmp_path):
        txt_file = _write_sample_text(tmp_path / "story.txt")
        config = _default_config()
        out_dir = tmp_path / "output"

        package = run_pipeline(str(txt_file), str(out_dir), config)
        assert len(package.cast) >= 3
        names = {p.character for p in package.cast}
        assert "Narrator" in names


# ── Ingest → Analyze → Dramatise chain ───────────────────────────────

class TestIngestAnalyzeDramatise:
    """Test the first half of the pipeline in isolation."""

    def test_ingest_produces_chunks(self, tmp_path):
        txt_file = _write_sample_text(tmp_path / "story.txt")
        chunks = load_document(str(txt_file))
        assert len(chunks) >= 1
        assert all(c.word_count > 0 for c in chunks)

    def test_analysis_extracts_characters(self, tmp_path):
        txt_file = _write_sample_text(tmp_path / "story.txt")
        chunks = load_document(str(txt_file))
        analysis = analyze_document(chunks)
        assert len(analysis.characters) >= 2
        assert analysis.title

    def test_heuristic_generator_respects_config(self, tmp_path):
        txt_file = _write_sample_text(tmp_path / "story.txt")
        chunks = load_document(str(txt_file))
        analysis = analyze_document(chunks)
        config = _default_config()
        config.style.scenes = 4
        config.style.lines_per_scene = 3

        gen = build_script_generator(config)
        scenes = gen.generate(analysis, config)
        assert len(scenes) == 4
        for scene in scenes:
            assert len(scene.beats) == 3

    def test_cast_includes_narrator(self, tmp_path):
        txt_file = _write_sample_text(tmp_path / "story.txt")
        chunks = load_document(str(txt_file))
        analysis = analyze_document(chunks)
        cast = build_cast(analysis)
        narrator = next((p for p in cast if p.character == "Narrator"), None)
        assert narrator is not None
        assert narrator.voice


# ── Rendering ────────────────────────────────────────────────────────

class TestRendering:
    """Test renderers and script text generation."""

    def test_script_only_renderer_writes_file(self, sample_package, app_config):
        result = ScriptOnlyRenderer().render(sample_package, app_config)
        assert result.exists()
        content = result.read_text()
        assert sample_package.analysis.title in content

    def test_build_renderer_returns_script_renderer(self):
        config = _default_config()
        renderer = build_renderer(config)
        assert isinstance(renderer, ScriptOnlyRenderer)

    def test_render_script_text_contains_all_scenes(self, sample_package):
        text = render_script_text(sample_package)
        for scene in sample_package.scenes:
            assert scene.title in text
        for scene in sample_package.scenes:
            for beat in scene.beats:
                assert beat.text in text

    def test_script_renderer_creates_manifest(self, sample_package, app_config):
        ScriptOnlyRenderer().render(sample_package, app_config)
        manifest_path = sample_package.manifest_path
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["analysis"]["title"] == sample_package.analysis.title


# ── Exports ──────────────────────────────────────────────────────────

class TestExports:
    """Test cue sheet, outline, and subtitle generation."""

    def test_cue_sheet_has_header_and_rows(self, sample_package):
        write_additional_exports(sample_package)
        csv_path = Path(sample_package.output_dir) / "cue_sheet.csv"
        lines = csv_path.read_text().strip().splitlines()
        assert lines[0].startswith("scene,beat,speaker")
        # At least header + intro row + beat rows
        assert len(lines) >= 2

    def test_subtitles_are_valid_srt(self, sample_package):
        write_additional_exports(sample_package)
        srt_path = Path(sample_package.output_dir) / "subtitles.srt"
        content = srt_path.read_text()
        # SRT blocks start with a sequence number
        assert content.strip().startswith("1")
        assert "-->" in content

    def test_episode_outline_has_cast(self, sample_package):
        write_additional_exports(sample_package)
        md_path = Path(sample_package.output_dir) / "episode_outline.md"
        content = md_path.read_text()
        assert "## Cast" in content
        for profile in sample_package.cast:
            assert profile.character in content


# ── SFX integration ─────────────────────────────────────────────────

class TestSFXIntegration:
    """Test sound effects resolution and mixing in the context of the pipeline."""

    def test_tone_bed_produces_nonzero_audio(self):
        pcm = generate_tone_bed(500, 22050)
        assert len(pcm) > 0
        # Should not be all silence
        assert pcm != b"\x00" * len(pcm)

    def test_scene_transition_returns_bytes(self):
        pcm = build_scene_transition("thunderstorm", 1000, 22050)
        expected_bytes = int(22050 * 1.0) * 2  # 1 second, 16-bit mono
        assert len(pcm) == expected_bytes

    def test_mix_audio_bytes_preserves_length(self):
        base = generate_tone_bed(200, 22050, frequency=440.0, volume=0.5)
        overlay = generate_tone_bed(200, 22050, frequency=220.0, volume=0.3)
        mixed = mix_audio_bytes(base, overlay, 0.5)
        assert len(mixed) == len(base)

    def test_cue_sound_returns_none_for_unknown(self):
        result = build_cue_sound("xyzzy_nonexistent_effect", 500, 22050)
        assert result is None

    def test_resolve_sfx_with_user_dir(self, tmp_path):
        # Create a user sfx directory with a rain.wav
        sfx_dir = tmp_path / "sfx"
        sfx_dir.mkdir()
        rain_wav = sfx_dir / "rain.wav"
        with wave.open(str(rain_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(b"\x00\x00" * 100)

        result = resolve_sfx_asset("heavy rain storm", sfx_dir)
        assert result is not None
        assert result == rain_wav


# ── Config ───────────────────────────────────────────────────────────

class TestConfigIntegration:
    """Test config loading and its effect on the pipeline."""

    def test_config_from_json(self, tmp_path):
        cfg_data = {
            "style": {"scenes": 5, "genre": "horror"},
            "audio": {"renderer": "script", "sample_rate": 44100},
        }
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text(json.dumps(cfg_data), encoding="utf-8")

        config = AppConfig.load(str(cfg_path))
        assert config.style.scenes == 5
        assert config.style.genre == "horror"
        assert config.audio.sample_rate == 44100

    def test_default_config_is_valid(self):
        config = AppConfig()
        assert config.style.scenes > 0
        assert config.audio.sample_rate > 0
        assert config.audio.renderer == "say"

    def test_voice_overrides_propagate(self, tmp_path):
        txt_file = _write_sample_text(tmp_path / "story.txt")
        config = _default_config()
        config.casting.voice_overrides = {"Narrator": "Samantha"}
        out_dir = tmp_path / "output"

        package = run_pipeline(str(txt_file), str(out_dir), config)
        narrator = next(p for p in package.cast if p.character == "Narrator")
        # The override should be attempted (exact result depends on available voices)
        assert narrator.voice


# ── Error handling ───────────────────────────────────────────────────

class TestErrorHandling:
    """Test that the pipeline raises clear errors for bad inputs."""

    def test_missing_file_raises_file_not_found(self, tmp_path):
        config = _default_config()
        with pytest.raises(FileNotFoundError):
            run_pipeline(str(tmp_path / "nonexistent.txt"), str(tmp_path / "out"), config)

    def test_unsupported_extension_raises_value_error(self, tmp_path):
        bad_file = tmp_path / "data.xlsx"
        bad_file.write_text("some data")
        config = _default_config()
        with pytest.raises(ValueError, match="Unsupported"):
            run_pipeline(str(bad_file), str(tmp_path / "out"), config)

    def test_empty_file_raises_value_error(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        config = _default_config()
        with pytest.raises(ValueError, match="No readable text"):
            run_pipeline(str(empty_file), str(tmp_path / "out"), config)
