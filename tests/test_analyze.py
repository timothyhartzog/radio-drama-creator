"""Tests for document analysis."""

from radio_drama_creator.analyze import analyze_document
from radio_drama_creator.models import DocumentChunk


class TestAnalyzeDocument:
    def test_basic_analysis(self, sample_chunks):
        analysis = analyze_document(sample_chunks)
        assert analysis.title
        assert len(analysis.characters) > 0
        assert len(analysis.themes) > 0

    def test_extracts_characters(self, sample_chunks):
        analysis = analyze_document(sample_chunks)
        assert "Clarke" in analysis.characters

    def test_detects_mood(self, sample_chunks):
        analysis = analyze_document(sample_chunks)
        assert analysis.mood  # Should detect something

    def test_detects_setting(self, sample_chunks):
        analysis = analyze_document(sample_chunks)
        assert analysis.setting

    def test_has_summary(self, sample_chunks):
        analysis = analyze_document(sample_chunks)
        assert len(analysis.summary) > 20

    def test_minimal_text(self):
        chunks = [DocumentChunk(index=0, source_path="t.txt", text="Hello world.", word_count=2)]
        analysis = analyze_document(chunks)
        assert analysis.title
        assert len(analysis.characters) > 0  # Defaults kick in
