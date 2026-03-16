# Radio Drama Creator

`radio-drama-creator` turns local documents into a staged, multi-speaker radio drama package on macOS. The first version runs end-to-end on Apple Silicon with:

- local document ingestion for `.txt`, `.md`, `.pdf`, `.rtf`, `.doc`, and `.docx`
- automatic story analysis and golden-age style scene construction
- multi-speaker casting using built-in macOS voices
- rendered output as `script.txt`, `production_manifest.json`, and `radio_drama.wav`
- export artifacts including `cue_sheet.csv`, `episode_outline.md`, and `subtitles.srt`
- an MLX stack built around `Qwen3`, `Qwen2.5-VL`/`Qwen3-VL`, `Dia`, `Qwen3-TTS`, and `Kokoro`
- a simple desktop GUI entrypoint for Mac-friendly runs

## Why this design

This repo is set up so you can produce audio immediately with built-in Apple voices, then progressively improve the creative quality by installing local MLX models for script writing and, later, a separate MLX TTS backend.

Today:

- script generation works with either a heuristic dramatizer or an MLX LLM backend
- voice rendering works with either the built-in macOS `say` command or `mlx-audio`
- the package structure is ready for scanned-document extraction with `mlx-vlm`

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
radio-drama examples/sample_source.txt --output output
```

Desktop app:

```bash
radio-drama-gui
```

Optional PDF support:

```bash
pip install -e '.[pdf]'
```

Optional MLX script-generation support:

```bash
pip install -e '.[mlx]'
```

Run with the included config:

```bash
radio-drama examples/sample_source.txt --config examples/config.json --output output
```

Useful CLI extras:

```bash
radio-drama --list-voices
radio-drama --list-models
radio-drama examples/sample_source.txt --script-only --output output_script
radio-drama examples/sample_source.txt --backend mlx --config examples/config.json --output output_mlx
radio-drama examples/sample_source.txt --backend mlx --script-preset qwen3-14b --renderer mlx_audio --tts-preset dia-1.6b --output output_mlx_full
radio-drama examples/sample_source.txt --genre noir --scenes 4 --lines-per-scene 10 --output output_noir
```

## Output structure

After a run, the output directory contains:

- `script.txt`: the full staged radio play
- `production_manifest.json`: analysis, scenes, and cast metadata
- `radio_drama.wav`: concatenated spoken output
- `cue_sheet.csv`: production cues by scene and beat
- `episode_outline.md`: high-level dramatic plan
- `subtitles.srt`: estimated subtitles/timing file
- `lines/`: per-line AIFF renders from macOS voices
- `wav/`: normalized WAV segments used to build the final mix

Voice overrides live in the `casting` section of the config:

```json
{
  "casting": {
    "voice_overrides": {
      "Narrator": "Tom",
      "Evelyn": "Allison"
    },
    "pace_overrides": {
      "Narrator": 160,
      "Evelyn": 190
    }
  }
}
```

## Using an MLX model for script writing

Update the config:

```json
{
  "models": {
    "script_backend": "mlx",
    "script_preset": "qwen3-8b",
    "mlx_model": "mlx-community/Qwen3-8B-4bit"
  },
  "audio": {
    "renderer": "mlx_audio",
    "tts_preset": "dia-1.6b",
    "tts_model": "mlx-community/Dia-1.6B-fp16"
  }
}
```

Then run:

```bash
radio-drama path/to/document.pdf --config path/to/config.json --output output
```

If MLX generation fails or returns malformed JSON, the app falls back to the heuristic dramatizer so you still get a full production package.

## Recommended MLX presets

- Script: `qwen3-8b` for balanced local generation, `qwen3-14b` for stronger writing on larger Macs
- Vision: `qwen2.5-vl-7b` for scanned PDFs, `qwen3-vl-8b` for harder page layouts
- TTS: `dia-1.6b` for dialogue-first scenes, `qwen3-tts-0.6b` for lighter expressive TTS, `kokoro-82m` for fastest iteration

The app records the resolved stack in `production_manifest.json` under `model_stack` so each output folder keeps a trace of which local MLX models were intended for the run.

## Emotion-aware TTS

The MLX audio renderer maps each dialogue beat's emotion tag (e.g. `tense`, `urgent`, `haunted`, `joyful`) to synthesis parameters — pitch shift, speed, energy, and breathiness — so that the generated speech reflects the dramatic intent of each line. When using the Dia TTS family, emotions are converted to inline cues like `(gasps)`, `(whispering)`, or `(laughs softly)`. For Qwen3-TTS, emotions become natural-language descriptors such as `urgent, fast-paced, intense`. The macOS `say` renderer adjusts speaking pace per emotion.

The full emotion vocabulary is defined in `src/radio_drama_creator/emotion_tts.py` and includes: measured, tense, urgent, anxious, haunted, tender, angry, fearful, sorrowful, joyful, suspicious, commanding, whispering, desperate, and sarcastic.

## Music beds and sound effects

Enable procedural music beds and ambient sound effects at scene transitions:

```bash
radio-drama examples/sample_source.txt --music-beds --sound-effects --output output
```

- `--music-beds` inserts an opening fanfare, minor-key chord transitions between scenes, and a closing dramatic sting
- `--sound-effects` inserts short ambient texture beds before each scene, matched to the scene's ambience description (storms, darkness, bright mornings, etc.)

Both options are also available in the GUI via checkboxes on the Production tab, and in the config JSON under `audio.music_beds` and `audio.sound_effects`.

## GUI features

The desktop GUI (`radio-drama-gui`) provides:

- **Drag-and-drop**: Drop a document file onto the drop zone to load it (requires `tkinterdnd2`; falls back to click-to-browse)
- **Audition buttons**: Click "Play" next to any character in the Cast & Voices tab to hear a test phrase with that voice and pace, or click "Audition line" on the Production tab for a narrator preview
- **Per-character voice overrides**: Set a specific macOS or MLX voice and speaking pace (WPM) for each of the six cast roles
- **Style & Pacing tab**: Tune genre, tone, decade flavor, number of scenes, lines per scene, and narration-to-dialogue ratio with dedicated controls
- **Music beds and sound effects checkboxes**: Toggle procedural audio enhancements directly from the Production tab

## CLI extras

```bash
radio-drama examples/sample_source.txt --genre noir --scenes 4 --lines-per-scene 10 --output output_noir
radio-drama examples/sample_source.txt --tone "dark, brooding, intimate" --narration-ratio 0.4 --output output_custom
radio-drama examples/sample_source.txt --music-beds --sound-effects --output output_full
```
