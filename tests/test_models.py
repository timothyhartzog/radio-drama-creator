"""Tests for data models."""

from radio_drama_creator.models import (
    DialogueBeat,
    DocumentChunk,
    ProductionPackage,
    Scene,
    StoryAnalysis,
    VoiceProfile,
)


class TestDocumentChunk:
    def test_creation(self):
        chunk = DocumentChunk(index=0, source_path="test.txt", text="hello world", word_count=2)
        assert chunk.index == 0
        assert chunk.word_count == 2

    def test_fields(self):
        chunk = DocumentChunk(index=1, source_path="/a/b.txt", text="some text", word_count=2)
        assert chunk.source_path == "/a/b.txt"


class TestStoryAnalysis:
    def test_creation(self, sample_analysis):
        assert sample_analysis.title == "The Dark Street"
        assert len(sample_analysis.characters) == 3
        assert "mystery" in sample_analysis.themes


class TestDialogueBeat:
    def test_defaults(self):
        beat = DialogueBeat(speaker="A", text="Hi", emotion="neutral")
        assert beat.cue == ""

    def test_with_cue(self):
        beat = DialogueBeat(speaker="A", text="Hi", emotion="neutral", cue="[waves]")
        assert beat.cue == "[waves]"


class TestScene:
    def test_creation(self, sample_scenes):
        scene = sample_scenes[0]
        assert "Dark Street" in scene.title
        assert len(scene.beats) == 2


class TestVoiceProfile:
    def test_defaults(self):
        vp = VoiceProfile(character="Test", voice="Tom", role="lead")
        assert vp.pace_wpm == 180
        assert vp.pitch == 45


class TestProductionPackage:
    def test_to_dict(self, sample_package):
        d = sample_package.to_dict()
        assert "analysis" in d
        assert "scenes" in d
        assert "cast" in d
        assert d["model_stack"]["script"] == "heuristic"

    def test_manifest_path(self, sample_package):
        assert sample_package.manifest_path.name == "production_manifest.json"
