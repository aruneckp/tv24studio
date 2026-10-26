"""TV24 Newsroom — agent-based Telugu news reader API.

Run:  uvicorn app.main:app --reload --port 8000   (from the server/ folder)
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config
from .agents.base import Bulletin
from .pipeline import run_pipeline

app = FastAPI(title="TV24 Newsroom Agents", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=config.MEDIA_DIR), name="media")

_latest: dict | None = None


class ManualStory(BaseModel):
    title: str = Field(..., max_length=300)
    summary: str = Field("", max_length=3000)
    breaking: bool = False


class BulletinRequest(BaseModel):
    voice: str = Field("female", pattern="^(female|male)$")
    dialect: str = Field("standard", pattern="^(standard|coastal|uttarandhra)$")
    max_stories: int = Field(6, ge=1, le=15)
    use_llm: bool = True
    make_audio: bool = True
    manual_stories: list[ManualStory] = []


@app.get("/api/health")
async def health() -> dict:
    return {
        "ok": True,
        "llm": config.LLM_MODEL or None,
        "feeds": len(config.FEEDS),
        "voices": config.VOICES,
    }


@app.post("/api/bulletin")
async def make_bulletin(req: BulletinRequest) -> dict:
    global _latest
    state = Bulletin(
        voice=req.voice,
        dialect=req.dialect,
        max_stories=req.max_stories,
        use_llm=req.use_llm,
        make_audio=req.make_audio,
        manual_stories=[m.model_dump() for m in req.manual_stories],
    )
    await run_pipeline(state)
    _latest = state.to_dict()
    return _latest


@app.get("/api/bulletin/latest")
async def latest_bulletin() -> dict:
    if _latest is None:
        raise HTTPException(404, "No bulletin generated yet")
    return _latest
