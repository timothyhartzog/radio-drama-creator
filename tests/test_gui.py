"""Tests for GUI module (non-display tests)."""

import pytest

tk = pytest.importorskip("tkinter", reason="tkinter not available")


class TestGuiImport:
    def test_module_imports(self):
        from radio_drama_creator import gui
        assert hasattr(gui, "RadioDramaApp")
        assert hasattr(gui, "main")
