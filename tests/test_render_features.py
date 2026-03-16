"""Tests for the enhanced render module features (music beds, emotion TTS, sound effects)."""

import wave
from pathlib import Path

from radio_drama_creator.config import AppConfig
from radio_drama_creator.render import (
    ScriptOnlyRenderer,
    _build_tts_text,
    build_renderer,
    render_script_text,
)


class TestBuildTtsText:
    def test_dia_uses_emotion_tag(self):
        result = _build_tts_text("dia", "Clarke", "Something is wrong.", "fearful")
        assert "[S1]" in result
        assert "(gasps)" in result
        assert "Something is wrong." in result

    def test_dia_default_emotion(self):
        result = _build_tts_text("dia", "Clarke", "Hello.", "")
        assert "(measured)" in result

    def test_qwen_uses_descriptor(self):
        result = _build_tts_text("qwen3-tts", "Narrator", "Our story begins.", "urgent")
        assert "urgent" in result
        assert "fast-paced" in result

    def test_other_family_plain_text(self):
        result = _build_tts_text("kokoro", "Clarke", "Hello there.", "tense")
        assert result == "Hello there."


class TestBuildRenderer:
    def test_script_renderer(self):
        config = AppConfig()
        config.audio.renderer = "script"
        renderer = build_renderer(config)
        assert isinstance(renderer, ScriptOnlyRenderer)


class TestScriptOnlyRendererWithMusicBeds:
    def test_renders_script_text(self, sample_package, app_config):
        """Script-only renderer should produce script.txt regardless of music_beds setting."""
        app_config.audio.music_beds = True
        app_config.audio.sound_effects = True
        renderer = ScriptOnlyRenderer()
        result = renderer.render(sample_package, app_config)
        assert result.exists()
        assert result.name == "script.txt"


class TestConfigMusicBedsDefault:
    def test_defaults_to_false(self):
        config = AppConfig()
        assert config.audio.music_beds is False
        assert config.audio.sound_effects is False

    def test_can_enable(self):
        config = AppConfig()
        config.audio.music_beds = True
        config.audio.sound_effects = True
        assert config.audio.music_beds is True
        assert config.audio.sound_effects is True
