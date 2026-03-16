"""Tests for Kokoro renderer utilities."""

from radio_drama_creator.kokoro_renderer import (
    check_if_chapter_heading,
    find_voice_for_gender_score,
    split_and_annotate_text,
)


class TestSplitAndAnnotateText:
    def test_separates_dialogue_and_narration(self):
        text = 'He walked in. "Hello," he said. She nodded.'
        segments = split_and_annotate_text(text)
        types = [s[1] for s in segments]
        assert "narration" in types
        assert "dialogue" in types

    def test_empty_text(self):
        assert split_and_annotate_text("") == []

    def test_only_narration(self):
        segments = split_and_annotate_text("Just narration here.")
        assert all(s[1] == "narration" for s in segments)


class TestCheckIfChapterHeading:
    def test_chapter_number(self):
        assert check_if_chapter_heading("Chapter 1") is True
        assert check_if_chapter_heading("Chapter 23") is True
        assert check_if_chapter_heading("CHAPTER 5") is True

    def test_part_number(self):
        assert check_if_chapter_heading("Part 2") is True
        assert check_if_chapter_heading("PART 1") is True

    def test_not_a_heading(self):
        assert check_if_chapter_heading("He walked away.") is False
        assert check_if_chapter_heading("The chapter ended.") is False


class TestFindVoiceForGenderScore:
    def test_masculine_voice(self):
        gender_map = {"John": {"gender_score": 2, "age": 35}}
        voice = find_voice_for_gender_score("John", gender_map)
        assert "am_" in voice  # Male voice prefix

    def test_feminine_voice(self):
        gender_map = {"Jane": {"gender_score": 8, "age": 30}}
        voice = find_voice_for_gender_score("Jane", gender_map)
        assert "af_" in voice or "bf_" in voice  # Female voice prefix

    def test_neutral_score(self):
        gender_map = {"Alex": {"gender_score": 5, "age": 25}}
        voice = find_voice_for_gender_score("Alex", gender_map)
        assert voice  # Should return something

    def test_unknown_character(self):
        voice = find_voice_for_gender_score("Unknown", {})
        assert voice  # Falls back to narrator
