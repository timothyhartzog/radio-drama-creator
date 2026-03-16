"""Tests for character identification."""

from radio_drama_creator.character_identification import extract_dialogues


class TestExtractDialogues:
    def test_extracts_quoted_text(self):
        text = 'He said, "Hello there." She replied, "How are you?"'
        dialogues = extract_dialogues(text)
        assert len(dialogues) == 2
        assert "Hello there" in dialogues[0]
        assert "How are you" in dialogues[1]

    def test_no_dialogues(self):
        text = "There was no spoken word in this passage."
        dialogues = extract_dialogues(text)
        assert len(dialogues) == 0

    def test_unicode_quotes(self):
        text = "\u201cHello,\u201d she said. \u201cGoodbye.\u201d"
        dialogues = extract_dialogues(text)
        assert len(dialogues) >= 1
