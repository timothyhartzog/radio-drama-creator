"""Tests for the emotion-aware TTS module."""

from radio_drama_creator.emotion_tts import (
    EmotionProfile,
    apply_pace_adjustment,
    emotion_to_dia_tag,
    emotion_to_qwen_descriptor,
    resolve_emotion,
)


class TestResolveEmotion:
    def test_known_emotion(self):
        profile = resolve_emotion("tense")
        assert profile.emotion == "tense"
        assert profile.pitch_shift == 1.0
        assert profile.speed_factor == 1.05

    def test_unknown_emotion_returns_neutral(self):
        profile = resolve_emotion("bewildered")
        assert profile.emotion == "neutral"
        assert profile.pitch_shift == 0.0
        assert profile.speed_factor == 1.0

    def test_case_insensitive(self):
        profile = resolve_emotion("URGENT")
        assert profile.emotion == "urgent"

    def test_whitespace_stripped(self):
        profile = resolve_emotion("  haunted  ")
        assert profile.emotion == "haunted"

    def test_all_profiles_have_valid_ranges(self):
        from radio_drama_creator.emotion_tts import EMOTION_PROFILES
        for name, profile in EMOTION_PROFILES.items():
            assert 0.0 <= profile.energy <= 1.0, f"{name} energy out of range"
            assert 0.0 <= profile.breathiness <= 1.0, f"{name} breathiness out of range"
            assert 0.5 <= profile.speed_factor <= 1.5, f"{name} speed out of range"


class TestEmotionToDiaTag:
    def test_joyful(self):
        tag = emotion_to_dia_tag("joyful")
        assert "(laughs" in tag

    def test_fearful(self):
        tag = emotion_to_dia_tag("fearful")
        assert "(gasps)" in tag

    def test_unknown_wraps_name(self):
        tag = emotion_to_dia_tag("bewildered")
        assert "(neutral)" in tag


class TestEmotionToQwenDescriptor:
    def test_urgent(self):
        desc = emotion_to_qwen_descriptor("urgent")
        assert "urgent" in desc
        assert "fast-paced" in desc

    def test_sorrowful(self):
        desc = emotion_to_qwen_descriptor("sorrowful")
        assert "sorrowful" in desc
        assert "slow" in desc

    def test_angry_intense(self):
        desc = emotion_to_qwen_descriptor("angry")
        assert "intense" in desc


class TestApplyPaceAdjustment:
    def test_neutral_no_change(self):
        pace = apply_pace_adjustment(180, "measured")
        # measured has speed_factor 0.95 -> 171
        assert 100 <= pace <= 250

    def test_urgent_faster(self):
        base = 180
        pace = apply_pace_adjustment(base, "urgent")
        assert pace > base

    def test_sorrowful_slower(self):
        base = 180
        pace = apply_pace_adjustment(base, "sorrowful")
        assert pace < base

    def test_clamped_to_range(self):
        pace = apply_pace_adjustment(50, "sorrowful")
        assert pace >= 100
        pace = apply_pace_adjustment(300, "desperate")
        assert pace <= 250
