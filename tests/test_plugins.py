"""Tests for the plugin registry system."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from radio_drama_creator.config import AppConfig
from radio_drama_creator.dramatize import ScriptGenerator, build_script_generator
from radio_drama_creator.models import Scene, DialogueBeat, StoryAnalysis
from radio_drama_creator.plugins import PluginRegistry, SFXPack, registry
from radio_drama_creator.render import Renderer, build_renderer


# ── Fixtures ─────────────────────────────────────────────────────────

class StubRenderer(Renderer):
    """A minimal renderer for testing plugin registration."""
    def render(self, package, config):
        return Path(package.output_dir) / "stub_output.txt"


class StubScriptGenerator(ScriptGenerator):
    """A minimal script generator for testing plugin registration."""
    def generate(self, analysis, config):
        return [
            Scene(
                title="Plugin Scene",
                announcer_intro="From a plugin.",
                ambience="silence",
                beats=[DialogueBeat(speaker="Narrator", text="Hello from the plugin.", emotion="calm")],
                closing="End of plugin scene.",
            )
        ]


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure the global registry is clean before and after each test."""
    registry.clear()
    yield
    registry.clear()


# ── PluginRegistry unit tests ────────────────────────────────────────

class TestPluginRegistry:

    def test_register_and_get_renderer(self):
        reg = PluginRegistry()
        reg.register_renderer("stub", StubRenderer)
        assert reg.get_renderer("stub") is StubRenderer

    def test_register_and_get_script_backend(self):
        reg = PluginRegistry()
        reg.register_script_backend("stub", StubScriptGenerator)
        assert reg.get_script_backend("stub") is StubScriptGenerator

    def test_get_unknown_returns_none(self):
        reg = PluginRegistry()
        assert reg.get_renderer("nonexistent") is None
        assert reg.get_script_backend("nonexistent") is None
        assert reg.get_sfx_pack("nonexistent") is None

    def test_list_renderers(self):
        reg = PluginRegistry()
        reg.register_renderer("beta", StubRenderer)
        reg.register_renderer("alpha", StubRenderer)
        assert reg.list_renderers() == ["alpha", "beta"]

    def test_list_script_backends(self):
        reg = PluginRegistry()
        reg.register_script_backend("z_backend", StubScriptGenerator)
        reg.register_script_backend("a_backend", StubScriptGenerator)
        assert reg.list_script_backends() == ["a_backend", "z_backend"]

    def test_register_sfx_pack(self, tmp_path):
        reg = PluginRegistry()
        pack = SFXPack(name="horror", directory=tmp_path, catalog={"scream": "scream.wav"})
        reg.register_sfx_pack(pack)
        assert reg.get_sfx_pack("horror") is pack
        assert reg.list_sfx_packs() == ["horror"]

    def test_clear_removes_all(self):
        reg = PluginRegistry()
        reg.register_renderer("r", StubRenderer)
        reg.register_script_backend("s", StubScriptGenerator)
        reg.register_sfx_pack(SFXPack("p", Path(".")))
        reg.clear()
        assert reg.list_renderers() == []
        assert reg.list_script_backends() == []
        assert reg.list_sfx_packs() == []

    def test_discover_is_idempotent(self):
        reg = PluginRegistry()
        reg.discover()
        reg.discover()  # Should not raise


# ── SFXPack tests ───────────────────────────────────────────────────

class TestSFXPack:

    def test_resolve_finds_matching_asset(self, tmp_path):
        wav_path = tmp_path / "explosion.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(b"\x00\x00" * 50)

        pack = SFXPack("action", tmp_path, catalog={"explosion": "explosion.wav"})
        result = pack.resolve("a big explosion in the distance")
        assert result == wav_path

    def test_resolve_returns_none_for_no_match(self, tmp_path):
        pack = SFXPack("action", tmp_path, catalog={"explosion": "explosion.wav"})
        assert pack.resolve("gentle breeze") is None

    def test_resolve_returns_none_for_missing_file(self, tmp_path):
        pack = SFXPack("action", tmp_path, catalog={"explosion": "explosion.wav"})
        # File doesn't exist on disk
        assert pack.resolve("explosion") is None


# ── Integration with build_renderer / build_script_generator ────────

class TestPluginIntegration:

    def test_build_renderer_uses_plugin(self):
        registry.register_renderer("stub", StubRenderer)
        config = AppConfig()
        config.audio.renderer = "stub"
        renderer = build_renderer(config)
        assert isinstance(renderer, StubRenderer)

    def test_build_renderer_falls_back_for_unknown(self):
        config = AppConfig()
        config.audio.renderer = "totally_unknown_xyz"
        # Should fall back to MacOSSayRenderer without raising
        renderer = build_renderer(config)
        assert renderer is not None

    def test_build_script_generator_uses_plugin(self):
        registry.register_script_backend("stub", StubScriptGenerator)
        config = AppConfig()
        config.models.script_backend = "stub"
        gen = build_script_generator(config)
        assert isinstance(gen, StubScriptGenerator)

    def test_build_script_generator_falls_back_for_unknown(self):
        config = AppConfig()
        config.models.script_backend = "totally_unknown_xyz"
        gen = build_script_generator(config)
        # Should fall back to HeuristicScriptGenerator
        assert gen is not None

    def test_sfx_pack_resolves_via_sfx_module(self, tmp_path):
        from radio_drama_creator.sfx import resolve_sfx_asset

        wav_path = tmp_path / "laser.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(b"\x00\x00" * 50)

        pack = SFXPack("scifi", tmp_path, catalog={"laser": "laser.wav"})
        registry.register_sfx_pack(pack)

        result = resolve_sfx_asset("laser blast")
        assert result == wav_path


# ── Entry-point simulation ──────────────────────────────────────────

class TestEntryPointSimulation:
    """Simulate what an external package would do when loaded as an entry point."""

    def test_plugin_init_function_pattern(self):
        """A plugin's init function receives the registry and calls register_*."""
        def my_plugin_init(reg: PluginRegistry):
            reg.register_renderer("my_custom_tts", StubRenderer)
            reg.register_script_backend("my_custom_llm", StubScriptGenerator)

        # Simulate discovery calling the init function
        my_plugin_init(registry)

        assert registry.get_renderer("my_custom_tts") is StubRenderer
        assert registry.get_script_backend("my_custom_llm") is StubScriptGenerator
