"""Tests for emotion vocabulary normalisation."""

from radio_drama_creator.emotions import normalize_emotion, get_emotion_vocab


class TestNormalizeEmotion:
    def test_direct_match(self):
        assert normalize_emotion("happy", "dia") == "happy"

    def test_synonym_mapping(self):
        assert normalize_emotion("tense", "dia") == "fearful"
        assert normalize_emotion("joyful", "dia") == "happy"

    def test_case_insensitive(self):
        assert normalize_emotion("HAPPY", "dia") == "happy"
        assert normalize_emotion("Tense", "dia") == "fearful"

    def test_unknown_emotion_returns_default(self):
        result = normalize_emotion("flibbertigibbet", "dia")
        assert result in get_emotion_vocab("dia")

    def test_kokoro_limited_vocab(self):
        result = normalize_emotion("tense", "kokoro")
        assert result in get_emotion_vocab("kokoro")

    def test_say_always_neutral(self):
        assert normalize_emotion("happy", "say") == "neutral"

    def test_unknown_family_uses_dia(self):
        result = normalize_emotion("happy", "unknown_family")
        assert result == "happy"


class TestGetEmotionVocab:
    def test_dia_has_emotions(self):
        vocab = get_emotion_vocab("dia")
        assert len(vocab) > 0
        assert "happy" in vocab

    def test_kokoro_has_emotions(self):
        vocab = get_emotion_vocab("kokoro")
        assert "neutral" in vocab

    def test_unknown_family(self):
        vocab = get_emotion_vocab("nonexistent")
        assert len(vocab) > 0  # Falls back to dia
