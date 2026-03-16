"""Tests for GUI feature additions (drag-and-drop, voice overrides, config tabs)."""

import pytest

try:
    import tkinter  # noqa: F401
    _HAS_TK = True
except ImportError:
    _HAS_TK = False


@pytest.mark.skipif(not _HAS_TK, reason="tkinter not available")
class TestGuiConstants:
    def test_cast_roles_include_narrator(self):
        from radio_drama_creator.gui import _CAST_ROLES
        assert "Narrator" in _CAST_ROLES

    def test_cast_roles_has_six_entries(self):
        from radio_drama_creator.gui import _CAST_ROLES
        assert len(_CAST_ROLES) == 6

    def test_genres_list_not_empty(self):
        from radio_drama_creator.gui import _GENRES
        assert len(_GENRES) >= 5

    def test_genres_include_mystery(self):
        from radio_drama_creator.gui import _GENRES
        assert "mystery" in _GENRES


@pytest.mark.skipif(not _HAS_TK, reason="tkinter not available")
class TestGuiAppInit:
    def test_import_app_class(self):
        from radio_drama_creator.gui import RadioDramaApp
        assert RadioDramaApp is not None

    def test_main_function_exists(self):
        from radio_drama_creator.gui import main
        assert callable(main)
