"""Editor agent — the 'script writer'. Turns raw stories into anchor-ready Telugu scripts.

Uses any OpenAI-compatible LLM (Ollama, Groq, Gemini, OpenAI, Azure…) when
configured, and a rule-based writer otherwise, so it always produces a script.
"""

from __future__ import annotations

import asyncio
import json
import re

import httpx

from .. import config
from .base import Agent, Bulletin, Story
from .collector import strip_publisher

DIALECT_HINT = {
    "standard": "ప్రామాణిక తెలుగు వార్తా భాష (standard Telugu TV news register).",
    "coastal": "కోస్తాంధ్ర యాస, మాటతీరు కొద్దిగా (light Coastal Andhra flavour), but still clear news register.",
    "uttarandhra": "ఉత్తరాంధ్ర యాస కొద్దిగా (light Uttarandhra / North Andhra flavour), but still clear news register.",
}

SYSTEM_PROMPT = """You are the script editor of TV24 Studio, a Telugu TV news channel.
Rewrite the given news item as a script a news anchor reads aloud on air.
Rules:
- Write in Telugu script only. Dialect/register: {dialect}
- Use ONLY facts present in the input. Never invent names, numbers, quotes or events.
- Neutral and factual. No opinions, no praise or attack on any party or person.
- Never read out the feed/source name (e.g. a publisher given in "Source:") — attribute stories to TV24 Studio's own newsroom, not to where the item was picked up from.
- Script: 3 to 5 short spoken sentences, 45-90 words, easy to read aloud. Write numbers as words where natural.
- Headline: max 8 words for the on-screen lower-third.
- Ticker: one short line (max 12 words) for the bottom scroll.
- Category: one Telugu word such as రాజకీయం, ప్రాంతీయం, జాతీయం, అంతర్జాతీయం, సినిమా, క్రీడలు, వాతావరణం, వ్యాపారం, నేరాలు.
Reply with JSON only: {{"headline": "...", "script": "...", "ticker": "...", "category": "...", "breaking": false}}"""

CATEGORY_RULES = [
    ("రాజకీయం", ["పార్టీ", "ఎన్నిక", "సీఎం", "ముఖ్యమంత్రి", "మంత్రి", "ఎమ్మెల్యే", "జనసేన", "టీడీపీ", "వైసీపీ", "బీజేపీ", "కాంగ్రెస్", "election", "minister"]),
    ("సినిమా", ["సినిమా", "హీరో", "టాలీవుడ్", "tollywood", "movie", "film"]),
    ("క్రీడలు", ["క్రికెట్", "మ్యాచ్", "cricket", "match", "ఒలింపిక్"]),
    ("వాతావరణం", ["వర్ష", "తుఫాను", "వాతావరణ", "rain", "cyclone"]),
    ("వ్యాపారం", ["మార్కెట్", "బంగారం", "ధర", "stock", "market"]),
    ("నేరాలు", ["పోలీస్", "అరెస్ట్", "హత్య", "police", "arrest"]),
]
OPENERS = ["", "తాజా సమాచారం ప్రకారం, ", "ఇప్పుడు మరో ముఖ్య వార్త. ", "ఇక ", "మరో వార్త విషయానికొస్తే, "]
SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+")


def guess_category(text: str) -> str:
    low = text.lower()
    for cat, words in CATEGORY_RULES:
        if any(w in low for w in words):
            return cat
    return "వార్తలు"


def shorten(text: str, words: int) -> str:
    parts = text.split()
    return text if len(parts) <= words else " ".join(parts[:words]) + "…"


def rule_based(story: Story, index: int) -> None:
    title = strip_publisher(story.title)
    sentences = [s for s in SENT_SPLIT.split(story.summary) if s.strip()][:3]
    body = " ".join(sentences)
    opener = OPENERS[index % len(OPENERS)]
    script = f"{opener}{title}."
    if body:
        script += f" {body}"
    story.headline = shorten(title, 9)
    story.script = script
    story.ticker = shorten(title, 12)
    story.category = guess_category(f"{title} {body}")


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON in LLM reply")
    return json.loads(match.group(0))


class EditorAgent(Agent):
    name = "Editor"

    def __init__(self, concurrency: int = 3, timeout: float = 45.0):
        self.sem = asyncio.Semaphore(concurrency)
        self.timeout = timeout

    @property
    def llm_ready(self) -> bool:
        return bool(config.LLM_BASE_URL and config.LLM_MODEL)

    async def llm_rewrite(self, client: httpx.AsyncClient, story: Story, dialect: str) -> None:
        user = f"Source: {story.source}\nTitle: {story.title}\nDetails: {story.summary or '(none)'}"
        headers = {"Content-Type": "application/json"}
        if config.LLM_API_KEY:
            headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
        payload = {
            "model": config.LLM_MODEL,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT.format(dialect=DIALECT_HINT.get(dialect, DIALECT_HINT["standard"]))},
                {"role": "user", "content": user},
            ],
        }
        async with self.sem:
            resp = await client.post(f"{config.LLM_BASE_URL}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = _parse_json(resp.json()["choices"][0]["message"]["content"])
        if not data.get("script"):
            raise ValueError("empty script")
        story.headline = data.get("headline") or strip_publisher(story.title)
        story.script = data["script"].strip()
        story.ticker = data.get("ticker") or story.headline
        story.category = data.get("category") or guess_category(story.title)
        story.breaking = story.breaking or bool(data.get("breaking"))

    async def run(self, state: Bulletin) -> None:
        use_llm = state.use_llm and self.llm_ready
        state.mode["editor"] = f"llm:{config.LLM_MODEL}" if use_llm else "rule-based"
        if not use_llm:
            for i, s in enumerate(state.rundown):
                rule_based(s, i)
            why = "LLM turned off" if not state.use_llm else "no LLM configured"
            state.note(self.name, f"Wrote {len(state.rundown)} scripts with the rule-based writer ({why})")
            return

        state.note(self.name, f"Rewriting {len(state.rundown)} stories with {config.LLM_MODEL} ({state.dialect} dialect)")
        async with httpx.AsyncClient(timeout=self.timeout) as client:

            async def one(i: int, s: Story) -> bool:
                try:
                    await self.llm_rewrite(client, s, state.dialect)
                    return True
                except Exception as exc:
                    rule_based(s, i)
                    state.note(self.name, f"LLM failed on story {i + 1} ({type(exc).__name__}) — used rule-based script", "warn")
                    return False

            results = await asyncio.gather(*(one(i, s) for i, s in enumerate(state.rundown)))
        state.note(self.name, f"{sum(results)}/{len(results)} scripts written by the LLM")
