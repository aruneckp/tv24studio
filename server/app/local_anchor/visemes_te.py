"""
Telugu text-timing -> mouth shapes (visemes) for lip sync.

Telugu script is phonetic, so each letter maps cleanly to a mouth shape. Timings come
from the TTS model's duration predictor (exact, per character). A consonant without a
vowel sign carries the inherent 'a', so its time is split: consonant shape first, then
an open 'a'.

Output per video frame: jaw (open), round (o/u lips), spread (i/e lips), close
(p/b/m lips pressed), tongue (tip up behind the teeth: t/d/n/l), teeth (show teeth).
"""
import numpy as np

# targets: jaw, round, spread, close, tongue, teeth
V = {
    "a":  (0.70, 0.00, 0.15, 0, 0, 0.6),
    "aa": (0.95, 0.00, 0.20, 0, 0, 0.7),
    "i":  (0.30, 0.00, 0.75, 0, 0, 1.0),
    "ii": (0.26, 0.00, 0.90, 0, 0, 1.0),
    "u":  (0.28, 0.85, 0.00, 0, 0, 0.2),
    "uu": (0.26, 0.95, 0.00, 0, 0, 0.1),
    "ru": (0.34, 0.50, 0.00, 0, 0.3, 0.4),
    "e":  (0.50, 0.00, 0.55, 0, 0, 0.9),
    "ee": (0.55, 0.00, 0.65, 0, 0, 0.9),
    "ai": (0.60, 0.00, 0.55, 0, 0, 0.9),
    "o":  (0.55, 0.65, 0.00, 0, 0, 0.4),
    "oo": (0.62, 0.78, 0.00, 0, 0, 0.3),
    "au": (0.66, 0.70, 0.00, 0, 0, 0.4),
    "rest": (0.04, 0.00, 0.00, 0, 0, 0.0),
}
VOWEL_LETTER = {"అ": "a", "ఆ": "aa", "ఇ": "i", "ఈ": "ii", "ఉ": "u", "ఊ": "uu", "ఋ": "ru",
                "ఎ": "e", "ఏ": "ee", "ఐ": "ai", "ఒ": "o", "ఓ": "oo", "ఔ": "au"}
VOWEL_SIGN = {"ా": "aa", "ి": "i", "ీ": "ii", "ు": "u", "ూ": "uu", "ృ": "ru",
              "ె": "e", "ే": "ee", "ై": "ai", "ొ": "o", "ో": "oo", "ౌ": "au"}
VIRAMA, ANUSVARA, VISARGA = "్", "ం", "ః"

C = {}
for ch in "పఫబభమ":
    C[ch] = (0.00, 0.10, 0.00, 1, 0, 0)          # lips pressed
C["వ"] = (0.10, 0.10, 0.10, 0.55, 0, 0.6)          # lower lip to upper teeth
for ch in "తథదధనలరఱ":
    C[ch] = (0.20, 0.00, 0.25, 0, 0.9, 0.8)        # tongue tip behind teeth
for ch in "టఠడఢణళ":
    C[ch] = (0.24, 0.00, 0.20, 0, 0.6, 0.7)        # retroflex
for ch in "సశషచఛజఝఞయ":
    C[ch] = (0.14, 0.00, 0.45, 0, 0.2, 1.0)        # teeth nearly together
for ch in "కఖగఘఙ":
    C[ch] = (0.36, 0.00, 0.10, 0, 0, 0.5)
C["హ"] = (0.50, 0.00, 0.10, 0, 0, 0.5)
BILABIAL = set("పఫబభమ")


def keyframes(chars):
    """chars: [(ch, t0, t1)] -> list of (t_center, target_tuple, weight)."""
    keys = []
    n = len(chars)
    for i, (ch, s, e) in enumerate(chars):
        nxt = chars[i + 1][0] if i + 1 < n else " "
        d = e - s
        if ch in C:
            has_sign = nxt in VOWEL_SIGN or nxt == VIRAMA
            if has_sign:
                keys.append(((s + e) / 2, C[ch], 1.4 if ch in BILABIAL else 1.0))
            else:                                   # inherent 'a'
                cs = s + 0.38 * d
                keys.append(((s + cs) / 2, C[ch], 1.4 if ch in BILABIAL else 1.0))
                keys.append(((cs + e) / 2, V["a"], 1.0))
        elif ch in VOWEL_SIGN:
            keys.append(((s + e) / 2, V[VOWEL_SIGN[ch]], 1.0))
        elif ch in VOWEL_LETTER:
            keys.append(((s + e) / 2, V[VOWEL_LETTER[ch]], 1.0))
        elif ch == ANUSVARA:
            tgt = C["మ"] if nxt in BILABIAL else (0.18, 0.05, 0.05, 0, 0.5, 0.3)
            keys.append(((s + e) / 2, tgt, 1.0))
        elif ch == VISARGA:
            keys.append(((s + e) / 2, (0.4, 0, 0.1, 0, 0, 0.4), 0.8))
        elif ch == VIRAMA:
            continue
        elif ch in ".?!":
            keys.append((s + 0.04, V["rest"], 1.2))
            keys.append((e, V["rest"], 1.2))
        elif ch in ",;:":
            keys.append(((s + e) / 2, V["rest"], 0.8))
        # spaces inside a phrase: no key (coarticulate across the word gap)
    return keys


def tracks(timeline, n_frames, fps=25, lead=0.0, energy=None):
    """Per-frame mouth tracks from a TTS timeline (see tts_bulletin.py)."""
    keys = keyframes(timeline["chars"])
    names = ["jaw", "round", "spread", "close", "tongue", "teeth"]
    sr = 200                                          # internal control rate (5 ms)
    T = n_frames / fps
    t = np.arange(int(T * sr) + 1) / sr
    out = {k: np.zeros_like(t) for k in names}
    if not keys:
        return {k: np.zeros(n_frames) for k in names}
    kt = np.array([k[0] for k in keys]) - lead       # mouth leads the sound slightly
    kv = np.array([k[1] for k in keys], np.float32)
    kw = np.array([k[2] for k in keys], np.float32)
    # coarticulation: each key spreads with a Gaussian dominance function (~45 ms)
    sig = 0.045
    W = np.exp(-0.5 * ((t[:, None] - kt[None, :]) / sig) ** 2) * kw[None, :]
    rest_w = 0.02                                     # far from any key -> rest pose
    num = W @ kv + rest_w * np.array(V["rest"], np.float32)[None, :]
    den = W.sum(1, keepdims=True) + rest_w
    vals = num / den
    for j, k in enumerate(names):
        out[k] = vals[:, j]
    # bilabial closures must actually close: sharper dominance for p/b/m
    cl = np.exp(-0.5 * ((t[:, None] - kt[None, :]) / 0.03) ** 2) * kv[None, :, 3]
    close = np.clip(cl.max(1) if cl.size else 0, 0, 1)
    out["close"] = close
    out["jaw"] = out["jaw"] * (1 - 0.9 * close)
    # resample to video frames (average over each frame's window)
    res = {}
    for k in names:
        x = out[k]
        res[k] = np.array([x[int(i / fps * sr): int((i + 1) / fps * sr) + 1].mean() for i in range(n_frames)])
    if energy is not None:                            # stressed syllables open wider
        e = np.convolve(energy, np.ones(3) / 3, "same")
        res["jaw"] = res["jaw"] * (0.78 + 0.32 * e)
    res["n"] = n_frames
    res["energy"] = energy if energy is not None else np.clip(res["jaw"], 0, 1)
    return res
