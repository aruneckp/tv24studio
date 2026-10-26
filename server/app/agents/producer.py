"""Producer agent — the 'shift in-charge'. Ranks and selects stories for the bulletin."""

from __future__ import annotations

import time

from .base import Agent, Bulletin

# Topics the channel cares about most (AP politics first).
PRIORITY_KEYWORDS = {
    3.0: ["ఆంధ్ర", "andhra", "అమరావతి", "amaravati", "జనసేన", "janasena", "పవన్", "tdp", "టీడీపీ", "ysrcp", "వైసీపీ"],
    2.0: ["తిరుపతి", "tirupati", "విశాఖ", "vizag", "విజయవాడ", "గుంటూరు", "సీఎం", "ముఖ్యమంత్రి", "మంత్రి", "అసెంబ్లీ"],
    1.0: ["తెలంగాణ", "హైదరాబాద్", "ఎన్నిక", "election", "సినిమా", "tollywood"],
}
BREAKING_WORDS = ["బ్రేకింగ్", "breaking", "అత్యవసర"]


class ProducerAgent(Agent):
    name = "Producer"

    async def run(self, state: Bulletin) -> None:
        now = time.time()
        for s in state.raw:
            text = f"{s.title} {s.summary}".lower()
            score = 0.0
            for weight, words in PRIORITY_KEYWORDS.items():
                if any(w in text for w in words):
                    score += weight
            if s.published_ts:
                age_h = max(0.0, (now - s.published_ts) / 3600)
                score += max(0.0, 3.0 - age_h / 4)  # fresher = higher, fades over ~12h
                if age_h < 1:
                    s.breaking = True
            if any(w in text for w in BREAKING_WORDS):
                s.breaking = True
            if s.source == "TV24 Desk":
                score += 10  # the desk's own stories always make the cut
            if s.breaking:
                score += 2
            s.score = round(score, 2)

        ranked = sorted(state.raw, key=lambda s: s.score, reverse=True)
        state.rundown = ranked[: state.max_stories]
        n_break = sum(1 for s in state.rundown if s.breaking)
        state.note(
            self.name,
            f"Picked top {len(state.rundown)} of {len(state.raw)} stories"
            + (f" — {n_break} flagged BREAKING" if n_break else ""),
        )
