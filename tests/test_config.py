"""Tests for configuration management."""

import json
from pathlib import Path

import pytest

from radio_drama_creator.config import (
    AppConfig,
    AudioSettings,
    CastingSettings,
    ModelSettings,
    StyleSettings,
)


class TestModelSettings:
    def test_defaults(self):
        ms = ModelSettings()
        assert ms.script_backend == "heuristic"
        assert ms.temperature == 0.8


class TestAudioSettings:
    def test_defaults(self):
        a = AudioSettings()
        assert a.renderer == "say"
        assert a.line_gap_ms == 350
        assert a.scene_gap_ms == 1200


class TestStyleSettings:
    def test_defaults(self):
        s = StyleSettings()
        assert s.scenes == 3
        assert s.genre == "mystery"


class TestAppConfig:
    def test_default_load(self):
        config = AppConfig.load(None)
        assert isinstance(config, AppConfig)
        assert config.models.script_backend == "heuristic"

    def test_load_from_json(self, tmp_path):
        cfg = {"style": {"genre": "comedy", "scenes": 5}}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(cfg))
        config = AppConfig.load(str(path))
        assert config.style.genre == "comedy"
        assert config.style.scenes == 5

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            AppConfig.load("/nonexistent/config.json")

    def test_load_invalid_json_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json{{{")
        with pytest.raises(json.JSONDecodeError):
            AppConfig.load(str(path))
