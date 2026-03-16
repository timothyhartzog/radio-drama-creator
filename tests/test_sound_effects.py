"""Tests for the procedural sound effects and music beds module."""

import wave
from pathlib import Path

from radio_drama_creator.sound_effects import (
    write_ambience_bed,
    write_chord,
    write_closing_sting,
    write_opening_fanfare,
    write_scene_transition,
    write_tone,
)


class TestWriteTone:
    def test_creates_valid_wav(self, tmp_path):
        path = write_tone(tmp_path / "tone.wav", 440.0, 500)
        assert path.exists()
        with wave.open(str(path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getnframes() > 0

    def test_custom_sample_rate(self, tmp_path):
        path = write_tone(tmp_path / "tone.wav", 440.0, 300, sample_rate=44100)
        with wave.open(str(path), "rb") as wf:
            assert wf.getframerate() == 44100

    def test_duration_proportional(self, tmp_path):
        short = write_tone(tmp_path / "short.wav", 440.0, 200)
        long = write_tone(tmp_path / "long.wav", 440.0, 1000)
        with wave.open(str(short), "rb") as ws, wave.open(str(long), "rb") as wl:
            assert wl.getnframes() > ws.getnframes()


class TestWriteChord:
    def test_creates_valid_wav(self, tmp_path):
        path = write_chord(tmp_path / "chord.wav", [220.0, 330.0, 440.0], 600)
        assert path.exists()
        with wave.open(str(path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getnframes() > 0


class TestWriteSceneTransition:
    def test_creates_file(self, tmp_path):
        path = write_scene_transition(tmp_path / "trans.wav", 0)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_different_scenes_produce_output(self, tmp_path):
        for i in range(4):
            p = write_scene_transition(tmp_path / f"trans_{i}.wav", i)
            assert p.exists()


class TestWriteOpeningFanfare:
    def test_creates_file(self, tmp_path):
        path = write_opening_fanfare(tmp_path / "fanfare.wav")
        assert path.exists()
        with wave.open(str(path), "rb") as wf:
            assert wf.getnframes() > 0


class TestWriteClosingSting:
    def test_creates_file(self, tmp_path):
        path = write_closing_sting(tmp_path / "sting.wav")
        assert path.exists()


class TestWriteAmbienceBed:
    def test_storm_hint(self, tmp_path):
        path = write_ambience_bed(tmp_path / "storm.wav", "Thunder and rain in the distance")
        assert path.exists()

    def test_dark_hint(self, tmp_path):
        path = write_ambience_bed(tmp_path / "dark.wav", "A dark alley at night")
        assert path.exists()

    def test_bright_hint(self, tmp_path):
        path = write_ambience_bed(tmp_path / "bright.wav", "A bright sunny morning")
        assert path.exists()

    def test_neutral_fallback(self, tmp_path):
        path = write_ambience_bed(tmp_path / "neutral.wav", "An ordinary room")
        assert path.exists()
