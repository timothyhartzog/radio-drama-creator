"""Tests for book extraction utilities."""

from radio_drama_creator.book_extraction import (
    extract_main_content,
    fix_unterminated_quotes,
    normalize_line_breaks,
)


class TestExtractMainContent:
    def test_extracts_between_markers(self):
        text = "Preface stuff.\nPROLOGUE\nThe story begins.\nABOUT THE AUTHOR\nBio here."
        result = extract_main_content(text)
        assert "The story begins" in result
        assert "Preface" not in result
        assert "Bio" not in result

    def test_case_insensitive(self):
        text = "before\nprologue\ncontent\nabout the author\nafter"
        result = extract_main_content(text)
        assert "content" in result

    def test_no_markers_returns_full(self):
        text = "Just some plain text without markers."
        result = extract_main_content(text)
        assert result == text

    def test_custom_markers(self):
        text = "intro\nCHAPTER 1\nmain content\nAPPENDIX\nextra"
        result = extract_main_content(text, start_marker="CHAPTER 1", end_marker="APPENDIX")
        assert "main content" in result


class TestNormalizeLineBreaks:
    def test_normalizes_multiple_newlines(self):
        text = "Hello\n\n\n\nWorld"
        result = normalize_line_breaks(text)
        assert "\n\n\n\n" not in result

    def test_preserves_content(self):
        text = "Line one\nLine two"
        result = normalize_line_breaks(text)
        assert "Line one" in result
        assert "Line two" in result


class TestFixUnterminatedQuotes:
    def test_handles_open_quotes(self):
        text = '"Hello there\nNext line.'
        result = fix_unterminated_quotes(text)
        # Should return a string without crashing
        assert isinstance(result, str)
        assert "Hello there" in result

    def test_already_terminated(self):
        text = '"Hello," she said.'
        result = fix_unterminated_quotes(text)
        assert '"Hello,"' in result
