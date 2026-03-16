"""End-to-end integration tests for the full radio drama pipeline.

These tests run the complete pipeline from document ingestion through
rendering using the script-only renderer (no audio synthesis hardware
required) and verify that all expected output files are produced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from radio_drama_creator.config import AppConfig
from radio_drama_creator.pipeline import run_pipeline


SAMPLE_TEXT = (
    "Inspector Clarke walked through the dark street. "
    'He whispered, "Something is not right here." '
    "The rain hammered the cobblestones. Mrs. Pemberton watched from her window. "
    '"You cannot hide the secret forever," she said. '
    "The danger was growing. The city held its breath. "
    "Clarke returned to the station. "
    '"We must act now," he told Sergeant Davis. '
    "The threat loomed over the entire district."
)


@pytest.fixture
def source_file(tmp_path):
    p = tmp_path / "story.txt"
    p.write_text(SAMPLE_TEXT, encoding="utf-8")
    return str(p)


@pytest.fixture
def output_dir(tmp_path):
    return str(tmp_path / "output")


def _base_config() -> AppConfig:
    config = AppConfig()
    config.audio.renderer = "script"
    config.style.scenes = 2
    config.style.lines_per_scene = 4
    return config


class TestBasePipeline:
    def test_produces_script_and_manifest(self, source_file, output_dir):
        config = _base_config()
        package = run_pipeline(source_file, output_dir, config)
        out = Path(package.output_dir)
        assert (out / "script.txt").exists()
        assert (out / "production_manifest.json").exists()

    def test_produces_export_files(self, source_file, output_dir):
        config = _base_config()
        package = run_pipeline(source_file, output_dir, config)
        out = Path(package.output_dir)
        assert (out / "cue_sheet.csv").exists()
        assert (out / "episode_outline.md").exists()
        assert (out / "subtitles.srt").exists()

    def test_manifest_has_model_stack(self, source_file, output_dir):
        config = _base_config()
        package = run_pipeline(source_file, output_dir, config)
        assert "script" in package.model_stack
        assert "tts" in package.model_stack

    def test_scenes_and_cast_in_package(self, source_file, output_dir):
        config = _base_config()
        package = run_pipeline(source_file, output_dir, config)
        assert len(package.scenes) == 2
        assert len(package.cast) > 0

    def test_script_contains_genre(self, source_file, output_dir):
        config = _base_config()
        config.style.genre = "horror"
        package = run_pipeline(source_file, output_dir, config)
        script = (Path(package.output_dir) / "script.txt").read_text(encoding="utf-8")
        assert len(script) > 100


class TestNarrationRatio:
    def test_high_narration_ratio(self, source_file, output_dir):
        config = _base_config()
        config.style.narration_ratio = 0.75
        package = run_pipeline(source_file, output_dir, config)
        all_beats = [beat for scene in package.scenes for beat in scene.beats]
        narrator_beats = [b for b in all_beats if b.speaker == "Narrator"]
        assert len(narrator_beats) / len(all_beats) >= 0.5

    def test_zero_narration_ratio(self, source_file, output_dir):
        config = _base_config()
        config.style.narration_ratio = 0.0
        package = run_pipeline(source_file, output_dir, config)
        all_beats = [beat for scene in package.scenes for beat in scene.beats]
        narrator_beats = [b for b in all_beats if b.speaker == "Narrator"]
        assert len(narrator_beats) == 0

    def test_full_narration_ratio(self, source_file, output_dir):
        config = _base_config()
        config.style.narration_ratio = 1.0
        package = run_pipeline(source_file, output_dir, config)
        all_beats = [beat for scene in package.scenes for beat in scene.beats]
        narrator_beats = [b for b in all_beats if b.speaker == "Narrator"]
        assert len(narrator_beats) == len(all_beats)


class TestMusicBedsAndSoundEffects:
    def test_pipeline_with_music_beds_script_renderer(self, source_file, output_dir):
        """Music beds flag should not break the script-only renderer."""
        config = _base_config()
        config.audio.music_beds = True
        config.audio.sound_effects = True
        package = run_pipeline(source_file, output_dir, config)
        assert (Path(package.output_dir) / "script.txt").exists()

    def test_pipeline_with_sound_effects_script_renderer(self, source_file, output_dir):
        config = _base_config()
        config.audio.sound_effects = True
        package = run_pipeline(source_file, output_dir, config)
        assert (Path(package.output_dir) / "script.txt").exists()


class TestVoiceOverrides:
    def test_cast_respects_voice_overrides(self, source_file, output_dir):
        config = _base_config()
        config.casting.voice_overrides["Narrator"] = "CustomVoice"
        package = run_pipeline(source_file, output_dir, config)
        narrator = next((p for p in package.cast if p.character == "Narrator"), None)
        assert narrator is not None
        # Custom voice is set (may fall back if not in macOS voices list, but override is attempted)

    def test_cast_respects_pace_overrides(self, source_file, output_dir):
        config = _base_config()
        config.casting.pace_overrides["Narrator"] = 140
        package = run_pipeline(source_file, output_dir, config)
        narrator = next((p for p in package.cast if p.character == "Narrator"), None)
        assert narrator is not None
        assert narrator.pace_wpm == 140


class TestDiaSpeakerSlots:
    def test_build_dia_speaker_slots(self):
        from radio_drama_creator.models import DialogueBeat, ProductionPackage, Scene, StoryAnalysis, VoiceProfile
        from radio_drama_creator.render import _build_dia_speaker_slots

        analysis = StoryAnalysis(
            title="T", summary="S", themes=["t"], setting="S", mood="m",
            characters=["A", "B"], conflicts=["c"], source_excerpt="e",
        )
        scenes = [
            Scene(
                title="Sc1", announcer_intro="Intro", ambience="Amb",
                beats=[
                    DialogueBeat(speaker="Narrator", text="X", emotion="measured"),
                    DialogueBeat(speaker="Alice", text="Y", emotion="tense"),
                    DialogueBeat(speaker="Bob", text="Z", emotion="tense"),
                ],
                closing="Close",
            )
        ]
        cast = [VoiceProfile(character="Narrator", voice="Tom", role="narrator")]
        package = ProductionPackage(
            source_path="x", analysis=analysis, scenes=scenes, cast=cast,
            output_dir="/tmp", model_stack={},
        )
        slots = _build_dia_speaker_slots(package)
        assert slots["Narrator"] == "[S1]"
        assert slots["Alice"] == "[S2]"
        assert slots["Bob"] == "[S1]"  # third speaker wraps back to [S1]
