from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True)
class DocumentChunk:
    index: int
    source_path: str
    text: str
    word_count: int


@dataclass(slots=True)
class StoryAnalysis:
    title: str
    summary: str
    themes: list[str]
    setting: str
    mood: str
    characters: list[str]
    conflicts: list[str]
    source_excerpt: str


@dataclass(slots=True)
class DialogueBeat:
    speaker: str
    text: str
    emotion: str
    cue: str = ""


@dataclass(slots=True)
class Scene:
    title: str
    announcer_intro: str
    ambience: str
    beats: list[DialogueBeat] = field(default_factory=list)
    closing: str = ""


@dataclass(slots=True)
class VoiceProfile:
    character: str
    voice: str
    role: str
    pace_wpm: int = 180
    pitch: int = 45


@dataclass(slots=True)
class ProductionPackage:
    source_path: str
    analysis: StoryAnalysis
    scenes: list[Scene]
    cast: list[VoiceProfile]
    output_dir: str
    model_stack: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "analysis": asdict(self.analysis),
            "scenes": [asdict(scene) for scene in self.scenes],
            "cast": [asdict(profile) for profile in self.cast],
            "output_dir": self.output_dir,
            "model_stack": self.model_stack,
        }

    @property
    def manifest_path(self) -> Path:
        return Path(self.output_dir) / "production_manifest.json"
