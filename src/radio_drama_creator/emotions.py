"""Canonical emotion vocabulary for TTS rendering.

Maps free-form emotion strings from the dramatiser to canonical emotions
that each TTS family recognises, ensuring consistent delivery.
"""

from __future__ import annotations

# Canonical emotions per TTS family
EMOTION_VOCAB: dict[str, list[str]] = {
    "dia": [
        "happy", "sad", "angry", "fearful", "disgusted",
        "surprised", "measured", "tender", "urgent", "haunted",
    ],
    "qwen3-tts": [
        "happy", "sad", "angry", "fearful", "surprised",
        "calm", "excited", "serious", "gentle", "dramatic",
    ],
    "kokoro": [
        "neutral", "happy", "sad", "angry", "surprised",
    ],
    "say": [
        "neutral",
    ],
}

# Map free-form emotions to the nearest canonical form
_SYNONYM_MAP: dict[str, str] = {
    "tense": "fearful",
    "anxious": "fearful",
    "worried": "fearful",
    "nervous": "fearful",
    "brooding": "sad",
    "melancholy": "sad",
    "gloomy": "sad",
    "somber": "sad",
    "warning": "urgent",
    "urgent": "angry",
    "furious": "angry",
    "rage": "angry",
    "joyful": "happy",
    "cheerful": "happy",
    "elated": "happy",
    "excited": "excited",
    "tender": "gentle",
    "loving": "gentle",
    "romantic": "gentle",
    "haunted": "fearful",
    "dread": "fearful",
    "horror": "fearful",
    "surprised": "surprised",
    "shocked": "surprised",
    "measured": "calm",
    "steady": "calm",
    "neutral": "neutral",
    "dramatic": "dramatic",
    "theatrical": "dramatic",
}


def normalize_emotion(emotion: str, tts_family: str) -> str:
    """Map a free-form emotion to the nearest canonical one for the given TTS family.

    Args:
        emotion: Free-form emotion string from the dramatiser.
        tts_family: TTS family name (e.g. "dia", "qwen3-tts", "kokoro", "say").

    Returns:
        A canonical emotion string that the TTS family recognises.
    """
    emotion_lower = emotion.lower().strip()
    vocab = EMOTION_VOCAB.get(tts_family, EMOTION_VOCAB.get("dia", []))

    # Direct match
    if emotion_lower in vocab:
        return emotion_lower

    # Synonym lookup
    mapped = _SYNONYM_MAP.get(emotion_lower, emotion_lower)
    if mapped in vocab:
        return mapped

    # Fallback: return the first vocab entry (most neutral)
    return vocab[0] if vocab else "measured"


def get_emotion_vocab(tts_family: str) -> list[str]:
    """Return the list of canonical emotions for a TTS family."""
    return list(EMOTION_VOCAB.get(tts_family, EMOTION_VOCAB.get("dia", [])))
