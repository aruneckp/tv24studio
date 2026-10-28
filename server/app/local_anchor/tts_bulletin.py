"""Builds one segment's newsreader audio — broadcast-processed, with a
per-character timeline for lip sync.

Writes (next to ``out``):
  <out>.wav            broadcast-processed voice (48 kHz mono, -14 LUFS)
  <out>_timeline.json  per-character timings and sentence start times

Needs an ffmpeg build with the "rubberband" filter (Homebrew's plain
``ffmpeg`` formula does not include it — install ``ffmpeg-full`` instead, or
point ``TV24_FFMPEG`` at a build that has it).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from .tts_te import TeluguVoice

# deepen ~2 semitones with formants preserved (anchor tone), rumble cut, gentle
# de-ess, chest warmth, presence, broadcast compression, a very short room so
# it doesn't sound "in a box", YouTube loudness
BROADCAST = ("rubberband=pitch=0.89:formant=preserved:pitchq=quality:transients=smooth:detector=soft,"
             "highpass=f=75,lowpass=f=10500,deesser=i=0.35:m=0.5:f=0.5,"
             "equalizer=f=140:t=q:w=0.9:g=2.5,equalizer=f=320:t=q:w=1.2:g=-1.5,"
             "equalizer=f=3200:t=q:w=1.0:g=2.2,equalizer=f=9000:t=h:w=0.7:g=1.2,"
             "acompressor=threshold=-21dB:ratio=2.6:attack=6:release=90:makeup=2,"
             "aecho=0.85:0.6:18|31:0.07|0.04,"
             "loudnorm=I=-14:TP=-1.2:LRA=9")


def _find_ffmpeg() -> str:
    env = os.environ.get("TV24_FFMPEG")
    if env and Path(env).exists():
        return env
    for candidate in ("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "/usr/local/opt/ffmpeg-full/bin/ffmpeg"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError(
        "No ffmpeg found. Install one with the rubberband filter: `brew install ffmpeg-full`, "
        "or set TV24_FFMPEG to a build that has it."
    )


FFMPEG = None  # resolved lazily so importing this module doesn't require ffmpeg to exist yet


def install_pitch_control(model, var: float = 1.0, shift: float = 0.0) -> None:
    """Scale FastPitch's predicted pitch contour: var>1 = livelier anchor
    intonation, shift>0 = slightly higher (in the model's normalised units)."""
    pp = model.pitch_predictor
    if not hasattr(pp, "_orig_forward"):
        pp._orig_forward = pp.forward

    def fwd(*a, **k):
        p = pp._orig_forward(*a, **k)
        voiced = p.abs() > 1e-3
        if voiced.any():
            mu = p[voiced].mean()
            p = torch.where(voiced, mu + (p - mu) * var + shift, p)
        return p

    pp.forward = fwd


def trim(wav: np.ndarray, sr: int, chars: list, thr_db: float = -42, keep: float = 0.06):
    """Cut leading/trailing silence and shift character timings to match."""
    x = np.abs(wav)
    win = int(0.01 * sr)
    env = np.convolve(x, np.ones(win) / win, "same")
    on = np.where(20 * np.log10(env + 1e-9) > thr_db)[0]
    if len(on) == 0:
        return wav, chars
    a = max(on[0] - int(keep * sr), 0)
    b = min(on[-1] + int(keep * sr), len(wav))
    t0 = a / sr
    out = []
    for ch, s, e in chars:
        s, e = max(s - t0, 0), max(e - t0, 0)
        out.append((ch, min(s, (b - a) / sr), min(e, (b - a) / sr)))
    return wav[a:b], out


def build_segment(
    sentences: list[str],
    out,
    voice: TeluguVoice,
    pace: float = 1.05,
    pitch_var: float = 1.1,
    pitch_shift: float = -0.6,
    speaker: str = "male",
    gap_sentence: float = 0.34,
    lead_in: float = 0.18,
    trailing_pause: float = 0.3,
) -> dict:
    """Synthesise one rundown segment's sentences into one broadcast-processed
    WAV + character timeline. `out` is a path stem; writes `<out>.wav` and
    `<out>_timeline.json`."""
    global FFMPEG
    if FFMPEG is None:
        FFMPEG = _find_ffmpeg()
    install_pitch_control(voice.model, pitch_var, pitch_shift)
    sr = voice.sr
    pieces, chars, sent_marks = [], [], []
    t = lead_in
    pieces.append(np.zeros(int(t * sr), np.float32))
    for k, text in enumerate(sentences):
        wav, _, ch = voice.say(text, speaker=speaker, pace=pace)
        wav, ch = trim(wav, sr, ch)
        sent_marks.append({"start": t, "end": t + len(wav) / sr, "text": text})
        chars += [(c, t + s, t + e) for c, s, e in ch]
        pieces.append(wav)
        t += len(wav) / sr
        gap = gap_sentence if k < len(sentences) - 1 else trailing_pause
        pieces.append(np.zeros(int(gap * sr), np.float32))
        t += gap
    audio = np.concatenate(pieces) if pieces else np.zeros(1, np.float32)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_name(out.name + "_raw.wav")
    sf.write(raw, audio, sr)
    try:
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", str(raw), "-af", BROADCAST,
             "-ar", "48000", "-ac", "1", str(out.with_suffix(".wav"))],
            check=True,
        )
    finally:
        raw.unlink(missing_ok=True)

    tl = {
        "duration": t,
        "sr": 48000,
        "chars": chars,
        "sentences": sent_marks,
        "voice": {"model": "AI4Bharat Indic-TTS FastPitch+HiFiGAN (te)", "speaker": speaker,
                  "pace": pace, "pitch_var": pitch_var, "pitch_shift": pitch_shift},
    }
    out.with_name(out.name + "_timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1))
    return tl
