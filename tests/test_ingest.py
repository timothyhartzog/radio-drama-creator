"""Tests for document ingestion."""

import pytest

from radio_drama_creator.ingest import load_document


class TestLoadDocument:
    def test_load_txt(self, sample_text_file):
        chunks = load_document(sample_text_file)
        assert len(chunks) >= 1
        assert chunks[0].word_count > 0
        assert "Clarke" in chunks[0].text

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_document("/nonexistent/file.txt")

    def test_load_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("data")
        with pytest.raises(ValueError, match="Unsupported"):
            load_document(str(f))

    def test_load_empty_file_raises(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        with pytest.raises(ValueError, match="No readable text"):
            load_document(str(f))

    def test_chunking(self, tmp_path):
        text = " ".join(f"word{i}" for i in range(500))
        f = tmp_path / "long.txt"
        f.write_text(text)
        chunks = load_document(str(f), chunk_words=100)
        assert len(chunks) == 5
        assert all(c.word_count <= 100 for c in chunks)
