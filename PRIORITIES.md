# Next Priorities

Status assessment as of 2026-03-17 based on the codebase at v0.1.0.

## Priority 1 — Music Beds & Sound Effects

Insert ambient music and sound effects between scene transitions to make
productions feel like authentic golden-age radio dramas.

### What exists today

- `render.py` already writes silence gaps between scenes (`_write_silence`).
- Each `Scene` carries an `ambience` field (e.g. "rain on cobblestones") that is
  written into the script text but **never rendered as audio**.
- Each `Beat` has a `cue` field for inline sound cues that is also text-only.

### Proposed work

1. **SFX asset resolver** — new module `sfx.py` that maps ambience/cue strings
   to local WAV files. Start with a bundled set of royalty-free clips
   (rain, thunder, footsteps, door creak, crowd murmur, etc.) and support a
   user-supplied `sfx/` directory that overrides built-in assets.
2. **Music bed generator** — use MLX audio models or a simple synthesiser to
   generate short transition stingers (3–5 s) keyed to genre/mood. Fall back to
   bundled royalty-free beds when no model is available.
3. **Renderer integration** — extend `MacOSSayRenderer`, `MLXAudioRenderer`, and
   the Kokoro path to mix SFX and music beds into the final WAV:
   - Play the scene's `ambience` clip at reduced volume under dialogue.
   - Insert `cue` one-shots at the correct beat position.
   - Crossfade a transition stinger between scenes instead of dead silence.
4. **Config knobs** — add `audio.sfx_volume`, `audio.music_volume`, and
   `audio.sfx_dir` to `AppConfig` so users can tune or disable effects.
5. **Tests** — unit tests for the resolver and integration tests that verify the
   mixed WAV contains the expected number of segments.

### Why first

This is the single biggest gap in production quality. Emotion-aware TTS is
already in place; adding soundscapes completes the "radio drama" feel without
requiring any UI changes.

---

## Priority 2 — Richer Configuration in the Web UI

Let users control genre, pacing, narrator ratio, and per-character voice
assignments from the web interface instead of hand-editing JSON.

### What exists today

- `web/app.py` accepts `backend` and `renderer` via form fields but does not
  expose most `AppConfig` options (genre, scenes, lines_per_scene, voice
  overrides, TTS preset, etc.).
- The CLI already supports `--genre`, `--scenes`, `--lines-per-scene`,
  `--script-preset`, `--tts-preset`, `--cast-override`.

### Proposed work

1. **Expand the producer form** (`index.html`) with collapsible "Advanced
   Settings" sections:
   - Style: genre dropdown, decade flavour, tone, scene count, lines per scene.
   - Audio: renderer picker, TTS preset, sample rate, gap durations.
   - Cast: dynamic rows for character → voice overrides.
2. **API changes** — pass the new fields through the `/produce` endpoint into
   `AppConfig` construction.
3. **Preset saving** — let users save/load named config presets from the web UI
   (stored as JSON in a `presets/` directory).
4. **Validation** — server-side validation with clear error messages for
   out-of-range values.

### Why second

The web UI is the primary interactive surface. Making it feature-complete
reduces friction for non-CLI users and showcases the full power of the engine.

---

## Priority 3 — GUI Drag-and-Drop & Audition

Modernise the Tkinter desktop GUI with drag-and-drop file input, inline audio
audition, and per-character voice preview.

### What exists today

- `gui.py` is a functional Tkinter app (~250 lines) with file chooser dialogs,
  preset selectors, and a progress log.
- No drag-and-drop support. No audio playback.

### Proposed work

1. **Drag-and-drop** — use `tkinterdnd2` (or the built-in `Tk DnD` on macOS) to
   accept files dropped onto the window.
2. **Audition panel** — after a production completes, show a simple waveform bar
   per scene with play/pause buttons using `simpleaudio` or `pyaudio`.
3. **Voice preview** — in a Cast tab, let users pick a voice for each character
   and click "Preview" to hear a short sample line.
4. **Per-character overrides** — editable table of character → voice mappings
   that feeds into `AppConfig.casting.voice_overrides`.

### Why third

The Tkinter GUI is secondary to the web UI for most users. These improvements
matter, but the web UI serves a broader audience.

---

## Priority 4 — Finish Emotion-Aware TTS Polish

The MLX TTS renderer already passes emotion tags, but there is room for
refinement.

### What exists today

- `MLXAudioRenderer._speak_to_wav` receives `emotion` from each beat and
  passes it to `_build_tts_text`, which wraps it for Dia and Qwen3-TTS.
- Kokoro renderer (`kokoro_renderer.py`) does not use emotions.
- No emotion validation or normalisation — the dramatiser may produce emotions
  that the TTS model doesn't recognise.

### Proposed work

1. **Emotion vocabulary** — define a canonical set of emotions per TTS family
   (e.g. Dia supports "happy", "sad", "angry", "fearful", "measured") and map
   the dramatiser's free-form emotions to the nearest canonical one.
2. **Kokoro emotion support** — investigate Kokoro's expressiveness controls and
   wire them into `kokoro_renderer.py`.
3. **SSML / prosody hints** — for macOS `say`, explore SSML or `[[rate]]` /
   `[[pitch]]` directives to approximate emotional delivery.
4. **A/B evaluation** — add a CLI flag `--compare-emotions` that renders the
   same line with and without emotion hints so users can judge the difference.

### Why fourth

The current emotion pass-through already works acceptably for Dia and Qwen3.
This is a polish pass, not a missing feature.

---

## Priority 5 — CI, Packaging & Distribution

### Proposed work

1. **GitHub Actions CI** — run `pytest` and a lint pass (`ruff`) on every push.
2. **Pre-built wheels** — publish to PyPI so users can `pip install radio-drama-creator`.
3. **Docker image** — for Linux users who want a one-command setup without
   worrying about system dependencies (ffmpeg, calibre, etc.).
4. **Homebrew formula** — for macOS users who prefer `brew install`.

### Why fifth

The project works locally today. Distribution broadens the audience but is lower
urgency than feature completeness.
