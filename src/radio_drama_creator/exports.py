from __future__ import annotations

from pathlib import Path

from .models import ProductionPackage


def write_additional_exports(package: ProductionPackage) -> None:
    output_dir = Path(package.output_dir)
    (output_dir / "cue_sheet.csv").write_text(build_cue_sheet(package), encoding="utf-8")
    (output_dir / "episode_outline.md").write_text(build_episode_outline(package), encoding="utf-8")
    (output_dir / "subtitles.srt").write_text(build_subtitles(package), encoding="utf-8")


def build_cue_sheet(package: ProductionPackage) -> str:
    rows = ["scene,beat,speaker,emotion,cue,text"]
    for scene_index, scene in enumerate(package.scenes, start=1):
        rows.append(
            f'{scene_index},0,"{package.cast[0].character}","measured","{_csv_escape(scene.ambience)}","{_csv_escape(scene.announcer_intro)}"'
        )
        for beat_index, beat in enumerate(scene.beats, start=1):
            rows.append(
                f'{scene_index},{beat_index},"{_csv_escape(beat.speaker)}","{_csv_escape(beat.emotion)}","{_csv_escape(beat.cue)}","{_csv_escape(beat.text)}"'
            )
    return "\n".join(rows) + "\n"


def build_episode_outline(package: ProductionPackage) -> str:
    lines = [
        f"# {package.analysis.title}",
        "",
        f"Source: `{package.source_path}`",
        "",
        "## Dramatic Summary",
        package.analysis.summary,
        "",
        f"Setting: {package.analysis.setting}",
        f"Mood: {package.analysis.mood}",
        f"Themes: {', '.join(package.analysis.themes)}",
        "",
        "## Cast",
    ]
    for profile in package.cast:
        lines.append(f"- {profile.character}: voice `{profile.voice}`, pace {profile.pace_wpm} wpm")
    lines.extend(["", "## Scene Outline"])
    for index, scene in enumerate(package.scenes, start=1):
        lines.extend(
            [
                f"### Scene {index}: {scene.title}",
                f"- Ambience: {scene.ambience}",
                f"- Intro: {scene.announcer_intro}",
                f"- Closing: {scene.closing}",
                "",
            ]
        )
    return "\n".join(lines)


def build_subtitles(package: ProductionPackage) -> str:
    current_seconds = 0.0
    blocks: list[str] = []
    counter = 1

    for scene in package.scenes:
        current_seconds, counter = _append_block(
            blocks,
            counter,
            current_seconds,
            package.cast[0].pace_wpm,
            f"{package.cast[0].character}: {scene.announcer_intro}",
        )
        current_seconds += 0.2
        for beat in scene.beats:
            profile = next((profile for profile in package.cast if profile.character == beat.speaker), package.cast[0])
            current_seconds, counter = _append_block(
                blocks,
                counter,
                current_seconds,
                profile.pace_wpm,
                f"{beat.speaker}: {beat.text}",
            )
            current_seconds += 0.15
        current_seconds, counter = _append_block(
            blocks,
            counter,
            current_seconds,
            package.cast[0].pace_wpm,
            f"{package.cast[0].character}: {scene.closing}",
        )
        current_seconds += 0.75
    return "\n".join(blocks)


def _append_block(
    blocks: list[str],
    counter: int,
    start_seconds: float,
    pace_wpm: int,
    text: str,
) -> tuple[float, int]:
    words = max(1, len(text.split()))
    duration = max(1.2, words / max(100, pace_wpm) * 60.0)
    end_seconds = start_seconds + duration
    blocks.append(
        "\n".join(
            [
                str(counter),
                f"{_format_srt_time(start_seconds)} --> {_format_srt_time(end_seconds)}",
                text,
                "",
            ]
        )
    )
    return end_seconds, counter + 1


def _format_srt_time(total_seconds: float) -> str:
    millis = int(round(total_seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _csv_escape(text: str) -> str:
    return text.replace('"', "'")
