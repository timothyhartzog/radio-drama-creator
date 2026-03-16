"""Procedural music beds and sound effects for scene transitions.

Generates short audio segments using sine-wave synthesis so the pipeline
can insert musical interludes and ambient cues without requiring external
audio assets.  All output is mono 16-bit PCM WAV.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def write_tone(
    path: Path,
    frequency: float,
    duration_ms: int,
    sample_rate: int = 22050,
    volume: float = 0.3,
    fade_ms: int = 80,
) -> Path:
    """Write a sine-wave tone with fade-in/out to a WAV file."""
    frames = int(sample_rate * duration_ms / 1000.0)
    fade_frames = int(sample_rate * fade_ms / 1000.0)
    data = bytearray()
    for i in range(frames):
        t = i / sample_rate
        sample = math.sin(2.0 * math.pi * frequency * t) * volume
        # Apply fade envelope
        if i < fade_frames:
            sample *= i / max(1, fade_frames)
        elif i > frames - fade_frames:
            sample *= (frames - i) / max(1, fade_frames)
        pcm = int(max(-1.0, min(1.0, sample)) * 32767)
        data.extend(struct.pack("<h", pcm))

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(data))
    return path


def write_chord(
    path: Path,
    frequencies: list[float],
    duration_ms: int,
    sample_rate: int = 22050,
    volume: float = 0.2,
    fade_ms: int = 120,
) -> Path:
    """Write a multi-frequency chord with fade envelope."""
    frames = int(sample_rate * duration_ms / 1000.0)
    fade_frames = int(sample_rate * fade_ms / 1000.0)
    n = max(1, len(frequencies))
    data = bytearray()
    for i in range(frames):
        t = i / sample_rate
        sample = sum(math.sin(2.0 * math.pi * f * t) for f in frequencies) / n * volume
        if i < fade_frames:
            sample *= i / max(1, fade_frames)
        elif i > frames - fade_frames:
            sample *= (frames - i) / max(1, fade_frames)
        pcm = int(max(-1.0, min(1.0, sample)) * 32767)
        data.extend(struct.pack("<h", pcm))

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(data))
    return path


# ---------------------------------------------------------------------------
# Pre-defined musical elements
# ---------------------------------------------------------------------------

# Minor-key chords for dramatic transitions (frequencies in Hz)
DRAMATIC_CHORDS = [
    [220.0, 261.6, 329.6],   # Am
    [196.0, 246.9, 293.7],   # Gm
    [174.6, 220.0, 261.6],   # Fm
    [164.8, 196.0, 246.9],   # Em
]

# Suspense tones — low frequencies for tension
SUSPENSE_TONES = [82.4, 98.0, 110.0, 73.4]

# Bright stingers for upbeat transitions
BRIGHT_TONES = [440.0, 523.3, 659.3]


def write_scene_transition(
    path: Path,
    scene_index: int,
    sample_rate: int = 22050,
    duration_ms: int = 1800,
) -> Path:
    """Generate a scene-transition music bed.

    Cycles through dramatic minor chords based on scene index to give
    each transition a slightly different character.
    """
    chord = DRAMATIC_CHORDS[scene_index % len(DRAMATIC_CHORDS)]
    return write_chord(path, chord, duration_ms, sample_rate, volume=0.18, fade_ms=300)


def write_opening_fanfare(
    path: Path,
    sample_rate: int = 22050,
    duration_ms: int = 2400,
) -> Path:
    """Generate an opening fanfare — a bright rising chord."""
    return write_chord(path, BRIGHT_TONES, duration_ms, sample_rate, volume=0.22, fade_ms=400)


def write_closing_sting(
    path: Path,
    sample_rate: int = 22050,
    duration_ms: int = 2000,
) -> Path:
    """Generate a closing dramatic sting — low suspense chord."""
    chord = [SUSPENSE_TONES[0], SUSPENSE_TONES[2], 130.8]  # Low Am
    return write_chord(path, chord, duration_ms, sample_rate, volume=0.20, fade_ms=500)


def write_ambience_bed(
    path: Path,
    ambience_hint: str,
    sample_rate: int = 22050,
    duration_ms: int = 1200,
) -> Path:
    """Generate a short ambient texture based on the scene ambience description.

    Uses keyword matching to select appropriate tonal qualities.
    """
    hint_lower = ambience_hint.lower()
    if any(w in hint_lower for w in ("storm", "thunder", "rain", "wind")):
        # Low rumble
        return write_chord(path, [55.0, 73.4, 110.0], duration_ms, sample_rate, volume=0.15, fade_ms=250)
    if any(w in hint_lower for w in ("bright", "morning", "sun", "cheerful")):
        return write_chord(path, [330.0, 440.0, 523.3], duration_ms, sample_rate, volume=0.12, fade_ms=200)
    if any(w in hint_lower for w in ("night", "dark", "shadow", "dread")):
        return write_chord(path, [82.4, 110.0, 146.8], duration_ms, sample_rate, volume=0.14, fade_ms=300)
    # Default: neutral warm pad
    return write_chord(path, [196.0, 246.9, 293.7], duration_ms, sample_rate, volume=0.12, fade_ms=200)
