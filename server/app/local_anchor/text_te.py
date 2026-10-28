"""Makes script text safe for the AI4Bharat Telugu voice model, which only
has Telugu-script characters in its vocabulary — any Latin letter or ASCII
digit is silently dropped by the tokenizer (not an error, just missing
audio), so a stray "TV24" or "77" goes silent or garbled rather than failing
loudly. This fixes the two guaranteed-recurring cases (the channel name, and
numbers in headlines/scripts) and flags scripts that are mostly non-Telugu so
the caller can skip them instead of publishing broken audio.
"""
from __future__ import annotations

import re

ZERO_WIDTH_RE = re.compile(r"[​-‏]")  # ZWSP, ZWNJ, ZWJ, LRM, RLM
TELUGU_RE = re.compile(r"[ఀ-౿]")
LATIN_OR_DIGIT_RE = re.compile(r"[A-Za-z0-9]")

_ONES = ["", "ఒకటి", "రెండు", "మూడు", "నాలుగు", "ఐదు", "ఆరు", "ఏడు", "ఎనిమిది", "తొమ్మిది",
         "పది", "పదకొండు", "పన్నెండు", "పదమూడు", "పద్నాలుగు", "పదిహేను", "పదహారు", "పదిహేడు",
         "పద్దెనిమిది", "పంతొమ్మిది"]
_TENS = ["", "", "ఇరవై", "ముప్పై", "నలభై", "యాభై", "అరవై", "డెబ్బై", "ఎనభై", "తొంభై"]
_DIGIT_NAME = ["సున్నా", "ఒకటి", "రెండు", "మూడు", "నాలుగు", "ఐదు", "ఆరు", "ఏడు", "ఎనిమిది", "తొమ్మిది"]

# Known proper nouns/brand names the TTS would otherwise read character-by-character
# (and silently drop, since they're Latin script). Longest match first.
KNOWN_TERMS = [
    ("TV24", "టీవీ ట్వంటీ ఫోర్"),
    ("TV-24", "టీవీ ట్వంటీ ఫోర్"),
]


def _two_digit_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (" " + _ONES[ones] if ones else "")


def _three_digit_words(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append((_ONES[hundreds] + " " if hundreds > 1 else "") + "వంద")
    if rest:
        parts.append(_two_digit_words(rest))
    return " ".join(parts)


def number_to_telugu_words(n: int) -> str:
    """0..9999 as spoken Telugu words; digit-by-digit outside that range
    (still fully in-vocabulary, just less natural) rather than silently
    dropping the number."""
    if n == 0:
        return _DIGIT_NAME[0]
    if n < 0:
        return "మైనస్ " + number_to_telugu_words(-n)
    if n < 100:
        return _two_digit_words(n)
    if n < 1000:
        return _three_digit_words(n)
    if n < 10000:
        thousands, rest = divmod(n, 1000)
        words = (_ONES[thousands] + " " if thousands > 1 else "") + "వేల"
        if rest:
            words += " " + (_three_digit_words(rest) if rest >= 100 else _two_digit_words(rest))
        return words
    return " ".join(_DIGIT_NAME[int(d)] for d in str(n))


def _replace_number(m: re.Match) -> str:
    return number_to_telugu_words(int(m.group(0)))


def telugu_safe(text: str) -> str:
    """Best-effort: swap known Latin terms and ASCII numbers for Telugu words
    so the voice model doesn't just skip them. Does not handle arbitrary
    English words/names — see `is_mostly_telugu`."""
    for term, repl in KNOWN_TERMS:
        text = text.replace(term, repl)
    text = re.sub(r"\d+", _replace_number, text)
    return ZERO_WIDTH_RE.sub("", text)


def is_mostly_telugu(text: str, min_ratio: float = 0.55) -> bool:
    """True if enough of the text is Telugu script that it's worth
    synthesising. Scraped headlines are sometimes entirely in English (mixed-
    language news feeds); the voice model would render those as near-silence
    rather than failing, so the caller should skip them instead."""
    letters = LATIN_OR_DIGIT_RE.findall(text) + TELUGU_RE.findall(text)
    if not letters:
        return False
    telugu = len(TELUGU_RE.findall(text))
    return telugu / len(letters) >= min_ratio
