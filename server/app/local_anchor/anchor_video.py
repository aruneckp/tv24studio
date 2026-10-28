"""Renders one rundown segment's talking-head video: the studio frame photo
(public/anchor-frame.png) with the mouth warped open/closed in time with the
synthesised voice, plus blinks. No cutout, no drawn studio/lower-third/ticker
— the React stage already draws all of that on top of this video
(`.stage-segvideo { object-fit: cover }`), so this renderer only needs to
produce a believably-talking version of the same frame the site already uses.

One-time per anchor photo:  prepare_face(path) -> saves "<path>.landmarks.npy"

Lip sync comes from the TTS model's own per-character timings (see
tts_bulletin.build_segment), via visemes_te's Telugu letter -> mouth-shape
table — not audio analysis, so it is exact rather than guessed.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

from . import visemes_te


def _sp68_path() -> str:
    """Path of dlib's 68-point model shipped in the face_recognition_models wheel."""
    import importlib.util
    import os

    spec = importlib.util.find_spec("face_recognition_models")
    return os.path.join(os.path.dirname(spec.origin), "models", "shape_predictor_68_face_landmarks.dat")


def _landmarks_path(photo_path: Path) -> Path:
    return photo_path.with_suffix(photo_path.suffix + ".landmarks.npy")


def prepare_face(photo_path: str | Path) -> np.ndarray:
    """One-time: detect the 68 face landmarks on the anchor photo and cache them."""
    import dlib

    photo_path = Path(photo_path)
    img = cv2.imread(str(photo_path))
    if img is None:
        raise FileNotFoundError(photo_path)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = dlib.get_frontal_face_detector()(rgb, 1)
    if not faces:
        raise ValueError(f"No face detected in {photo_path}")
    rect = max(faces, key=lambda r: r.area())
    sp = dlib.shape_predictor(_sp68_path())
    pts = np.array([[p.x, p.y] for p in sp(rgb, rect).parts()], np.float32)
    np.save(_landmarks_path(photo_path), pts)
    return pts


def load_landmarks(photo_path: str | Path) -> np.ndarray:
    photo_path = Path(photo_path)
    lm = _landmarks_path(photo_path)
    if not lm.exists():
        return prepare_face(photo_path)
    return np.load(lm)


def blink_track(n: int, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    b = np.zeros(n)
    i = int(rng.uniform(15, 50))
    prof = [0.45, 1.0, 1.0, 0.6, 0.2]
    while i < n - 5:
        b[i:i + 5] = prof
        i += int(rng.uniform(2.6, 5.0) * 25)
    return b


class Face:
    """Mouth warp + painted interior + blink, applied directly onto a photo
    (no cutout, no background composite — the photo already is the shot)."""

    def __init__(self, img: np.ndarray, pts: np.ndarray):
        self.img = img
        p = self.pts = pts.astype(np.float32)
        self.fw = p[16, 0] - p[0, 0]
        mx0, mx1 = p[48, 0], p[54, 0]
        self.mw = mx1 - mx0
        x0, x1 = int(p[2, 0] - 10), int(p[14, 0] + 10)
        y0, y1 = int(p[29, 1]), int(p[8, 1] + 0.45 * self.fw)
        H, W = img.shape[:2]
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, W), min(y1, H)
        self.box = (x0, y0, x1, y1)
        Hh, Ww = y1 - y0, x1 - x0
        X, Y = np.meshgrid(np.arange(Ww, dtype=np.float32) + x0, np.arange(Hh, dtype=np.float32) + y0)
        self.X, self.Y = X, Y
        upper = p[[60, 61, 62, 63, 64]]
        lower = p[[60, 67, 66, 65, 64]]
        lip_y = (upper[:, 1] + lower[:, 1]) / 2
        self.lip_line = np.interp(X[0], upper[:, 0], lip_y)
        self.cx = p[[48, 54], 0].mean()
        self.cy = lip_y.mean()
        chin_y = p[8, 1]
        jl, jr = p[4, 0], p[12, 0]
        half = max(self.cx - jl, jr - self.cx)
        wx = np.clip(1 - (np.abs(X[0] - self.cx) / half) ** 2, 0, 1) ** 1.2
        self.half_open = 0.37 * self.mw
        prof = np.clip(1 - (np.abs(X[0] - self.cx) / self.half_open) ** 2, 0, 1) ** 0.8
        self.prof_x = X[0]
        self.prof = prof
        Ll = self.lip_line[None, :]
        below = Y - Ll
        soft = np.clip((below + 8) / 30, 0, 1)
        soft = soft * soft * (3 - 2 * soft)
        near = np.clip(1 - below / (0.16 * self.fw), 0, 1)
        fade = np.clip(1 - (Y - chin_y) / (0.28 * self.fw), 0, 1)
        fade = fade * fade * (3 - 2 * fade)
        chin_part = 0.7 * wx[None, :] * soft
        lip_part = prof[None, :] * (below > 0).astype(np.float32) * near * (1 - chin_part)
        self.Wjaw = (chin_part + lip_part) * fade
        up = np.clip(1 - (-below) / 20, 0, 1) * (below <= 0) * prof[None, :]
        self.Wup = up
        self.Wup_press = np.clip(1 - np.abs(below - 4) / 9, 0, 1) * prof[None, :]
        r = np.hypot((X - self.cx) / (self.mw * 1.05), (Y - self.cy) / (self.mw * 0.55))
        self.Wlips = np.clip(1 - r, 0, 1) ** 0.8
        self.eyes = [p[36:42], p[42:48]]

    def mouth(self, jaw, rnd, spr, close=0.0, tongue=0.0, teeth=0.6):
        x0, y0, x1, y1 = self.box
        open_px = jaw * 0.31 * self.mw
        Dy_src = open_px * self.Wjaw - 0.12 * open_px * self.Wup
        Dy_src = Dy_src - close * 1.6 * self.Wup_press
        scale = 1 + spr * 0.06 - rnd * 0.24 - close * 0.03
        sx = (scale - 1) * (self.X - self.cx) * self.Wlips
        Dy = np.zeros_like(Dy_src)
        xi = (self.X - x0).astype(np.int32)
        for _ in range(4):
            yy = np.clip(self.Y - Dy - y0, 0, Dy_src.shape[0] - 1).astype(np.int32)
            Dy = Dy_src[yy, xi]
        mapx = (self.X - sx).astype(np.float32)
        mapy = (self.Y - Dy).astype(np.float32)
        patch = cv2.remap(self.img, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        if open_px > 1.0:
            patch = self._paint_interior(patch, open_px, scale, tongue, teeth, spr, rnd)
        return patch

    def _paint_interior(self, patch, open_px, scale, tongue_up=0.0, teeth_amt=0.6, spr=0.0, rnd=0.0):
        x0, y0, _, _ = self.box
        H, W = patch.shape[:2]
        ho = self.half_open * scale
        xs = np.linspace(self.cx - ho, self.cx + ho, 48)
        prof = np.clip(1 - ((xs - self.cx) / ho) ** 2, 0, 1) ** (0.8 - 0.35 * rnd)
        line = np.interp(xs, self.prof_x, self.lip_line)
        up_y = line - 0.03 * open_px * prof
        lo_y = line + 0.88 * open_px * prof
        poly = np.concatenate([np.stack([xs, up_y], 1), np.stack([xs[::-1], lo_y[::-1]], 1)]) - [x0, y0]
        mask = np.zeros((H * 4, W * 4), np.uint8)
        cv2.fillPoly(mask, [np.round(poly * 4).astype(np.int32)], 255, cv2.LINE_AA)
        mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        mask = cv2.GaussianBlur(mask, (0, 0), 0.6)
        Xc = np.arange(W, dtype=np.float32)[None, :] + x0
        upper_y = np.interp(Xc[0], xs, up_y) - y0
        lower_y = np.interp(Xc[0], xs, lo_y) - y0
        Yr = np.arange(H, dtype=np.float32)[:, None]
        rel = (Yr - upper_y[None, :]) / np.maximum(lower_y - upper_y, 1)[None, :]
        side = np.clip(1 - np.abs(Xc - self.cx) / ho, 0, 1)
        cav = np.empty((H, W, 3), np.float32)
        cav[:] = (22, 24, 52)
        cav *= (0.7 + 0.3 * side[..., None])
        big = min(open_px / (0.18 * self.mw), 1)
        tongue = np.clip((rel - 0.6) * 2.5, 0, 1) * big * side
        tip = np.exp(-((rel - 0.38) / 0.22) ** 2) * np.clip(side * 1.4, 0, 1) * tongue_up
        tongue = np.clip(tongue + tip * 0.9, 0, 1)
        tcol = np.array([92, 100, 178], np.float32) * (0.8 + 0.2 * (1 - rel[..., None]).clip(0, 1))
        cav = cav * (1 - tongue[..., None]) + tcol * tongue[..., None]
        d = Yr - upper_y[None, :]
        teeth_h = min(0.085 * self.mw, (0.45 + 0.25 * teeth_amt) * open_px)
        u = (Xc - self.cx) / self.mw
        widths = np.cumsum([0.105, 0.085, 0.075, 0.07])
        gap = np.exp(-(u[0] ** 2) / 2e-5)
        for wdt in widths:
            gap += np.exp(-((np.abs(u[0]) - wdt) ** 2) / 2e-5)
        tooth_len = teeth_h * (1 - 0.35 * np.clip((np.abs(u) - 0.1) / 0.2, 0, 1))
        teeth = np.clip((tooth_len - d) / 1.2, 0, 1) * (d > -3) * np.clip(side * 1.7, 0, 1)
        tooth_col = np.array([176, 194, 210], np.float32) * (0.62 + 0.38 * side[..., None])
        shade = 0.82 + 0.18 * np.clip(d / max(teeth_h, 1), 0, 1)
        tooth_col = tooth_col * shade[..., None] * (1 - 0.32 * np.clip(gap, 0, 1))[None, :, None]
        cav = cav * (1 - teeth[..., None]) + tooth_col * teeth[..., None]
        dl = lower_y[None, :] - Yr
        low_amt = np.clip(0.7 * (1 - big) + 0.8 * spr * teeth_amt, 0, 1)
        lt = np.clip((0.4 * teeth_h - dl) / 1.3, 0, 1) * (dl > -2) * np.clip(side * 2, 0, 1) * low_amt
        cav = cav * (1 - lt[..., None]) + tooth_col * 0.85 * lt[..., None]
        edge = cv2.GaussianBlur(mask, (0, 0), 2.0)
        cav *= (0.55 + 0.45 * edge[..., None])
        cav = cv2.GaussianBlur(cav, (0, 0), 0.55)
        out = patch.astype(np.float32) * (1 - mask[..., None]) + cav * mask[..., None]
        return np.clip(out, 0, 255).astype(np.uint8)

    def blink(self, frame, c):
        if c <= 0:
            return frame
        for e in self.eyes:
            x0, y0 = int(e[:, 0].min() - 6), int(e[:, 1].min() - 14)
            x1, y1 = int(e[:, 0].max() + 6), int(e[:, 1].max() + 6)
            reg = frame[y0:y1, x0:x1].astype(np.float32)
            H, W = reg.shape[:2]
            eye_h = (e[[4, 5], 1].mean() - e[[1, 2], 1].mean()) + 4
            X, Y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
            m = np.zeros((H, W), np.uint8)
            cv2.fillConvexPoly(m, cv2.convexHull((e - [x0, y0]).astype(np.int32)), 255)
            m = cv2.dilate(m, np.ones((5, 5), np.uint8))
            m = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 1.3)
            shift = c * (eye_h + 2)
            lid = cv2.remap(reg, X, (Y - shift).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            top = e[:, 1].min() - y0
            cover = np.clip((top + shift + 1 - Y) / 2.0, 0, 1) * m
            lash = np.exp(-((Y - (top + shift)) ** 2) / 2.5) * m * c
            out = reg * (1 - cover[..., None]) + lid * cover[..., None]
            out = out * (1 - 0.55 * lash[..., None])
            frame[y0:y1, x0:x1] = np.clip(out, 0, 255).astype(np.uint8)
        return frame


def render_segment(
    wav_path: str | Path,
    out_mp4: str | Path,
    timeline: dict,
    frame_path: str | Path,
    fps: int = 25,
    crf: int = 19,
    ffmpeg: str = "ffmpeg",
) -> float:
    """Renders the talking-head video for one segment. Returns its duration in seconds."""
    frame_path = Path(frame_path)
    img = cv2.imread(str(frame_path))
    if img is None:
        raise FileNotFoundError(frame_path)
    pts = load_landmarks(frame_path)
    face = Face(img, pts)

    info = sf.info(str(wav_path))
    duration = info.frames / info.samplerate
    n = max(1, int(round(duration * fps)))
    tr = visemes_te.tracks(timeline, n, fps)
    bl = blink_track(n)
    # a touch of life on stressed syllables, from the jaw track itself (no audio analysis needed)
    jaw_smooth = np.convolve(tr["jaw"], np.ones(5) / 5, "same")
    brow = np.clip(tr["jaw"] - jaw_smooth, 0, None) * 18

    H, W = img.shape[:2]
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
         "-i", str(wav_path), "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
         "-movflags", "+faststart", str(out_mp4)],
        stdin=subprocess.PIPE,
    )
    x0, y0, x1, y1 = face.box
    for i in range(n):
        frame = img.copy()
        frame[y0:y1, x0:x1] = face.mouth(tr["jaw"][i], tr["round"][i], tr["spread"][i],
                                         tr["close"][i], tr["tongue"][i], tr["teeth"][i])
        frame = face.blink(frame, bl[i])
        if brow[i] > 0.15:
            _lift_brows(face, frame, brow[i])
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode:
        raise RuntimeError(f"ffmpeg exited {proc.returncode} rendering {out_mp4}")
    return n / fps


def _lift_brows(face: Face, frame: np.ndarray, amt: float) -> None:
    p = face.pts
    x0, x1 = int(p[17, 0] - 15), int(p[26, 0] + 15)
    y0, y1 = int(p[17:27, 1].min() - 40), int(p[36:48, 1].min() - 2)
    H, W = frame.shape[:2]
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return
    reg = frame[y0:y1, x0:x1]
    Hh, Ww = reg.shape[:2]
    X, Y = np.meshgrid(np.arange(Ww, dtype=np.float32), np.arange(Hh, dtype=np.float32))
    by = p[17:27, 1].mean() - y0
    wy = np.exp(-((Y - by) / (0.4 * Hh)) ** 2)
    wx = np.clip(1 - np.abs(X - Ww / 2) / (Ww / 2), 0, 1) ** 0.5
    frame[y0:y1, x0:x1] = cv2.remap(reg, X, (Y + amt * wy * wx).astype(np.float32),
                                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
