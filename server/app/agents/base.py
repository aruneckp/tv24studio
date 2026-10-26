"""Shared types for the newsroom agents.

Every agent receives the shared ``Bulletin`` state, does one job, writes its
results back into the state and records what it did in ``state.log`` so the
newsroom page can show the agents working, like a live gallery/PCR feed.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field


@dataclass
class Story:
    title: str
    summary: str = ""
    source: str = ""
    link: str = ""
    published_ts: float = 0.0  # unix seconds, 0 if unknown
    # filled by Editor agent
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    headline: str = ""
    script: str = ""
    ticker: str = ""
    category: str = "వార్తలు"
    breaking: bool = False
    # filled by Producer / Voice agents
    score: float = 0.0
    audio_url: str | None = None
    kind: str = "story"  # story | intro | outro


@dataclass
class Bulletin:
    voice: str = "female"
    dialect: str = "standard"  # standard | coastal | uttarandhra
    max_stories: int = 6
    use_llm: bool = True
    make_audio: bool = True
    manual_stories: list[dict] = field(default_factory=list)

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_ts: float = field(default_factory=time.time)
    raw: list[Story] = field(default_factory=list)
    rundown: list[Story] = field(default_factory=list)
    ticker: list[str] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)
    mode: dict = field(default_factory=dict)

    def note(self, agent: str, message: str, level: str = "info") -> None:
        self.log.append(
            {"t": round(time.time() - self.created_ts, 2), "agent": agent, "level": level, "message": message}
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_ts": self.created_ts,
            "voice": self.voice,
            "dialect": self.dialect,
            "mode": self.mode,
            "ticker": self.ticker,
            "rundown": [asdict(s) for s in self.rundown],
            "log": self.log,
        }


class Agent:
    name = "agent"

    async def run(self, state: Bulletin) -> None:  # pragma: no cover - interface
        raise NotImplementedError
