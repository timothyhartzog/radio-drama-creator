"""Audio processing, format conversion, and M4B audiobook creation via FFmpeg."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .shell_utils import check_if_ffmpeg_is_installed, check_if_ffprobe_is_installed


def escape_metadata(value: str) -> str:
    """Replace double quotes with escaped quotes in metadata values."""
    return value.replace('"', '\\"')


def get_audio_duration_using_ffprobe(file_path: str) -> int:
    """Return the duration of an audio file in milliseconds using ffprobe."""
    if not check_if_ffprobe_is_installed():
        raise RuntimeError("ffprobe is not installed.")
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", file_path,
        ],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(result.stdout)
    duration_sec = float(info["format"]["duration"])
    return int(duration_sec * 1000)


def get_audio_duration_using_raw_ffmpeg(file_path: str) -> int:
    """Return the duration of an audio file in milliseconds using FFmpeg stderr."""
    result = subprocess.run(
        ["ffmpeg", "-i", file_path, "-f", "null", "-"],
        capture_output=True, text=True,
    )
    for line in result.stderr.splitlines():
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            total_ms = int(h) * 3600000 + int(m) * 60000 + int(float(s) * 1000)
            return total_ms
    return 0


def generate_chapters_file(
    chapter_files: list[str], output_file: str = "chapters.txt"
) -> None:
    """Generate an FFmpeg chapter metadata file from a list of audio files."""
    lines = [";FFMETADATA1"]
    current_ms = 0
    for idx, chapter_path in enumerate(chapter_files, start=1):
        try:
            duration_ms = get_audio_duration_using_ffprobe(chapter_path)
        except Exception:
            duration_ms = get_audio_duration_using_raw_ffmpeg(chapter_path)
        end_ms = current_ms + duration_ms
        lines.extend([
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={current_ms}",
            f"END={end_ms}",
            f"title=Chapter {idx}",
        ])
        current_ms = end_ms
    Path(output_file).write_text("\n".join(lines), encoding="utf-8")


def create_m4a_file_from_raw_aac_file(input_path: str, output_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path],
        check=True, capture_output=True,
    )


def create_aac_file_from_m4a_file(input_path: str, output_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "copy", output_path],
        check=True, capture_output=True,
    )


def create_mp3_file_from_m4a_file(input_path: str, output_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", output_path],
        check=True, capture_output=True,
    )


def create_wav_file_from_m4a_file(input_path: str, output_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "pcm_s16le", output_path],
        check=True, capture_output=True,
    )


def create_opus_file_from_m4a_file(input_path: str, output_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "libopus", output_path],
        check=True, capture_output=True,
    )


def create_flac_file_from_m4a_file(input_path: str, output_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "flac", output_path],
        check=True, capture_output=True,
    )


def create_pcm_file_from_m4a_file(input_path: str, output_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-f", "s16le", "-acodec", "pcm_s16le", output_path],
        check=True, capture_output=True,
    )


CONVERTERS = {
    "mp3": create_mp3_file_from_m4a_file,
    "wav": create_wav_file_from_m4a_file,
    "opus": create_opus_file_from_m4a_file,
    "flac": create_flac_file_from_m4a_file,
    "pcm": create_pcm_file_from_m4a_file,
    "aac": create_aac_file_from_m4a_file,
    "m4a": create_m4a_file_from_raw_aac_file,
}


def convert_audio_file_formats(
    input_format: str, output_format: str, folder_path: str, file_name: str
) -> None:
    """Convert an audio file from one format to another."""
    input_path = os.path.join(folder_path, f"{file_name}.{input_format}")
    output_path = os.path.join(folder_path, f"{file_name}.{output_format}")
    converter = CONVERTERS.get(output_format)
    if converter is None:
        raise ValueError(f"Unsupported output format: {output_format}")
    converter(input_path, output_path)


def merge_chapters_to_m4b(book_path: str, chapter_files: list[str]) -> None:
    """Merge chapter audio files into a single M4B audiobook with metadata."""
    if not check_if_ffmpeg_is_installed():
        raise RuntimeError("ffmpeg is required to create M4B files.")

    chapters_meta = "chapters.txt"
    generate_chapters_file(chapter_files, chapters_meta)

    file_list = "concat_list.txt"
    with open(file_list, "w") as fh:
        for cf in chapter_files:
            fh.write(f"file '{cf}'\n")

    cover_path = os.path.join(os.path.dirname(book_path), "cover.jpg")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", file_list,
        "-i", chapters_meta,
    ]
    if os.path.exists(cover_path):
        cmd.extend(["-i", cover_path, "-map", "0:a", "-map", "2:v", "-disposition:v:0", "attached_pic"])
    else:
        cmd.extend(["-map", "0:a"])

    cmd.extend([
        "-map_metadata", "1",
        "-c:a", "aac", "-b:a", "64k",
        "-movflags", "+faststart",
        os.path.join(os.path.dirname(book_path), "audiobook.m4b"),
    ])
    subprocess.run(cmd, check=True, capture_output=True)

    for temp_file in [file_list, chapters_meta]:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def merge_chapters_to_standard_audio_file(chapter_files: list[str]) -> None:
    """Merge chapter audio files into a single M4A file."""
    if not check_if_ffmpeg_is_installed():
        raise RuntimeError("ffmpeg is required.")

    file_list = "concat_list.txt"
    with open(file_list, "w") as fh:
        for cf in chapter_files:
            fh.write(f"file '{cf}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", file_list, "-c", "copy", "audiobook.m4a"],
        check=True, capture_output=True,
    )
    if os.path.exists(file_list):
        os.remove(file_list)


def add_silence_to_audio_file(
    temp_dir: str, input_file_name: str, pause_duration: str = "00:00:02"
) -> None:
    """Add silence at the end of an audio file using ffmpeg re-encoding."""
    input_path = os.path.join(temp_dir, input_file_name)
    output_path = os.path.join(temp_dir, f"padded_{input_file_name}")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-af", f"apad=pad_dur={pause_duration}",
            output_path,
        ],
        check=True, capture_output=True,
    )
    os.replace(output_path, input_path)
