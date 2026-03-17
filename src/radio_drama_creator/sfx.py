"""Sound effects and music bed resolver for scene transitions and inline cues."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


SFX_CATALOG: dict[str, str] = {
    "rain": "rain.wav",
    "thunder": "thunder.wav",
    "footsteps": "footsteps.wav",
    "door": "door.wav",
    "organ": "organ.wav",
    "crowd": "crowd.wav",
    "wind": "wind.wav",
    "orchestral": "orchestral.wav",
    "strings": "strings.wav",
    "clock": "clock.wav",
}

_BUNDLED_SFX_DIR = Path(__file__).parent / "sfx"


def resolve_sfx_asset(cue_text: str, sfx_dir: Path | None = None) -> Path | None:
    """Return the path to a WAV asset matching *cue_text*, or ``None``.

    Checks a user-supplied *sfx_dir* first, then the bundled ``sfx/``
    directory shipped with the package.
    """
    lowered = cue_text.lower()
    for keyword, filename in SFX_CATALOG.items():
        if keyword in lowered:
            if sfx_dir is not None:
                candidate = sfx_dir / filename
                if candidate.exists():
                    return candidate
            bundled = _BUNDLED_SFX_DIR / filename
            if bundled.exists():
                return bundled
    return None


def generate_silence_bed(duration_ms: int, sample_rate: int) -> bytes:
    """Return PCM silence (16-bit signed LE mono) for *duration_ms*."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    return b"\x00\x00" * num_samples


def generate_tone_bed(
    duration_ms: int,
    sample_rate: int,
    frequency: float = 220.0,
    volume: float = 0.05,
) -> bytes:
    """Return a low ambient sine-wave drone as PCM (16-bit signed LE mono)."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    buf = bytearray(num_samples * 2)
    two_pi_f = 2.0 * math.pi * frequency
    for i in range(num_samples):
        sample = volume * math.sin(two_pi_f * i / sample_rate)
        clamped = max(-1.0, min(1.0, sample))
        struct.pack_into("<h", buf, i * 2, int(clamped * 32767))
    return bytes(buf)


def mix_audio_bytes(base: bytes, overlay: bytes, overlay_volume: float = 0.3) -> bytes:
    """Mix two PCM byte streams (16-bit signed LE mono).

    The *overlay* is scaled by *overlay_volume* and added to *base*.
    The output length equals the length of *base*; the overlay is
    zero-padded or truncated as needed.
    """
    num_samples = len(base) // 2
    out = bytearray(num_samples * 2)
    overlay_samples = len(overlay) // 2
    for i in range(num_samples):
        b_val = struct.unpack_from("<h", base, i * 2)[0]
        if i < overlay_samples:
            o_val = struct.unpack_from("<h", overlay, i * 2)[0]
        else:
            o_val = 0
        mixed = b_val + int(o_val * overlay_volume)
        mixed = max(-32768, min(32767, mixed))
        struct.pack_into("<h", out, i * 2, mixed)
    return bytes(out)


def build_scene_transition(
    ambience: str,
    duration_ms: int,
    sample_rate: int,
    sfx_dir: Path | None = None,
) -> bytes:
    """Build a transition sound for a scene break.

    If a matching SFX asset is found for *ambience*, its PCM data is
    returned (truncated or padded to *duration_ms*).  Otherwise a
    generated tone bed is returned.
    """
    asset_path = resolve_sfx_asset(ambience, sfx_dir)
    if asset_path is not None:
        return _load_wav_pcm(asset_path, duration_ms, sample_rate)
    return generate_tone_bed(duration_ms, sample_rate)


def build_cue_sound(
    cue: str,
    duration_ms: int,
    sample_rate: int,
    sfx_dir: Path | None = None,
) -> bytes | None:
    """Return a short sound effect for an inline *cue*, or ``None``."""
    asset_path = resolve_sfx_asset(cue, sfx_dir)
    if asset_path is not None:
        return _load_wav_pcm(asset_path, duration_ms, sample_rate)
    return None


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _load_wav_pcm(path: Path, duration_ms: int, sample_rate: int) -> bytes:
    """Read raw PCM frames from a WAV file, padded/truncated to *duration_ms*."""
    target_samples = int(sample_rate * (duration_ms / 1000.0))
    with wave.open(str(path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    # Pad or truncate to target length
    target_bytes = target_samples * 2
    if len(raw) >= target_bytes:
        return raw[:target_bytes]
    return raw + b"\x00" * (target_bytes - len(raw))
