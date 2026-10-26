"""Director agent — the 'PCR'. Orders the rundown and packages intro, outro and ticker."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .. import config
from .base import Agent, Bulletin, Story

IST = timezone(timedelta(hours=5, minutes=30))


def greeting(hour: int) -> str:
    if hour < 12:
        return "శుభోదయం"
    if hour < 17:
        return "నమస్కారం"
    return "శుభ సాయంత్రం"


class DirectorAgent(Agent):
    name = "Director"

    async def run(self, state: Bulletin) -> None:
        # Breaking stories open the bulletin; otherwise keep the producer's order.
        stories = sorted(state.rundown, key=lambda s: not s.breaking)
        hour = datetime.now(IST).hour
        heads = " ".join(f"{s.headline}." for s in stories[:3])

        intro = Story(
            title="Intro",
            kind="intro",
            headline=f"{config.CHANNEL_NAME} వార్తలు",
            category="ముఖ్యాంశాలు",
            script=f"{greeting(hour)}. {config.CHANNEL_NAME} వార్తలకు స్వాగతం. ముందుగా ఈ గంట ముఖ్యాంశాలు. {heads}",
        )
        outro = Story(
            title="Outro",
            kind="outro",
            headline="ధన్యవాదాలు",
            category=config.CHANNEL_NAME,
            script=(
                f"ఇవీ ఈ గంట ముఖ్య వార్తలు. మరిన్ని తాజా వార్తల కోసం {config.CHANNEL_NAME} యూట్యూబ్ ఛానల్‌ను "
                "సబ్‌స్క్రైబ్ చేయండి. ధన్యవాదాలు."
            ),
        )
        state.rundown = [intro, *stories, outro]
        state.ticker = [s.ticker for s in stories if s.ticker]
        state.note(self.name, f"Rundown locked: intro + {len(stories)} stories + outro, {len(state.ticker)} ticker lines")
