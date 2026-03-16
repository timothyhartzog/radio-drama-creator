"""Emotion-aware TTS synthesis layer.

Maps dramatic emotions to voice synthesis parameters (pitch, speed, energy)
for richer, more expressive radio drama output.  Works with any TTS backend
by providing per-line parameter adjustments.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmotionProfile:
    """Synthesis parameters derived from a dramatic emotion tag."""

    emotion: str
    pitch_shift: float  # semitones relative to baseline (0 = neutral)
    speed_factor: float  # multiplier (1.0 = normal)
    energy: float  # 0.0-1.0 intensity scale
    breathiness: float  # 0.0-1.0
    description: str  # human-readable note for manifests


# Canonical emotion map — covers the emotions produced by the heuristic
# dramatizer and common MLX script outputs.
EMOTION_PROFILES: dict[str, EmotionProfile] = {
    "measured": EmotionProfile(
        emotion="measured",
        pitch_shift=0.0,
        speed_factor=0.95,
        energy=0.4,
        breathiness=0.1,
        description="Calm, controlled delivery",
    ),
    "tense": EmotionProfile(
        emotion="tense",
        pitch_shift=1.0,
        speed_factor=1.05,
        energy=0.7,
        breathiness=0.2,
        description="Tight, clipped pacing with rising pitch",
    ),
    "urgent": EmotionProfile(
        emotion="urgent",
        pitch_shift=2.0,
        speed_factor=1.15,
        energy=0.85,
        breathiness=0.15,
        description="Fast, pressured delivery",
    ),
    "anxious": EmotionProfile(
        emotion="anxious",
        pitch_shift=1.5,
        speed_factor=1.10,
        energy=0.65,
        breathiness=0.35,
        description="Shaky, breathless quality",
    ),
    "haunted": EmotionProfile(
        emotion="haunted",
        pitch_shift=-1.0,
        speed_factor=0.88,
        energy=0.35,
        breathiness=0.45,
        description="Low, hollow, distant tone",
    ),
    "tender": EmotionProfile(
        emotion="tender",
        pitch_shift=-0.5,
        speed_factor=0.90,
        energy=0.3,
        breathiness=0.4,
        description="Soft, warm, intimate",
    ),
    "angry": EmotionProfile(
        emotion="angry",
        pitch_shift=2.5,
        speed_factor=1.12,
        energy=0.95,
        breathiness=0.05,
        description="Loud, sharp, forceful",
    ),
    "fearful": EmotionProfile(
        emotion="fearful",
        pitch_shift=2.0,
        speed_factor=1.20,
        energy=0.6,
        breathiness=0.5,
        description="High, rushed, trembling",
    ),
    "sorrowful": EmotionProfile(
        emotion="sorrowful",
        pitch_shift=-2.0,
        speed_factor=0.82,
        energy=0.25,
        breathiness=0.35,
        description="Slow, heavy, grief-laden",
    ),
    "joyful": EmotionProfile(
        emotion="joyful",
        pitch_shift=1.5,
        speed_factor=1.08,
        energy=0.8,
        breathiness=0.1,
        description="Bright, lilting, warm energy",
    ),
    "suspicious": EmotionProfile(
        emotion="suspicious",
        pitch_shift=0.5,
        speed_factor=0.92,
        energy=0.55,
        breathiness=0.2,
        description="Guarded, narrowed, deliberate",
    ),
    "commanding": EmotionProfile(
        emotion="commanding",
        pitch_shift=-1.5,
        speed_factor=0.95,
        energy=0.9,
        breathiness=0.0,
        description="Deep, authoritative, resonant",
    ),
    "whispering": EmotionProfile(
        emotion="whispering",
        pitch_shift=0.0,
        speed_factor=0.85,
        energy=0.15,
        breathiness=0.8,
        description="Near-silent, secretive",
    ),
    "desperate": EmotionProfile(
        emotion="desperate",
        pitch_shift=3.0,
        speed_factor=1.18,
        energy=0.9,
        breathiness=0.3,
        description="Strained, pleading, raw",
    ),
    "sarcastic": EmotionProfile(
        emotion="sarcastic",
        pitch_shift=0.5,
        speed_factor=0.93,
        energy=0.5,
        breathiness=0.15,
        description="Dry, flat with exaggerated peaks",
    ),
}

_DEFAULT_PROFILE = EmotionProfile(
    emotion="neutral",
    pitch_shift=0.0,
    speed_factor=1.0,
    energy=0.5,
    breathiness=0.1,
    description="Neutral baseline delivery",
)


def resolve_emotion(emotion: str) -> EmotionProfile:
    """Look up an emotion tag and return synthesis parameters.

    Unknown emotions fall back to the neutral baseline so the pipeline
    never breaks on unexpected tags from MLX script generation.
    """
    return EMOTION_PROFILES.get(emotion.lower().strip(), _DEFAULT_PROFILE)


def emotion_to_dia_tag(emotion: str) -> str:
    """Convert an emotion tag into Dia-style inline cues.

    Dia supports tags like ``(laughs)``, ``(gasps)``, ``(sighs)`` etc.
    We map our richer emotion vocabulary onto these where possible.
    """
    profile = resolve_emotion(emotion)
    mapping = {
        "joyful": "(laughs softly)",
        "fearful": "(gasps)",
        "sorrowful": "(sighs deeply)",
        "desperate": "(voice breaking)",
        "angry": "(sharply)",
        "whispering": "(whispering)",
        "anxious": "(nervously)",
        "haunted": "(distant, hollow)",
        "tender": "(gently)",
    }
    return mapping.get(profile.emotion, f"({profile.emotion})")


def emotion_to_qwen_descriptor(emotion: str) -> str:
    """Convert an emotion tag to a Qwen3-TTS style descriptor string."""
    profile = resolve_emotion(emotion)
    parts = [profile.emotion]
    if profile.speed_factor > 1.1:
        parts.append("fast-paced")
    elif profile.speed_factor < 0.9:
        parts.append("slow")
    if profile.energy > 0.75:
        parts.append("intense")
    elif profile.energy < 0.3:
        parts.append("subdued")
    return ", ".join(parts)


def apply_pace_adjustment(base_wpm: int, emotion: str) -> int:
    """Adjust speaking pace (words-per-minute) based on emotion profile."""
    profile = resolve_emotion(emotion)
    return max(100, min(250, int(base_wpm * profile.speed_factor)))
