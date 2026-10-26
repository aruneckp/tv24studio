"""The newsroom pipeline: Collector → Producer → Editor → Director → Anchor.

Each agent reads and writes the shared ``Bulletin`` state. This is a plain
sequential graph; it maps 1:1 onto LangGraph nodes if you later want
branching, retries or human-in-the-loop approval before air.
"""

from __future__ import annotations

from .agents.base import Agent, Bulletin
from .agents.collector import CollectorAgent
from .agents.director import DirectorAgent
from .agents.editor import EditorAgent
from .agents.producer import ProducerAgent
from .agents.voice import VoiceAgent


def default_agents() -> list[Agent]:
    return [CollectorAgent(), ProducerAgent(), EditorAgent(), DirectorAgent(), VoiceAgent()]


async def run_pipeline(state: Bulletin, agents: list[Agent] | None = None) -> Bulletin:
    for agent in agents or default_agents():
        state.note(agent.name, "started")
        try:
            await agent.run(state)
        except Exception as exc:  # one agent failing should not kill the bulletin
            state.note(agent.name, f"failed: {type(exc).__name__}: {exc}", "error")
    return state
