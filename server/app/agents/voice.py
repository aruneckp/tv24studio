"""Voice agent — the 'anchor'. Records each script with a free Telugu neural voice (edge-tts).

If the TTS service can't be reached, ``audio_url`` stays empty and the
newsroom page reads the script with the browser's own speech engine instead.
"""

from __future__ import annotations

import asyncio
import hashlib

from .. import config
from .base import Agent, Bulletin, Story

try:
    import edge_tts
except ImportError:  # pragma: no cover
    edge_tts = None


class VoiceAgent(Agent):
    name = "Anchor"

    def __init__(self, concurrency: int = 3):
        self.sem = asyncio.Semaphore(concurrency)

    async def record(self, story: Story, voice: str) -> None:
        digest = hashlib.sha1(f"{voice}|{config.VOICE_RATE}|{story.script}".encode()).hexdigest()[:16]
        path = config.MEDIA_DIR / f"{digest}.mp3"
        if not path.exists():  # cache: same script + voice is never recorded twice
            async with self.sem:
                tmp = path.with_suffix(".part")
                await edge_tts.Communicate(story.script, voice, rate=config.VOICE_RATE).save(str(tmp))
                tmp.rename(path)
        story.audio_url = f"/media/{path.name}"

    async def run(self, state: Bulletin) -> None:
        if not state.make_audio or edge_tts is None:
            state.mode["voice"] = "browser"
            state.note(self.name, "Server voice off — the page will read with the browser voice")
            return
        voice = config.VOICES.get(state.voice, config.VOICES["female"])
        results = await asyncio.gather(*(self.record(s, voice) for s in state.rundown), return_exceptions=True)
        failed = [r for r in results if isinstance(r, Exception)]
        ok = len(results) - len(failed)
        state.mode["voice"] = f"edge-tts:{voice}" if ok else "browser"
        if failed:
            state.note(self.name, f"Voice service failed for {len(failed)} segment(s) ({type(failed[0]).__name__}) — browser voice will cover them", "warn")
        if ok:
            state.note(self.name, f"Recorded {ok} segment(s) with {voice}")
