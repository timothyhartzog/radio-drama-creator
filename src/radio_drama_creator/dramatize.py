from __future__ import annotations

from abc import ABC, abstractmethod
import json

from .config import AppConfig
from .mlx_registry import resolve_script_model
from .models import DialogueBeat, Scene, StoryAnalysis


class ScriptGenerator(ABC):
    @abstractmethod
    def generate(self, analysis: StoryAnalysis, config: AppConfig) -> list[Scene]:
        raise NotImplementedError


class HeuristicScriptGenerator(ScriptGenerator):
    def generate(self, analysis: StoryAnalysis, config: AppConfig) -> list[Scene]:
        cast = _build_character_cycle(analysis.characters)
        non_narrator = [c for c in cast if c != "Narrator"]
        conflicts = analysis.conflicts or ["A truth strains against silence."]
        scenes: list[Scene] = []

        for scene_index in range(config.style.scenes):
            conflict = conflicts[scene_index % len(conflicts)]
            title = f"Scene {scene_index + 1}: {_scene_focus(conflict)}"
            intro = (
                f"From the velvet hush of the broadcast booth, our story returns to "
                f"{analysis.setting.lower()}, where this {config.style.genre} unfolds: "
                f"{analysis.summary.lower()}"
            )
            beats: list[DialogueBeat] = []

            narrator_target = int(config.style.lines_per_scene * config.style.narration_ratio)
            narrator_count = 0
            dialogue_count = 0
            dialogue_cycle = 0

            for beat_index in range(config.style.lines_per_scene):
                remaining = config.style.lines_per_scene - beat_index
                narrator_needed = narrator_target - narrator_count
                # Force narrator if we must fill the quota, force dialogue if narrator is saturated
                if narrator_needed >= remaining:
                    speaker = "Narrator"
                elif narrator_count >= narrator_target:
                    speaker = non_narrator[dialogue_cycle % len(non_narrator)] if non_narrator else "Narrator"
                    dialogue_cycle += 1
                elif beat_index % max(1, round(1.0 / config.style.narration_ratio)) == 0:
                    speaker = "Narrator"
                else:
                    speaker = non_narrator[dialogue_cycle % len(non_narrator)] if non_narrator else "Narrator"
                    dialogue_cycle += 1

                if speaker == "Narrator":
                    narrator_count += 1
                else:
                    dialogue_count += 1

                emotion = _emotion_for_beat(scene_index, beat_index, analysis.mood)
                cue = _cue_for_beat(scene_index, beat_index)
                line_text = _build_line(
                    speaker=speaker,
                    scene_index=scene_index,
                    beat_index=beat_index,
                    analysis=analysis,
                    conflict=conflict,
                )
                beats.append(DialogueBeat(speaker=speaker, text=line_text, emotion=emotion, cue=cue))

            closing = (
                "The orchestra rises, a warning wrapped in brass and strings, as the moment "
                "breaks and the darkness answers back."
            )
            scenes.append(
                Scene(
                    title=title,
                    announcer_intro=intro,
                    ambience=_ambience_for_scene(scene_index, analysis),
                    beats=beats,
                    closing=closing,
                )
            )

        return scenes


class MLXScriptGenerator(ScriptGenerator):
    def generate(self, analysis: StoryAnalysis, config: AppConfig) -> list[Scene]:
        try:
            from mlx_lm import generate, load
        except ImportError as exc:
            raise RuntimeError(
                "The MLX script backend requires `mlx-lm`. Install with `pip install .[mlx]`."
            ) from exc

        preset = resolve_script_model(config.models.script_preset)
        model_name = config.models.mlx_model or preset.repo
        model, tokenizer = load(model_name)
        prompt = build_mlx_prompt(analysis, config)
        output = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=config.models.max_new_tokens,
            temp=config.models.temperature,
            verbose=False,
        )

        text = getattr(output, "text", output)
        try:
            payload = json.loads(_extract_json_block(text))
        except json.JSONDecodeError:
            return HeuristicScriptGenerator().generate(analysis, config)
        return _scenes_from_payload(payload, analysis, config)


def build_script_generator(config: AppConfig) -> ScriptGenerator:
    if config.models.script_backend.lower() == "mlx":
        return MLXScriptGenerator()
    return HeuristicScriptGenerator()


def build_mlx_prompt(analysis: StoryAnalysis, config: AppConfig) -> str:
        narrator_pct = int(config.style.narration_ratio * 100)
        return f"""
You are an expert radio dramatist creating a script in the style of {config.style.decade_flavor}.
Write {config.style.scenes} scenes with {config.style.lines_per_scene} dialogue beats per scene.
Approximately {narrator_pct}% of beats should be spoken by the Narrator; the rest by named characters.
Use multiple speakers, strong narration, emotional delivery cues, and clean JSON output.
Genre: {config.style.genre}
Tone: {config.style.tone}
Model family: {resolve_script_model(config.models.script_preset).family}

Return JSON with this shape:
{{
  "scenes": [
    {{
      "title": "Scene title",
      "announcer_intro": "Opening narration",
      "ambience": "Sound bed",
      "closing": "Scene closing",
      "beats": [
        {{"speaker": "Name", "text": "Dialogue line", "emotion": "emotion", "cue": "fx cue"}}
      ]
    }}
  ]
}}

Source title: {analysis.title}
Summary: {analysis.summary}
Themes: {", ".join(analysis.themes)}
Setting: {analysis.setting}
Mood: {analysis.mood}
Characters: {", ".join(analysis.characters)}
Conflicts: {", ".join(analysis.conflicts)}
Excerpt: {analysis.source_excerpt}
Keep the writing playable as a 1930s-style radio script with cue-friendly lines and actor-friendly emotions.
""".strip()


def _extract_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    return text[start : end + 1]


def _scenes_from_payload(payload: dict, analysis: StoryAnalysis, config: AppConfig) -> list[Scene]:
    scenes: list[Scene] = []
    for raw_scene in payload.get("scenes", [])[: config.style.scenes]:
        beats = [
            DialogueBeat(
                speaker=beat.get("speaker", "Narrator"),
                text=beat.get("text", "").strip(),
                emotion=beat.get("emotion", "measured"),
                cue=beat.get("cue", ""),
            )
            for beat in raw_scene.get("beats", [])[: config.style.lines_per_scene]
            if beat.get("text")
        ]
        if not beats:
            continue
        scenes.append(
            Scene(
                title=raw_scene.get("title", "Untitled Scene"),
                announcer_intro=raw_scene.get("announcer_intro", analysis.summary),
                ambience=raw_scene.get("ambience", _ambience_for_scene(len(scenes), analysis)),
                beats=beats,
                closing=raw_scene.get("closing", "The music swells and the curtain falls."),
            )
        )
    return scenes or HeuristicScriptGenerator().generate(analysis, config)


def _build_character_cycle(characters: list[str]) -> list[str]:
    filtered = [name for name in characters if name.lower() != "narrator"]
    ensemble = ["Narrator", "Lead", "Confidant", "Rival"]
    for index, name in enumerate(filtered[:3], start=1):
        ensemble[index] = name
    return ensemble


def _scene_focus(conflict: str) -> str:
    words = conflict.split()
    return " ".join(words[:5]).strip(" .,;:!?").title() or "Shadows Gather"


def _emotion_for_beat(scene_index: int, beat_index: int, mood: str) -> str:
    if beat_index == 0:
        return "measured"
    if beat_index % 3 == 0:
        return "urgent"
    if scene_index == 1 and beat_index >= 4:
        return "anxious"
    if "romance" in mood:
        return "tender"
    if scene_index == 2:
        return "haunted"
    return "tense"


def _cue_for_beat(scene_index: int, beat_index: int) -> str:
    if beat_index == 0:
        return "organ swell"
    if beat_index % 2 == 0:
        return "footsteps under dialogue"
    if scene_index == 1 and beat_index > 4:
        return "door latch clicks"
    return "low room tone"


def _ambience_for_scene(scene_index: int, analysis: StoryAnalysis) -> str:
    if scene_index == 0:
        return f"Soft orchestral bed, distant room tone, and the atmosphere of {analysis.setting.lower()}."
    if scene_index == 1:
        return "Closer microphones, tighter silence, and a faint mechanical hum beneath the voices."
    return "Stormy underscore, rising strings, and a final pulse of dread."


def _build_line(
    speaker: str,
    scene_index: int,
    beat_index: int,
    analysis: StoryAnalysis,
    conflict: str,
) -> str:
    theme = analysis.themes[(scene_index + beat_index) % len(analysis.themes)]
    conflict_seed = conflict.lower().rstrip(".")
    if speaker == "Narrator":
        return (
            f"In that suspended hour, {analysis.setting.lower()} seemed to lean inward, "
            f"as if even the walls had begun to listen for {theme}, and for the trouble hidden in {conflict_seed}."
        )

    opener = [
        "Listen to me",
        "There is still time",
        "You heard it too",
        "We cannot keep pretending",
        "The truth has a way of arriving"
    ][(scene_index + beat_index) % 5]
    response = [
        "we are standing too close to the truth",
        "somebody already knows more than they admit",
        "the room has turned against us",
        "silence will not protect anyone tonight",
        "one wrong step will expose everything",
    ][(scene_index * 2 + beat_index) % 5]
    return (
        f"{opener}, because {conflict_seed}, {response}, and every sign points back to {theme}."
    )
