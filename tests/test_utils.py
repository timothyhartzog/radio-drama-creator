"""Tests for utility modules."""

import json
from pathlib import Path

from radio_drama_creator.utils.file_utils import (
    empty_file,
    ensure_directory,
    read_json,
    write_json_to_file,
    write_jsons_to_jsonl_file,
)
from radio_drama_creator.utils.shell_utils import (
    check_if_calibre_is_installed,
    check_if_ffmpeg_is_installed,
    check_if_ffprobe_is_installed,
)
from radio_drama_creator.utils.audio_utils import escape_metadata


class TestFileUtils:
    def test_write_and_read_json(self, tmp_path):
        data = {"key": "value", "num": 42}
        path = str(tmp_path / "test.json")
        write_json_to_file(data, path)
        result = read_json(path)
        assert result == data

    def test_empty_file(self, tmp_path):
        path = str(tmp_path / "test.txt")
        Path(path).write_text("some content")
        empty_file(path)
        assert Path(path).read_text() == ""

    def test_write_jsonl(self, tmp_path):
        objects = [{"a": 1}, {"b": 2}]
        path = str(tmp_path / "test.jsonl")
        write_jsons_to_jsonl_file(objects, path)
        lines = Path(path).read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"a": 1}

    def test_ensure_directory(self, tmp_path):
        new_dir = tmp_path / "new" / "nested"
        result = ensure_directory(str(new_dir))
        assert result.exists()
        assert result.is_dir()

    def test_ensure_existing_directory(self, tmp_path):
        result = ensure_directory(str(tmp_path))
        assert result == tmp_path


class TestShellUtils:
    def test_calibre_check_returns_bool(self):
        result = check_if_calibre_is_installed()
        assert isinstance(result, bool)

    def test_ffmpeg_check_returns_bool(self):
        result = check_if_ffmpeg_is_installed()
        assert isinstance(result, bool)

    def test_ffprobe_check_returns_bool(self):
        result = check_if_ffprobe_is_installed()
        assert isinstance(result, bool)


class TestAudioUtils:
    def test_escape_metadata(self):
        assert escape_metadata('He said "hello"') == "He said \\\"hello\\\""

    def test_escape_metadata_no_quotes(self):
        assert escape_metadata("plain text") == "plain text"
