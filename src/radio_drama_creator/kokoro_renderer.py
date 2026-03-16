"""Kokoro TTS API renderer for audiobook generation.

Ported from audiobook-creator-mlx: generate_audiobook.py
Uses the OpenAI-compatible Kokoro API for text-to-speech.
"""

from __future__ import annotations

import os
import re
import wave
from pathlib import Path
from typing import Generator

from .utils.audio_utils import convert_audio_file_formats, merge_chapters_to_m4b


KOKORO_VOICE_MAP = {
    "male_young": "am_adam",
    "male_middle": "am_michael",
    "male_old": "bm_george",
    "female_young": "af_heart",
    "female_middle": "af_bella",
    "female_old": "bf_emma",
    "narrator": "af_sky",
}


def split_and_annotate_text(text: str) -> list[tuple[str, str]]:
    """Split text into dialogue and narration while annotating each segment.

    Returns list of (segment_text, segment_type) where type is 'dialogue' or 'narration'.
    """
    segments = []
    parts = re.split(r'(\u201c[^\u201d]+\u201d|"[^"]*")', text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if (part.startswith("\u201c") and part.endswith("\u201d")) or (
            part.startswith('"') and part.endswith('"')
        ):
            segments.append((part.strip('"\u201c\u201d'), "dialogue"))
        else:
            segments.append((part, "narration"))
    return segments


def check_if_chapter_heading(text: str) -> bool:
    """Determine if text represents a chapter heading."""
    return bool(re.match(r"^(Chapter|Part|PART|CHAPTER)\s+\d+", text.strip(), re.IGNORECASE))


def find_voice_for_gender_score(
    character: str,
    character_gender_map: dict,
    voice_map: dict | None = None,
) -> str:
    """Identify the appropriate Kokoro voice for a character based on gender score.

    Gender score: 1=very masculine, 10=very feminine, 5=neutral.
    """
    if voice_map is None:
        voice_map = KOKORO_VOICE_MAP

    info = character_gender_map.get(character, {})
    score = info.get("gender_score", 5)
    age = info.get("age", 30)

    if score <= 3:
        if age < 25:
            return voice_map.get("male_young", "am_adam")
        elif age > 55:
            return voice_map.get("male_old", "bm_george")
        return voice_map.get("male_middle", "am_michael")
    elif score >= 7:
        if age < 25:
            return voice_map.get("female_young", "af_heart")
        elif age > 55:
            return voice_map.get("female_old", "bf_emma")
        return voice_map.get("female_middle", "af_bella")

    return voice_map.get("narrator", "af_sky")


def generate_audio_with_single_voice(
    openai_client,
    text: str,
    output_format: str = "wav",
    output_dir: str = "audiobook_output",
    narrator_voice: str = "af_sky",
    dialogue_voice: str = "am_adam",
) -> Generator[str, None, None]:
    """Create an audiobook using one narrator voice and one dialogue voice.

    Processes text chapter-by-chapter and generates audio files.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    chapters = re.split(r"(?=Chapter\s+\d+)", text, flags=re.IGNORECASE)
    chapters = [c.strip() for c in chapters if c.strip()]
    if not chapters:
        chapters = [text]

    chapter_files = []
    for ch_idx, chapter_text in enumerate(chapters):
        yield f"Processing chapter {ch_idx + 1}/{len(chapters)}..."
        segments = split_and_annotate_text(chapter_text)
        chapter_audio_path = str(out / f"chapter_{ch_idx + 1:03d}.m4a")

        audio_parts = []
        for seg_text, seg_type in segments:
            if not seg_text.strip():
                continue
            voice = dialogue_voice if seg_type == "dialogue" else narrator_voice
            try:
                response = openai_client.audio.speech.create(
                    model="kokoro",
                    voice=voice,
                    input=seg_text[:4000],
                    response_format="aac",
                    speed=0.85,
                )
                seg_path = str(out / f"temp_seg_{ch_idx}_{len(audio_parts)}.aac")
                with open(seg_path, "wb") as fh:
                    fh.write(response.read())
                audio_parts.append(seg_path)
            except Exception as exc:
                yield f"  Warning: TTS failed for segment: {exc}"

        if audio_parts:
            _concat_aac_files(audio_parts, chapter_audio_path)
            chapter_files.append(chapter_audio_path)
            for p in audio_parts:
                os.remove(p)

        yield f"Chapter {ch_idx + 1} complete."

    if chapter_files and output_format != "m4a":
        yield f"Converting to {output_format}..."
        for cf in chapter_files:
            convert_audio_file_formats("m4a", output_format, str(out), Path(cf).stem)

    yield f"Audiobook generation complete. {len(chapter_files)} chapters created."


def generate_audio_with_multiple_voices(
    openai_client,
    text: str,
    character_gender_map: dict,
    output_format: str = "wav",
    output_dir: str = "audiobook_output",
    narrator_voice: str = "af_sky",
) -> Generator[str, None, None]:
    """Produce an audiobook with multiple character-specific voices.

    Uses character gender map to assign voices per character.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    lines = text.split("\n")
    chapter_files = []
    current_chapter_segments: list[str] = []
    chapter_idx = 0

    for line in lines:
        if check_if_chapter_heading(line):
            if current_chapter_segments:
                chapter_path = str(out / f"chapter_{chapter_idx + 1:03d}.m4a")
                yield f"Rendering chapter {chapter_idx + 1}..."
                _render_segments_to_file(
                    openai_client, current_chapter_segments, chapter_path,
                    character_gender_map, narrator_voice, out
                )
                chapter_files.append(chapter_path)
                chapter_idx += 1
                current_chapter_segments = []
        else:
            if line.strip():
                current_chapter_segments.append(line.strip())

    if current_chapter_segments:
        chapter_path = str(out / f"chapter_{chapter_idx + 1:03d}.m4a")
        yield f"Rendering final chapter {chapter_idx + 1}..."
        _render_segments_to_file(
            openai_client, current_chapter_segments, chapter_path,
            character_gender_map, narrator_voice, out
        )
        chapter_files.append(chapter_path)

    yield f"Audiobook generation complete. {len(chapter_files)} chapters created."


def _render_segments_to_file(
    openai_client,
    segments: list[str],
    output_path: str,
    character_gender_map: dict,
    narrator_voice: str,
    temp_dir: Path,
) -> None:
    """Render a list of text segments to a single audio file."""
    audio_parts = []
    for idx, seg in enumerate(segments):
        annotated = split_and_annotate_text(seg)
        for text, seg_type in annotated:
            if not text.strip():
                continue
            voice = narrator_voice
            if seg_type == "dialogue" and character_gender_map:
                first_char = next(iter(character_gender_map), None)
                if first_char:
                    voice = find_voice_for_gender_score(first_char, character_gender_map)

            try:
                response = openai_client.audio.speech.create(
                    model="kokoro",
                    voice=voice,
                    input=text[:4000],
                    response_format="aac",
                    speed=0.85,
                )
                seg_path = str(temp_dir / f"temp_{idx}_{len(audio_parts)}.aac")
                with open(seg_path, "wb") as fh:
                    fh.write(response.read())
                audio_parts.append(seg_path)
            except Exception:
                pass

    if audio_parts:
        _concat_aac_files(audio_parts, output_path)
        for p in audio_parts:
            os.remove(p)


def _concat_aac_files(parts: list[str], output: str) -> None:
    """Concatenate AAC files using ffmpeg."""
    import subprocess

    list_file = output + ".list.txt"
    with open(list_file, "w") as fh:
        for p in parts:
            fh.write(f"file '{p}'\n")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output],
            check=True, capture_output=True,
        )
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)
