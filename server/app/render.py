"""Offline video rendering for the AI Newsroom.

The anchor video is generated ahead of time on a free GPU (Kaggle) with
InfiniteTalk, then published into the website, which simply plays it. Nothing
here needs to run on Render.

    # 1. On your Mac: agents write + voice a bulletin, and pack a render job
    python -m app.render prepare                 # -> server/renders/<id>.zip

    # 2. On Kaggle (free GPU): run render/infinitetalk_kaggle.ipynb with that
    #    zip attached as a dataset; download videos_<id>.zip when it finishes

    # 3. On your Mac: put the videos into the website
    python -m app.render publish ~/Downloads/videos_<id>.zip
    git add public/bulletins && git commit -m "Bulletin <id>" && git push

`python -m app.render list` shows prepared jobs and published bulletins.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import time
import zipfile
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

# Scene description for InfiniteTalk. It animates the frame; the voice drives the lips.
PROMPT = (
    "A male Telugu television news anchor in a dark navy blazer and light blue shirt sits in a "
    "news studio and reads the news to camera in a calm, professional manner. He looks straight "
    "into the camera, speaks clearly with natural lip movement, small natural head movements and "
    "occasional blinks. The background is a dark red studio backdrop. Steady medium shot, static camera."
)


def _seg_key(i: int, seg: dict) -> str:
    return f"{i:02d}_{seg['kind']}"


def _fail(msg: str) -> None:
    print(f"\n✗ {msg}\n", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- prepare
def prepare(args: argparse.Namespace) -> None:
    frame = Path(args.frame).expanduser() if args.frame else DEFAULT_FRAME
    if not frame.exists():
        _fail(f"Anchor frame not found: {frame}")

    state = Bulletin(
        voice=args.voice,
        dialect=args.dialect,
        max_stories=args.max_stories,
        use_llm=not args.no_llm,
        make_audio=True,
    )
    print("Running the agents (Collector → Producer → Editor → Director → Anchor)…")
    asyncio.run(run_pipeline(state))
    for e in state.log:
        if e["message"] != "started":
            print(f"  [{e['agent']}] {e['message']}")

    missing = [s.headline for s in state.rundown if not s.audio_url]
    if missing:
        _fail(
            "The Anchor agent could not record the voice for every segment "
            f"({len(missing)} missing). The voice service needs internet — check your connection and try again."
        )
    if state.mode.get("collector") != "live" and not args.allow_demo:
        _fail("No live news feeds were reachable, so this would be the demo bulletin. Re-run with --allow-demo to render it anyway.")

    data = state.to_dict()
    job = RENDERS_DIR / data["id"]
    if job.exists():
        shutil.rmtree(job)
    (job / "audio").mkdir(parents=True)
    shutil.copy(frame, job / "frame.png")

    segments = []
    for i, seg in enumerate(data["rundown"]):
        key = _seg_key(i, seg)
        src = config.MEDIA_DIR / Path(seg["audio_url"]).name
        audio_rel = f"audio/{key}.mp3"
        shutil.copy(src, job / audio_rel)
        seg["key"] = key
        segments.append({"key": key, "audio": audio_rel, "headline": seg["headline"]})

    data["render"] = {"engine": "infinitetalk", "prompt": PROMPT, "frame": "frame.png", "segments": segments}
    (job / "bulletin.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    zip_path = RENDERS_DIR / f"{data['id']}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in job.rglob("*"):
            z.write(f, f.relative_to(RENDERS_DIR))

    print(f"\n✓ Render job ready: {zip_path}")
    print(f"  {len(segments)} segments (intro + {len(segments) - 2} stories + outro)\n")
    print("Next:")
    print("  1. kaggle.com → Datasets → New Dataset → upload that zip")
    print("  2. Open render/infinitetalk_kaggle.ipynb on Kaggle, attach the dataset, GPU T4 x2, Run All")
    print(f"  3. Download videos_{data['id']}.zip, then:  python -m app.render publish <path to videos zip>")


# ---------------------------------------------------------------- publish
def publish(args: argparse.Namespace) -> None:
    src = Path(args.videos).expanduser()
    tmp = None
    if src.suffix == ".zip":
        tmp = RENDERS_DIR / f"_unzip_{int(time.time())}"
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp)
        src = tmp
    if not src.is_dir():
        _fail(f"Not a folder or zip: {args.videos}")

    manifests = list(src.rglob("bulletin.json"))
    if not manifests:
        _fail("bulletin.json not found next to the videos. Use the zip the Kaggle notebook produced.")
    vid_dir = manifests[0].parent
    data = json.loads(manifests[0].read_text(encoding="utf-8"))
    bid = data["id"]

    out = BULLETINS_DIR / bid
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    missing = []
    for seg in data["rundown"]:
        mp4 = vid_dir / f"{seg['key']}.mp4"
        if mp4.exists():
            shutil.copy(mp4, out / mp4.name)
            seg["video_url"] = f"/bulletins/{bid}/{mp4.name}"
        else:
            missing.append(seg["key"])
            seg["video_url"] = None
        seg["audio_url"] = None  # the video carries the voice
    data.pop("render", None)
    data["published_ts"] = time.time()
    (out / "bulletin.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # index.json — newest first, keep the last KEEP_PUBLISHED
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

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    size = sum(f.stat().st_size for f in out.iterdir()) / 1e6
    print(f"\n✓ Published bulletin {bid} ({when}) → public/bulletins/{bid}  [{size:.1f} MB]")
    if missing:
        print(f"  ! {len(missing)} segment(s) had no video and will be read with the photo anchor: {', '.join(missing)}")
    print("\nPreview: restart `npm run dev` (it only picks up new files in public/ on start), open /newsroom")
    print("Put it on the website:")
    print(f'  git add ../public/bulletins && git commit -m "Bulletin {bid}" && git push')


# ---------------------------------------------------------------- list
def list_cmd(_: argparse.Namespace) -> None:
    jobs = sorted(RENDERS_DIR.glob("*.zip")) if RENDERS_DIR.exists() else []
    print("Prepared render jobs (server/renders):")
    for z in jobs:
        print(f"  {z.name}  {z.stat().st_size / 1e6:.1f} MB")
    if not jobs:
        print("  (none)")
    index_path = BULLETINS_DIR / "index.json"
    print("\nPublished on the website (public/bulletins):")
    for b in json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []:
        print(f"  {b['id']}  {b['title']}  {b['stories']} stories — {b['headline']}")


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.render", description="Offline anchor-video rendering for the TV24 newsroom")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("prepare", help="run the agents and pack a render job zip")
    pp.add_argument("--voice", choices=["male", "female"], default="male")
    pp.add_argument("--dialect", choices=["standard", "coastal", "uttarandhra"], default="standard")
    pp.add_argument("--max-stories", type=int, default=5)
    pp.add_argument("--no-llm", action="store_true", help="use the rule-based editor")
    pp.add_argument("--frame", help="anchor studio frame image (default: public/anchor-frame.png)")
    pp.add_argument("--allow-demo", action="store_true", help="render even if no live feeds were reachable")
    pp.set_defaults(func=prepare)

    pb = sub.add_parser("publish", help="add rendered videos to the website")
    pb.add_argument("videos", help="videos_<id>.zip from Kaggle (or its unzipped folder)")
    pb.set_defaults(func=publish)

    pl = sub.add_parser("list", help="show prepared jobs and published bulletins")
    pl.set_defaults(func=list_cmd)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
