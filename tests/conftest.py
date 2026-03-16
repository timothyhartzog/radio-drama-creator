"""Shared fixtures for the Radio Drama Creator test suite."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from radio_drama_creator.config import AppConfig
from radio_drama_creator.models import (
    DialogueBeat,
    DocumentChunk,
    ProductionPackage,
    Scene,
    StoryAnalysis,
    VoiceProfile,
)


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test outputs."""
    return tmp_path


@pytest.fixture
def sample_text():
    """A short sample story text for testing."""
    return (
        "Inspector Clarke walked through the dark street. "
        'He whispered, "Something is not right here." '
        "The rain hammered the cobblestones. Mrs. Pemberton watched from her window. "
        '"You cannot hide the secret forever," she said. '
        "The danger was growing. The city held its breath. "
        "Chapter 2. Clarke returned to the station. "
        '"We must act now," he told Sergeant Davis. '
        "The threat loomed over the entire district."
    )


@pytest.fixture
def sample_text_file(tmp_path, sample_text):
    """Write sample text to a .txt file and return the path."""
    path = tmp_path / "sample.txt"
    path.write_text(sample_text, encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_chunks(sample_text):
    """Create DocumentChunks from the sample text."""
    words = sample_text.split()
    return [DocumentChunk(index=0, source_path="test.txt", text=sample_text, word_count=len(words))]


@pytest.fixture
def sample_analysis():
    """A pre-built StoryAnalysis fixture."""
    return StoryAnalysis(
        title="The Dark Street",
        summary="Inspector Clarke investigates a mystery in the city.",
        themes=["mystery", "danger", "secret"],
        setting="A restless city after dark",
        mood="brooding suspense",
        characters=["Clarke", "Pemberton", "Davis"],
        conflicts=["Something is not right here", "The danger was growing"],
        source_excerpt="Inspector Clarke walked through the dark street.",
    )


@pytest.fixture
def sample_scenes():
    """A list of Scene objects for testing."""
    return [
        Scene(
            title="Scene 1: The Dark Street",
            announcer_intro="Our story begins on a rain-soaked evening.",
            ambience="[Rain on cobblestones, distant thunder]",
            beats=[
                DialogueBeat(speaker="Clarke", text="Something is not right.", emotion="tense", cue="[leaning forward]"),
                DialogueBeat(speaker="Pemberton", text="You cannot hide it.", emotion="warning", cue=""),
            ],
            closing="The night deepened.",
        ),
    ]


@pytest.fixture
def sample_cast():
    """A list of VoiceProfile objects for testing."""
    return [
        VoiceProfile(character="Narrator", voice="Tom", role="narrator", pace_wpm=160),
        VoiceProfile(character="Clarke", voice="Daniel", role="lead", pace_wpm=180),
        VoiceProfile(character="Pemberton", voice="Karen", role="supporting", pace_wpm=170),
    ]


@pytest.fixture
def sample_package(sample_analysis, sample_scenes, sample_cast, tmp_path):
    """A complete ProductionPackage for testing."""
    out = str(tmp_path / "output")
    Path(out).mkdir(parents=True, exist_ok=True)
    return ProductionPackage(
        source_path="test.txt",
        analysis=sample_analysis,
        scenes=sample_scenes,
        cast=sample_cast,
        output_dir=out,
        model_stack={"script": "heuristic", "tts": "script"},
    )


@pytest.fixture
def app_config():
    """A default AppConfig for testing."""
    config = AppConfig()
    config.audio.renderer = "script"
    return config
