"""Cuts the anchor out of their source photo and composites them onto a
TV24-branded news-studio backdrop (red/gold on near-black, matching the
site's own --t24-red / --t24-gold), instead of just reusing whatever
background happened to be behind them in the original photo.

Run once whenever the anchor photo changes:

    python -m app.local_anchor.studio public/anchor.png public/anchor-frame.png
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

T24_RED = (31, 28, 238)     # BGR for #ee1c1f
T24_GOLD = (31, 150, 248)   # BGR for #f8961f
OUT_W, OUT_H = 1280, 720


def _grabcut_alpha(img: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Soft person/foreground mask, GrabCut seeded from the face landmarks
    (so it generalises to any portrait, not just this one photo)."""
    h, w = img.shape[:2]
    fw = pts[16, 0] - pts[0, 0]
    m = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    cv2.rectangle(m, (int(pts[0, 0] - 1.6 * fw), 0), (w - 1, h - 1), cv2.GC_PR_FGD, -1)
    cv2.fillConvexPoly(m, cv2.convexHull(pts.astype(np.int32)), cv2.GC_FGD)
    cx = int(pts[27, 0])
    top = int(pts[19:25, 1].min())
    cv2.ellipse(m, (cx, int(top - 0.30 * fw)), (int(0.42 * fw), int(0.33 * fw)), 0, 0, 360, cv2.GC_FGD, -1)
    cv2.rectangle(m, (int(cx - 0.6 * fw), int(pts[8, 1] + 0.25 * fw)), (int(cx + 0.9 * fw), h - 1), cv2.GC_FGD, -1)
    for x0, y0, x1, y1 in [(0, 0, int(cx - 1.0 * fw), int(pts[8, 1] + 0.2 * fw)),
                           (int(cx + 1.1 * fw), 0, w, int(pts[8, 1] - 0.2 * fw))]:
        cv2.rectangle(m, (max(x0, 0), y0), (x1, y1), cv2.GC_BGD, -1)
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, m, None, bgd, fgd, 10, cv2.GC_INIT_WITH_MASK)
    a = np.where((m == 1) | (m == 3), 255, 0).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(a)
    if n > 1:
        a = np.where(lab == 1 + np.argmax(st[1:, 4]), 255, 0).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return cv2.GaussianBlur(a, (0, 0), 1.0)


def _bokeh(img: np.ndarray, spots: list[tuple[float, float, float, float, tuple]]) -> None:
    """Soft out-of-focus light circles, in place. Each spot is
    (x_frac, y_frac, radius_px, opacity, BGR colour)."""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for xf, yf, rad, op, col in spots:
        d = np.hypot(xx - w * xf, yy - h * yf)
        g = np.exp(-(d / rad) ** 2) * op
        img += g[..., None] * np.array(col, np.float32)


def build_background(w: int = OUT_W, h: int = OUT_H, seed: int = 11) -> np.ndarray:
    """TV24-branded studio set: a bright, saturated red-to-deep-red gradient
    (not near-black mud) with soft bokeh light circles and a faint LED
    video-wall grid stage-right — the same red/gold brand as the rest of the
    site, built to read as a lit broadcast set."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = xx / w
    # left (behind the anchor): deep saturated red: right: warmer, towards gold-black
    left = np.array([58, 22, 150], np.float32)   # BGR, deep red
    right = np.array([24, 18, 40], np.float32)   # BGR, near-black with a hint of red
    img = left[None, None, :] * (1 - t[..., None]) + right[None, None, :] * t[..., None]
    img = img * (0.82 + 0.18 * (1 - yy[..., None] / h))  # a touch brighter up top, like set lighting

    rng = np.random.default_rng(seed)
    spots = []
    for _ in range(9):
        spots.append((rng.uniform(0.02, 0.55), rng.uniform(0.05, 0.95), rng.uniform(55, 130),
                      rng.uniform(0.10, 0.22), T24_RED))
    for _ in range(5):
        spots.append((rng.uniform(0.3, 0.9), rng.uniform(0.05, 0.6), rng.uniform(40, 90),
                      rng.uniform(0.10, 0.20), T24_GOLD))
    _bokeh(img, spots)

    # LED video-wall panels, stage-right (clear of the anchor and the lower-third/ticker)
    panel = np.zeros((h, w), np.float32)
    for i in range(12):
        x0 = int(w * 0.50 + i * w * 0.045)
        if x0 > w - 10:
            break
        x1 = min(x0 + int(w * 0.036), w)
        y0, y1 = int(h * 0.05), int(h * 0.68)
        panel[y0:y1, x0:x1] += 0.10 + 0.05 * (i % 3)
    for j in range(8):
        y = int(h * 0.06 + j * h * 0.085)
        panel[max(y - 1, 0):y + 1, int(w * 0.50):] += 0.08
    img += panel[..., None] * np.array([235, 215, 195], np.float32) * 0.30

    glow = np.exp(-(((xx - w * 0.72) / (w * 0.30)) ** 2 + ((yy - h * 0.40) / (h * 0.55)) ** 2))
    img += glow[..., None] * np.array(T24_GOLD, np.float32) * 0.10

    out = cv2.GaussianBlur(np.clip(img, 0, 255).astype(np.uint8), (0, 0), 1.4)
    vig = 1 - 0.30 * np.clip((np.hypot(xx - w * 0.5, yy - h * 0.58) / (w * 0.80)) ** 2, 0, 1)
    out = np.clip(out.astype(np.float32) * vig[..., None], 0, 255).astype(np.uint8)
    return out


def cutout_on_studio(photo_path: str | Path, out_path: str | Path) -> None:
    """Cuts the person out of `photo_path` (ideally a sharp, plainly-lit
    portrait — not one with a heavily blurred background, which GrabCut
    mattes poorly) and composites them onto the branded studio background at
    OUT_W x OUT_H, person framed left like a real news-anchor shot."""
    from . import anchor_video

    photo_path, out_path = Path(photo_path), Path(out_path)
    img = cv2.imread(str(photo_path))
    if img is None:
        raise FileNotFoundError(photo_path)
    pts = anchor_video.prepare_face(photo_path)
    alpha = _grabcut_alpha(img, pts).astype(np.float32) / 255

    # scale the cutout so the face reads at the same size as a real anchor shot,
    # then place it left-of-frame with a little headroom, like a news set
    fw = pts[16, 0] - pts[0, 0]
    target_fw = OUT_W * 0.145
    scale = target_fw / fw
    nh, nw = int(round(img.shape[0] * scale)), int(round(img.shape[1] * scale))
    person = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    amask = cv2.resize(alpha, (nw, nh), interpolation=cv2.INTER_LINEAR)
    pts_s = pts * scale

    bg = build_background(OUT_W, OUT_H)
    # anchor the face horizontally/vertically where a real anchor shot frames it
    face_cx = pts_s[27, 0]
    dst_cx = OUT_W * 0.195
    dst_eye_y = OUT_H * 0.30
    ox = int(round(dst_cx - face_cx))
    oy = int(round(dst_eye_y - pts_s[27, 1]))

    canvas_a = np.zeros((OUT_H, OUT_W), np.float32)
    canvas_p = np.zeros((OUT_H, OUT_W, 3), np.float32)
    # clip the paste region to the canvas
    sx0, sy0 = max(0, -ox), max(0, -oy)
    sx1, sy1 = min(nw, OUT_W - ox), min(nh, OUT_H - oy)
    dx0, dy0 = ox + sx0, oy + sy0
    dx1, dy1 = ox + sx1, oy + sy1
    if dx1 > dx0 and dy1 > dy0:
        canvas_p[dy0:dy1, dx0:dx1] = person[sy0:sy1, sx0:sx1]
        canvas_a[dy0:dy1, dx0:dx1] = amask[sy0:sy1, sx0:sx1]

    # grade the anchor to match the cooler studio light
    g = canvas_p / 255
    g = g * np.array([1.00, 1.00, 1.04], np.float32)
    g = g + 0.04 * (g - 0.5)
    anchor = np.clip(g * 255, 0, 255)

    out = bg.astype(np.float32) * (1 - canvas_a[..., None]) + anchor * canvas_a[..., None]
    cv2.imwrite(str(out_path), np.clip(out, 0, 255).astype(np.uint8))
    # landmarks moved (scaled + repositioned) with the person, so re-detect on the
    # final composite rather than reusing the source photo's coordinates
    anchor_video.prepare_face(out_path)


if __name__ == "__main__":
    import sys

    cutout_on_studio(sys.argv[1], sys.argv[2])
    print(f"wrote {sys.argv[2]}")
