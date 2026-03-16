from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import json
import inspect
import subprocess
import wave

from .casting import voice_for_speaker
from .config import AppConfig
from .emotion_tts import apply_pace_adjustment, emotion_to_dia_tag, emotion_to_qwen_descriptor, resolve_emotion
from .mlx_registry import resolve_tts_model
from .models import ProductionPackage, Scene
from .sound_effects import (
    write_ambience_bed,
    write_closing_sting,
    write_opening_fanfare,
    write_scene_transition,
)


class Renderer(ABC):
    @abstractmethod
    def render(self, package: ProductionPackage, config: AppConfig) -> Path:
        raise NotImplementedError


class ScriptOnlyRenderer(Renderer):
    def render(self, package: ProductionPackage, config: AppConfig) -> Path:
        output_dir = Path(package.output_dir)
        script_path = output_dir / "script.txt"
        script_path.write_text(render_script_text(package), encoding="utf-8")
        package.manifest_path.write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")
        return script_path


class MacOSSayRenderer(Renderer):
    def render(self, package: ProductionPackage, config: AppConfig) -> Path:
        output_dir = Path(package.output_dir)
        lines_dir = output_dir / "lines"
        wav_dir = output_dir / "wav"
        lines_dir.mkdir(parents=True, exist_ok=True)
        wav_dir.mkdir(parents=True, exist_ok=True)

        audio_segments: list[Path] = []
        script_path = output_dir / "script.txt"
        script_path.write_text(render_script_text(package), encoding="utf-8")

        # Opening fanfare
        if config.audio.music_beds:
            audio_segments.append(
                write_opening_fanfare(wav_dir / "0000_opening_fanfare.wav", config.audio.sample_rate)
            )

        segment_index = 1 if config.audio.music_beds else 0
        for scene_index, scene in enumerate(package.scenes):
            # Ambience bed before each scene
            if config.audio.sound_effects:
                ambience_path = wav_dir / f"{segment_index:04d}_ambience.wav"
                write_ambience_bed(ambience_path, scene.ambience, config.audio.sample_rate)
                audio_segments.append(ambience_path)
                segment_index += 1

            audio_segments.extend(
                self._render_scene(scene, segment_index, package, lines_dir, wav_dir, config)
            )
            segment_index += len(scene.beats) + 2
            should_add_gap = (
                scene_index < len(package.scenes) - 1 or config.audio.include_closing_scene_gap
            )
            if should_add_gap:
                # Music bed transition instead of plain silence
                if config.audio.music_beds:
                    transition_path = wav_dir / f"{segment_index:04d}_transition.wav"
                    write_scene_transition(transition_path, scene_index, config.audio.sample_rate)
                    audio_segments.append(transition_path)
                else:
                    audio_segments.append(
                        _write_silence(
                            wav_dir / f"{segment_index:04d}_scene_gap.wav",
                            config.audio.scene_gap_ms,
                            config.audio.sample_rate,
                        )
                    )
                segment_index += 1

        # Closing sting
        if config.audio.music_beds:
            audio_segments.append(
                write_closing_sting(wav_dir / f"{segment_index:04d}_closing_sting.wav", config.audio.sample_rate)
            )

        final_mix = output_dir / "radio_drama.wav"
        _concat_wavs(audio_segments, final_mix)
        package.manifest_path.write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")
        return final_mix

    def _render_scene(
        self,
        scene: Scene,
        start_index: int,
        package: ProductionPackage,
        lines_dir: Path,
        wav_dir: Path,
        config: AppConfig,
    ) -> list[Path]:
        rendered: list[Path] = []

        intro_aiff = lines_dir / f"{start_index:04d}_intro.aiff"
        intro_wav = wav_dir / f"{start_index:04d}_intro.wav"
        self._speak(package, "Narrator", scene.announcer_intro, intro_aiff)
        _convert_to_wav(intro_aiff, intro_wav, config.audio.sample_rate)
        rendered.append(intro_wav)

        for offset, beat in enumerate(scene.beats, start=1):
            profile = voice_for_speaker(package.cast, beat.speaker)
            aiff_path = lines_dir / f"{start_index + offset:04d}_{beat.speaker.lower()}.aiff"
            wav_path = wav_dir / f"{start_index + offset:04d}_{beat.speaker.lower()}.wav"
            spoken_text = beat.text
            self._speak(package, profile.character, spoken_text, aiff_path, emotion=beat.emotion)
            _convert_to_wav(aiff_path, wav_path, config.audio.sample_rate)
            rendered.append(wav_path)
            gap_path = wav_dir / f"{start_index + offset:04d}_{beat.speaker.lower()}_gap.wav"
            rendered.append(_write_silence(gap_path, config.audio.line_gap_ms, config.audio.sample_rate))
            # SFX cue tone after each beat gap
            if config.audio.sound_effects and beat.cue:
                cue_path = wav_dir / f"{start_index + offset:04d}_{beat.speaker.lower()}_cue.wav"
                from .sound_effects import write_cue_tone
                write_cue_tone(cue_path, beat.cue, config.audio.sample_rate)
                rendered.append(cue_path)

        closing_index = start_index + len(scene.beats) + 1
        closing_aiff = lines_dir / f"{closing_index:04d}_closing.aiff"
        closing_wav = wav_dir / f"{closing_index:04d}_closing.wav"
        self._speak(package, "Narrator", scene.closing, closing_aiff)
        _convert_to_wav(closing_aiff, closing_wav, config.audio.sample_rate)
        rendered.append(closing_wav)
        return rendered

    def _speak(
        self, package: ProductionPackage, speaker: str, text: str, out_path: Path, emotion: str = ""
    ) -> None:
        profile = voice_for_speaker(package.cast, speaker)
        pace = apply_pace_adjustment(profile.pace_wpm, emotion) if emotion else profile.pace_wpm
        subprocess.run(
            [
                "/usr/bin/say",
                "-v",
                profile.voice,
                "-r",
                str(pace),
                "-o",
                str(out_path),
                text,
            ],
            check=True,
        )


class MLXAudioRenderer(Renderer):
    def __init__(self) -> None:
        self._loaded_model = None
        self._loaded_repo = ""

    def render(self, package: ProductionPackage, config: AppConfig) -> Path:
        output_dir = Path(package.output_dir)
        lines_dir = output_dir / "lines"
        wav_dir = output_dir / "wav"
        lines_dir.mkdir(parents=True, exist_ok=True)
        wav_dir.mkdir(parents=True, exist_ok=True)

        script_path = output_dir / "script.txt"
        script_path.write_text(render_script_text(package), encoding="utf-8")

        preset = resolve_tts_model(config.audio.tts_preset)
        target_sample_rate = preset.sample_rate or config.audio.sample_rate
        audio_segments: list[Path] = []
        segment_index = 0

        # Build Dia speaker-slot map: first unique non-Narrator speaker → [S2], rest → [S1]
        speaker_slots = _build_dia_speaker_slots(package)

        # Opening fanfare
        if config.audio.music_beds:
            audio_segments.append(
                write_opening_fanfare(wav_dir / "0000_opening_fanfare.wav", target_sample_rate)
            )
            segment_index = 1

        for scene_index, scene in enumerate(package.scenes):
            # Ambience bed before each scene
            if config.audio.sound_effects:
                ambience_path = wav_dir / f"{segment_index:04d}_ambience.wav"
                write_ambience_bed(ambience_path, scene.ambience, target_sample_rate)
                audio_segments.append(ambience_path)
                segment_index += 1

            audio_segments.extend(
                self._render_scene(scene, segment_index, package, lines_dir, wav_dir, config, preset, target_sample_rate, speaker_slots)
            )
            segment_index += len(scene.beats) + 2
            should_add_gap = (
                scene_index < len(package.scenes) - 1 or config.audio.include_closing_scene_gap
            )
            if should_add_gap:
                if config.audio.music_beds:
                    transition_path = wav_dir / f"{segment_index:04d}_transition.wav"
                    write_scene_transition(transition_path, scene_index, target_sample_rate)
                    audio_segments.append(transition_path)
                else:
                    audio_segments.append(
                        _write_silence(
                            wav_dir / f"{segment_index:04d}_scene_gap.wav",
                            config.audio.scene_gap_ms,
                            target_sample_rate,
                        )
                    )
                segment_index += 1

        # Closing sting
        if config.audio.music_beds:
            audio_segments.append(
                write_closing_sting(wav_dir / f"{segment_index:04d}_closing_sting.wav", target_sample_rate)
            )

        final_mix = output_dir / "radio_drama.wav"
        _concat_wavs(audio_segments, final_mix)
        package.manifest_path.write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")
        return final_mix

    def _render_scene(
        self,
        scene: Scene,
        start_index: int,
        package: ProductionPackage,
        lines_dir: Path,
        wav_dir: Path,
        config: AppConfig,
        preset,
        sample_rate: int,
        speaker_slots: dict[str, str],
    ) -> list[Path]:
        rendered: list[Path] = []
        intro_path = wav_dir / f"{start_index:04d}_intro.wav"
        self._speak_to_wav(package, "Narrator", scene.announcer_intro, intro_path, config, preset, sample_rate, speaker_slots=speaker_slots)
        rendered.append(intro_path)

        for offset, beat in enumerate(scene.beats, start=1):
            wav_path = wav_dir / f"{start_index + offset:04d}_{beat.speaker.lower()}.wav"
            self._speak_to_wav(package, beat.speaker, beat.text, wav_path, config, preset, sample_rate, emotion=beat.emotion, speaker_slots=speaker_slots)
            rendered.append(wav_path)
            gap_path = wav_dir / f"{start_index + offset:04d}_{beat.speaker.lower()}_gap.wav"
            rendered.append(_write_silence(gap_path, config.audio.line_gap_ms, sample_rate))

            # SFX cue tone: insert a brief tonal cue when beat.cue is set
            if config.audio.sound_effects and beat.cue:
                cue_path = wav_dir / f"{start_index + offset:04d}_{beat.speaker.lower()}_cue.wav"
                from .sound_effects import write_cue_tone
                write_cue_tone(cue_path, beat.cue, sample_rate)
                rendered.append(cue_path)

        closing_index = start_index + len(scene.beats) + 1
        closing_path = wav_dir / f"{closing_index:04d}_closing.wav"
        self._speak_to_wav(package, "Narrator", scene.closing, closing_path, config, preset, sample_rate, speaker_slots=speaker_slots)
        rendered.append(closing_path)
        return rendered

    def _speak_to_wav(
        self,
        package: ProductionPackage,
        speaker: str,
        text: str,
        out_path: Path,
        config: AppConfig,
        preset,
        sample_rate: int,
        emotion: str = "",
        speaker_slots: dict[str, str] | None = None,
    ) -> None:
        try:
            from mlx_audio.tts.generate import generate_audio
            from mlx_audio.tts.utils import load_model
        except ImportError as exc:
            raise RuntimeError(
                "The MLX audio renderer requires `mlx-audio`. Install it before using `renderer=mlx_audio`."
            ) from exc

        model_repo = config.audio.tts_model or preset.repo
        if self._loaded_model is None or self._loaded_repo != model_repo:
            self._loaded_model = load_model(model_repo)
            self._loaded_repo = model_repo

        profile = voice_for_speaker(package.cast, speaker)
        slot = (speaker_slots or {}).get(speaker, "[S1]")
        prompt_text = _build_tts_text(preset.family, speaker, text, emotion, slot)
        kwargs = _mlx_audio_kwargs(
            preset_family=preset.family,
            profile=profile,
            config=config,
            preset=preset,
            speaker=speaker,
        )
        result = _call_generate_audio(generate_audio, self._loaded_model, prompt_text, kwargs)
        audio = getattr(result, "audio", result)
        result_rate = getattr(result, "sample_rate", sample_rate)
        _write_audio_like_to_wav(audio, out_path, result_rate or sample_rate)


def build_renderer(config: AppConfig) -> Renderer:
    if config.audio.renderer.lower() == "script":
        return ScriptOnlyRenderer()
    if config.audio.renderer.lower() == "mlx_audio":
        return MLXAudioRenderer()
    return MacOSSayRenderer()


def render_script_text(package: ProductionPackage) -> str:
    lines = [
        package.analysis.title,
        "=" * len(package.analysis.title),
        "",
        f"Setting: {package.analysis.setting}",
        f"Mood: {package.analysis.mood}",
        f"Themes: {', '.join(package.analysis.themes)}",
        "",
    ]

    for scene in package.scenes:
        lines.extend(
            [
                scene.title,
                "-" * len(scene.title),
                f"AMBIENCE: {scene.ambience}",
                f"ANNOUNCER: {scene.announcer_intro}",
                "",
            ]
        )
        for beat in scene.beats:
            cue = f" [{beat.cue}]" if beat.cue else ""
            lines.append(f"{beat.speaker.upper()} ({beat.emotion}){cue}: {beat.text}")
        lines.extend(["", f"CLOSING: {scene.closing}", ""])
    return "\n".join(lines)


def _convert_to_wav(source: Path, target: Path, sample_rate: int) -> None:
    subprocess.run(
        [
            "/usr/bin/afconvert",
            "-f",
            "WAVE",
            "-d",
            "LEI16",
            "-r",
            str(sample_rate),
            str(source),
            str(target),
        ],
        check=True,
    )


def _write_silence(path: Path, duration_ms: int, sample_rate: int) -> Path:
    frames = int(sample_rate * (duration_ms / 1000.0))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frames)
    return path


def _concat_wavs(parts: list[Path], output_path: Path) -> None:
    normalized = [path for path in parts if path.exists()]
    if not normalized:
        raise RuntimeError("No audio segments were rendered.")

    with wave.open(str(normalized[0]), "rb") as first:
        params = first.getparams()

    with wave.open(str(output_path), "wb") as out:
        out.setparams(params)
        for path in normalized:
            with wave.open(str(path), "rb") as wav_file:
                if wav_file.getparams()[:3] != params[:3]:
                    raise RuntimeError(f"WAV format mismatch while concatenating {path}")
                out.writeframes(wav_file.readframes(wav_file.getnframes()))


def _build_tts_text(preset_family: str, speaker: str, text: str, emotion: str, slot: str = "[S1]") -> str:
    if preset_family == "dia":
        dia_cue = emotion_to_dia_tag(emotion) if emotion else "(measured)"
        return f"{slot} {dia_cue} {text}"
    if preset_family == "qwen3-tts":
        descriptor = emotion_to_qwen_descriptor(emotion) if emotion else "steady"
        return f"{speaker}, {descriptor}: {text}"
    return text


def _mlx_audio_kwargs(preset_family: str, profile, config: AppConfig, preset, speaker: str = "") -> dict:
    # Per-character voice override takes precedence over the global tts_voice setting.
    # This allows users to assign distinct voices to each character on MLX TTS backends.
    per_char_voice = config.casting.voice_overrides.get(speaker, "") if speaker else ""
    if preset_family == "kokoro":
        voice = per_char_voice or config.audio.tts_voice or profile.voice or preset.default_voice
        return {
            "voice": voice,
            "lang_code": config.audio.tts_lang_code or preset.default_lang_code,
        }
    if preset_family == "qwen3-tts":
        voice = per_char_voice or config.audio.tts_voice or profile.voice or preset.default_voice
        return {
            "voice": voice,
            "language": config.audio.tts_language or preset.default_language,
        }
    if preset_family == "dia":
        return {}
    return {}


def _build_dia_speaker_slots(package: ProductionPackage) -> dict[str, str]:
    """Map each unique speaker to a Dia slot ([S1] or [S2]).

    Narrator always gets [S1].  The first non-Narrator character that appears
    across all scenes gets [S2], every other speaker also falls back to [S1].
    This lets Dia render two distinct synthetic voices for the main dialogue pair.
    """
    slots: dict[str, str] = {"Narrator": "[S1]"}
    second_slot_assigned = False
    for scene in package.scenes:
        for beat in scene.beats:
            if beat.speaker not in slots:
                if not second_slot_assigned:
                    slots[beat.speaker] = "[S2]"
                    second_slot_assigned = True
                else:
                    slots[beat.speaker] = "[S1]"
    return slots


def _write_audio_like_to_wav(audio, path: Path, sample_rate: int) -> None:
    if hasattr(audio, "tolist"):
        data = audio.tolist()
    else:
        data = audio

    samples = _flatten_audio_samples(data)
    pcm_frames = bytearray()
    for sample in samples:
        clipped = max(-1.0, min(1.0, float(sample)))
        pcm_frames.extend(int(clipped * 32767.0).to_bytes(2, byteorder="little", signed=True))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(pcm_frames))


def _flatten_audio_samples(data) -> list[float]:
    if isinstance(data, (int, float)):
        return [float(data)]
    if not data:
        return [0.0]
    if isinstance(data[0], list):
        flattened: list[float] = []
        for item in data:
            flattened.extend(_flatten_audio_samples(item))
        return flattened
    return [float(value) for value in data]


def _call_generate_audio(generate_audio, model, prompt_text: str, kwargs: dict):
    signature = inspect.signature(generate_audio)
    if "text" in signature.parameters:
        return generate_audio(model, text=prompt_text, **kwargs)
    if "prompt" in signature.parameters:
        return generate_audio(model, prompt=prompt_text, **kwargs)
    return generate_audio(model, prompt_text, **kwargs)
