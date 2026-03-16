"""Tests for script generation."""

from radio_drama_creator.config import AppConfig
from radio_drama_creator.dramatize import HeuristicScriptGenerator, build_script_generator


class TestHeuristicScriptGenerator:
    def test_generates_scenes(self, sample_analysis, app_config):
        gen = HeuristicScriptGenerator()
        scenes = gen.generate(sample_analysis, app_config)
        assert len(scenes) == app_config.style.scenes
        for scene in scenes:
            assert scene.title
            assert scene.announcer_intro
            assert len(scene.beats) > 0

    def test_beats_have_speakers(self, sample_analysis, app_config):
        gen = HeuristicScriptGenerator()
        scenes = gen.generate(sample_analysis, app_config)
        for scene in scenes:
            for beat in scene.beats:
                assert beat.speaker
                assert beat.text
                assert beat.emotion


class TestBuildScriptGenerator:
    def test_default_is_heuristic(self, app_config):
        gen = build_script_generator(app_config)
        assert isinstance(gen, HeuristicScriptGenerator)

    def test_explicit_heuristic(self):
        config = AppConfig()
        config.models.script_backend = "heuristic"
        gen = build_script_generator(config)
        assert isinstance(gen, HeuristicScriptGenerator)
