"""Collector agent — the 'reporter'. Pulls fresh stories from RSS feeds.

Falls back to bundled sample stories when no feed is reachable, so the studio
always has something to put on air.
"""

from __future__ import annotations

import calendar
import html
import re

import feedparser
import httpx

from .. import config
from ..samples import SAMPLE_STORIES
from .base import Agent, Bulletin, Story

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean(text: str) -> str:
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    return WS_RE.sub(" ", text).strip()


PUBLISHER_SUFFIX_RE = re.compile(r"\s+-\s+[^-]{2,40}$")


def strip_publisher(title: str) -> str:
    # Google News appends " - Publisher" (e.g. "... - ఆంధ్రజ్యోతి"); drop it so
    # it never ends up in a title the editor/anchor reuses verbatim.
    return PUBLISHER_SUFFIX_RE.sub("", title).strip()


def _norm_title(title: str) -> str:
    return strip_publisher(title).lower()


class CollectorAgent(Agent):
    name = "Collector"

    def __init__(self, feeds: list[str] | None = None, timeout: float = 8.0):
        self.feeds = feeds if feeds is not None else config.FEEDS
        self.timeout = timeout

    async def fetch_feed(self, client: httpx.AsyncClient, url: str) -> list[Story]:
        resp = await client.get(url, headers={"User-Agent": "TV24-Newsroom/1.0"})
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        source = clean(parsed.feed.get("title", "")) or url
        stories = []
        for entry in parsed.entries[:25]:
            title = strip_publisher(clean(entry.get("title", "")))
            if not title:
                continue
            ts = 0.0
            if entry.get("published_parsed"):
                ts = float(calendar.timegm(entry.published_parsed))
            summary = clean(entry.get("summary", ""))
            if summary.lower().startswith(title.lower()[:30]):
                summary = ""  # Google News summaries just repeat the title
            stories.append(
                Story(title=title, summary=summary[:800], source=source, link=entry.get("link", ""), published_ts=ts)
            )
        return stories

    async def run(self, state: Bulletin) -> None:
        collected: list[Story] = []

        for m in state.manual_stories:
            if (m.get("title") or "").strip():
                collected.append(
                    Story(
                        title=m["title"].strip(),
                        summary=(m.get("summary") or "").strip(),
                        source=m.get("source") or "TV24 Desk",
                        breaking=bool(m.get("breaking")),
                        published_ts=state.created_ts,
                    )
                )
        if state.manual_stories:
            state.note(self.name, f"Desk added {len(collected)} story(ies) manually")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for url in self.feeds:
                try:
                    items = await self.fetch_feed(client, url)
                    collected.extend(items)
                    state.note(self.name, f"Pulled {len(items)} items from {items[0].source if items else url}")
                except Exception as exc:  # network down, bad feed, etc.
                    state.note(self.name, f"Feed unreachable ({url[:60]}…): {type(exc).__name__}", "warn")

        fed = len(collected) - len(state.manual_stories)
        if fed <= 0:
            collected.extend(Story(**s) for s in SAMPLE_STORIES)
            state.mode["collector"] = "sample"
            state.note(self.name, "No live feeds reachable — using bundled sample stories", "warn")
        else:
            state.mode["collector"] = "live"

        seen: set[str] = set()
        unique = []
        for s in collected:
            key = _norm_title(s.title)[:60]
            if key in seen:
                continue
            seen.add(key)
            unique.append(s)
        state.raw = unique
        state.note(self.name, f"{len(unique)} unique stories after de-duplication")
