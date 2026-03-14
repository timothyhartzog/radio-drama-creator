from __future__ import annotations

import subprocess

from .config import AppConfig
from .models import StoryAnalysis, VoiceProfile


DEFAULT_VOICES = [
    ("Narrator", "Tom"),
    ("Lead", "Samantha"),
    ("Confidant", "Karen"),
    ("Rival", "Daniel"),
    ("Witness", "Moira"),
    ("Shadow", "Alex"),
]


def build_cast(analysis: StoryAnalysis, config: AppConfig | None = None) -> list[VoiceProfile]:
    available = list_available_voices()
    config = config or AppConfig()
    assigned: list[VoiceProfile] = []
    characters = ["Narrator", "Lead", "Confidant", "Rival", "Witness", "Shadow"]
    for index, name in enumerate([name for name in analysis.characters if name != "Narrator"][:3], start=1):
        characters[index] = name

    for index, character in enumerate(characters[:6]):
        fallback_role, preferred_voice = DEFAULT_VOICES[index % len(DEFAULT_VOICES)]
        override_voice = config.casting.voice_overrides.get(character)
        voice_choice = override_voice or preferred_voice
        voice = voice_choice if voice_choice in available else available[index % len(available)]
        role = fallback_role if character == "Narrator" else character
        default_pace = 165 if character == "Narrator" else 185
        pace = config.casting.pace_overrides.get(character, default_pace)
        pitch = 42 if character == "Narrator" else 48 + (index * 2)
        assigned.append(
            VoiceProfile(
                character=character,
                voice=voice,
                role=role,
                pace_wpm=pace,
                pitch=pitch,
            )
        )
    return assigned


def voice_for_speaker(cast: list[VoiceProfile], speaker: str) -> VoiceProfile:
    for profile in cast:
        if profile.character == speaker:
            return profile
    return cast[0]


def list_available_voices() -> list[str]:
    try:
        result = subprocess.run(
            ["/usr/bin/say", "-v", "?"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return [voice for _, voice in DEFAULT_VOICES]

    voices: list[str] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        voices.append(stripped.split()[0])
    return voices or [voice for _, voice in DEFAULT_VOICES]
