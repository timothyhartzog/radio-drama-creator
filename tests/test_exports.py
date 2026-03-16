"""Tests for export generation."""

from radio_drama_creator.exports import (
    build_cue_sheet,
    build_episode_outline,
    build_subtitles,
    write_additional_exports,
)


class TestBuildCueSheet:
    def test_csv_output(self, sample_package):
        csv = build_cue_sheet(sample_package)
        assert "scene" in csv.lower()
        assert "speaker" in csv.lower()
        assert "Clarke" in csv

    def test_has_all_beats(self, sample_package):
        csv = build_cue_sheet(sample_package)
        lines = csv.strip().split("\n")
        assert len(lines) >= 3  # header + 2 beats


class TestBuildEpisodeOutline:
    def test_markdown_output(self, sample_package):
        md = build_episode_outline(sample_package)
        assert "# " in md or "## " in md
        assert "Clarke" in md


class TestBuildSubtitles:
    def test_srt_format(self, sample_package):
        srt = build_subtitles(sample_package)
        assert "1\n" in srt
        assert "-->" in srt


class TestWriteAdditionalExports:
    def test_creates_files(self, sample_package):
        write_additional_exports(sample_package)
        from pathlib import Path

        out = Path(sample_package.output_dir)
        assert (out / "cue_sheet.csv").exists()
        assert (out / "episode_outline.md").exists()
        assert (out / "subtitles.srt").exists()
