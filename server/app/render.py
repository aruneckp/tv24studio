"""Offline video rendering for the AI Newsroom — fully local, no GPU needed.

The agents write the bulletin, then a local neural Telugu voice (AI4Bharat
FastPitch + HiFi-GAN) reads each segment and a CPU face-warp renderer animates
the studio frame photo's mouth from the voice's own per-character timings. One
command does the whole thing and drops the finished videos straight into the
website.

    python -m app.render build
    git add public/bulletins && git commit -m "Bulletin <id>" && git push

`python -m app.render list` shows published bulletins.

One-time setup (see server/README.md): `brew install ffmpeg-full` (plain
`ffmpeg` lacks the rubberband filter this needs) and the Python/model
download under "Local anchor video".
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config
from .agents.base import Bulletin
from .pipeline import run_pipeline

RENDERS_DIR = config.BASE_DIR / "renders"
SITE_PUBLIC = config.BASE_DIR.parent / "public"
BULLETINS_DIR = SITE_PUBLIC / "bulletins"
DEFAULT_FRAME = SITE_PUBLIC / "anchor-frame.png"
KEEP_PUBLISHED = 10  # older bulletins are dropped from the site
IST = timezone(timedelta(hours=5, minutes=30))
SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+")


def _seg_key(i: int, seg: dict) -> str:
    return f"{i:02d}_{seg['kind']}"


def _fail(msg: str) -> None:
    print(f"\n✗ {msg}\n", file=sys.stderr)
    sys.exit(1)


def _sentences(script: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(script) if s.strip()]


# ---------------------------------------------------------------- build
def build(args: argparse.Namespace) -> None:
    frame = Path(args.frame).expanduser() if args.frame else DEFAULT_FRAME
    if not frame.exists():
        _fail(f"Anchor frame not found: {frame}")

    from .local_anchor import anchor_video
    from .local_anchor.text_te import is_mostly_telugu, telugu_safe
    from .local_anchor.tts_bulletin import _find_ffmpeg, build_segment
    from .local_anchor.tts_te import TeluguVoice

    try:
        ffmpeg = _find_ffmpeg()
    except FileNotFoundError as exc:
        _fail(str(exc))
    try:
        anchor_video.load_landmarks(frame)  # detect + cache once, fail fast if no face found
    except Exception as exc:
        _fail(f"Could not find a face in {frame}: {exc}")

    state = Bulletin(
        voice=args.voice,
        dialect=args.dialect,
        max_stories=args.max_stories,
        use_llm=not args.no_llm,
        make_audio=False,  # voice comes from the local TTS below, not the server's edge-tts
    )
    print("Running the agents (Collector → Producer → Editor → Director)…")
    asyncio.run(run_pipeline(state))
    for e in state.log:
        if e["message"] != "started" and e["agent"] != "Anchor":
            print(f"  [{e['agent']}] {e['message']}")

    if state.mode.get("collector") != "live" and not args.allow_demo:
        _fail("No live news feeds were reachable, so this would be the demo bulletin. Re-run with --allow-demo to render it anyway.")

    data = state.to_dict()
    bid = data["id"]
    work = RENDERS_DIR / bid
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    print(f"Loading the Telugu voice ({args.voice})…")
    voice = TeluguVoice()

    out = BULLETINS_DIR / bid
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    t0 = time.time()
    for i, seg in enumerate(data["rundown"]):
        key = _seg_key(i, seg)
        sentences = _sentences(seg["script"])
        if not sentences:
            seg["video_url"] = None
            seg["audio_url"] = None
            continue
        if not is_mostly_telugu(seg["script"]):
            print(f"  [{i + 1}/{len(data['rundown'])}] {key}: skipped — script is mostly non-Telugu "
                  f"(the voice model can't read it): {seg['headline'][:50]!r}")
            seg["video_url"] = None
            seg["audio_url"] = None
            continue
        print(f"  [{i + 1}/{len(data['rundown'])}] {key}: {seg['headline'][:40]!r}", end="", flush=True)
        sentences = [telugu_safe(s) for s in sentences]
        tl = build_segment(sentences, work / key, voice, speaker=args.voice)
        mp4 = out / f"{key}.mp4"
        dur = anchor_video.render_segment(work / f"{key}.wav", mp4, tl, frame, ffmpeg=ffmpeg)
        seg["video_url"] = f"/bulletins/{bid}/{mp4.name}"
        seg["audio_url"] = None
        print(f"  ({dur:.1f}s)")
    print(f"Rendered {len(data['rundown'])} segments in {time.time() - t0:.1f}s")

    data.pop("render", None)
    data["published_ts"] = time.time()
    (out / "bulletin.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)

    _update_index(bid, data)

    size = sum(f.stat().st_size for f in out.iterdir()) / 1e6
    when = datetime.fromtimestamp(data["created_ts"], IST).strftime("%d %b %Y, %I:%M %p IST")
    print(f"\n✓ Published bulletin {bid} ({when}) → public/bulletins/{bid}  [{size:.1f} MB]")
    print("\nPreview: restart `npm run dev` (it only picks up new files in public/ on start), open /newsroom")
    print("Put it on the website:")
    print(f'  git add ../public/bulletins && git commit -m "Bulletin {bid}" && git push')


def _update_index(bid: str, data: dict) -> None:
    index_path = BULLETINS_DIR / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    index = [b for b in index if b["id"] != bid]
    when = datetime.fromtimestamp(data["created_ts"], IST).strftime("%d %b %Y, %I:%M %p IST")
    stories = [s for s in data["rundown"] if s["kind"] == "story"]
    index.insert(0, {"id": bid, "title": when, "created_ts": data["created_ts"], "stories": len(stories),
                     "headline": stories[0]["headline"] if stories else ""})
    for old in index[KEEP_PUBLISHED:]:
        shutil.rmtree(BULLETINS_DIR / old["id"], ignore_errors=True)
    index = index[:KEEP_PUBLISHED]
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- list
def list_cmd(_: argparse.Namespace) -> None:
    index_path = BULLETINS_DIR / "index.json"
    print("Published on the website (public/bulletins):")
    for b in json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []:
        print(f"  {b['id']}  {b['title']}  {b['stories']} stories — {b['headline']}")
    if not index_path.exists():
        print("  (none)")


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.render", description="Offline anchor-video rendering for the TV24 newsroom")
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("build", help="run the agents, voice and render the anchor videos, publish to the site")
    pb.add_argument("--voice", choices=["male", "female"], default="male")
    pb.add_argument("--dialect", choices=["standard", "coastal", "uttarandhra"], default="standard")
    pb.add_argument("--max-stories", type=int, default=5)
    pb.add_argument("--no-llm", action="store_true", help="use the rule-based editor")
    pb.add_argument("--frame", help="anchor studio frame image (default: public/anchor-frame.png)")
    pb.add_argument("--allow-demo", action="store_true", help="render even if no live feeds were reachable")
    pb.set_defaults(func=build)

    pl = sub.add_parser("list", help="show published bulletins")
    pl.set_defaults(func=list_cmd)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
