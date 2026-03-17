"""Tests for the SFX and music bed resolver module."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from radio_drama_creator.sfx import (
    build_cue_sound,
    build_scene_transition,
    generate_silence_bed,
    generate_tone_bed,
    mix_audio_bytes,
    resolve_sfx_asset,
)


class TestGenerateSilenceBed:
    def test_returns_correct_length(self):
        duration_ms = 500
        sample_rate = 22050
        pcm = generate_silence_bed(duration_ms, sample_rate)
        expected_samples = int(sample_rate * (duration_ms / 1000.0))
        assert len(pcm) == expected_samples * 2

    def test_all_bytes_are_zero(self):
        pcm = generate_silence_bed(100, 16000)
        assert pcm == b"\x00\x00" * int(16000 * 0.1)


class TestGenerateToneBed:
    def test_returns_correct_length(self):
        duration_ms = 1000
        sample_rate = 22050
        pcm = generate_tone_bed(duration_ms, sample_rate)
        expected_samples = int(sample_rate * (duration_ms / 1000.0))
        assert len(pcm) == expected_samples * 2

    def test_returns_nonzero_bytes(self):
        pcm = generate_tone_bed(500, 22050, frequency=220.0, volume=0.05)
        assert any(b != 0 for b in pcm)

    def test_custom_frequency_and_volume(self):
        pcm = generate_tone_bed(200, 16000, frequency=440.0, volume=0.1)
        expected_samples = int(16000 * 0.2)
        assert len(pcm) == expected_samples * 2


class TestMixAudioBytes:
    def test_output_length_matches_base(self):
        base = generate_tone_bed(500, 16000, frequency=220.0, volume=0.05)
        overlay = generate_tone_bed(500, 16000, frequency=440.0, volume=0.05)
        mixed = mix_audio_bytes(base, overlay, overlay_volume=0.3)
        assert len(mixed) == len(base)

    def test_shorter_overlay_is_zero_padded(self):
        base = generate_tone_bed(500, 16000, frequency=220.0, volume=0.05)
        overlay = generate_tone_bed(100, 16000, frequency=440.0, volume=0.05)
        mixed = mix_audio_bytes(base, overlay, overlay_volume=0.3)
        assert len(mixed) == len(base)

    def test_mixing_silence_returns_base(self):
        base = generate_tone_bed(200, 16000, frequency=300.0, volume=0.1)
        silence = generate_silence_bed(200, 16000)
        mixed = mix_audio_bytes(base, silence, overlay_volume=0.5)
        assert mixed == base


class TestResolveSfxAsset:
    def test_returns_none_when_no_assets_exist(self):
        result = resolve_sfx_asset("rain and thunder")
        assert result is None

    def test_returns_none_for_unrecognized_cue(self):
        result = resolve_sfx_asset("xylophone solo")
        assert result is None

    def test_returns_path_when_matching_file_exists(self, tmp_path):
        sfx_dir = tmp_path / "sfx"
        sfx_dir.mkdir()
        rain_file = sfx_dir / "rain.wav"
        # Write a minimal valid WAV file
        with wave.open(str(rain_file), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 160)

        result = resolve_sfx_asset("gentle rain", sfx_dir=sfx_dir)
        assert result is not None
        assert result == rain_file

    def test_user_dir_takes_precedence(self, tmp_path):
        sfx_dir = tmp_path / "user_sfx"
        sfx_dir.mkdir()
        door_file = sfx_dir / "door.wav"
        with wave.open(str(door_file), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 160)

        result = resolve_sfx_asset("door slams", sfx_dir=sfx_dir)
        assert result == door_file


class TestBuildSceneTransition:
    def test_returns_bytes_of_expected_length(self):
        duration_ms = 2000
        sample_rate = 16000
        pcm = build_scene_transition("soft orchestral bed", duration_ms, sample_rate)
        expected_samples = int(sample_rate * (duration_ms / 1000.0))
        assert len(pcm) == expected_samples * 2

    def test_with_matching_asset(self, tmp_path):
        sfx_dir = tmp_path / "sfx"
        sfx_dir.mkdir()
        orchestral_file = sfx_dir / "orchestral.wav"
        num_samples = 16000 * 3  # 3 seconds
        with wave.open(str(orchestral_file), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * num_samples)

        pcm = build_scene_transition("orchestral swell", 2000, 16000, sfx_dir=sfx_dir)
        expected_samples = int(16000 * 2.0)
        assert len(pcm) == expected_samples * 2

    def test_fallback_to_tone_bed(self):
        pcm = build_scene_transition("unknown ambience type", 1000, 16000)
        expected_samples = int(16000 * 1.0)
        assert len(pcm) == expected_samples * 2
        assert any(b != 0 for b in pcm)


class TestBuildCueSound:
    def test_returns_none_for_unrecognized_cues(self):
        result = build_cue_sound("xylophone crescendo", 500, 16000)
        assert result is None

    def test_returns_none_for_empty_cue(self):
        result = build_cue_sound("", 500, 16000)
        assert result is None

    def test_returns_bytes_when_asset_exists(self, tmp_path):
        sfx_dir = tmp_path / "sfx"
        sfx_dir.mkdir()
        footsteps_file = sfx_dir / "footsteps.wav"
        with wave.open(str(footsteps_file), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 8000)

        result = build_cue_sound("footsteps under dialogue", 500, 16000, sfx_dir=sfx_dir)
        assert result is not None
        expected_samples = int(16000 * 0.5)
        assert len(result) == expected_samples * 2
