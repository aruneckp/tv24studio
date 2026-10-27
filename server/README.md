# TV24 Newsroom — agent server

FastAPI backend for the **AI Newsroom** page (`/newsroom`). Five agents produce
each bulletin, like a TV news shift:

| Agent | Newsroom role | What it does |
|---|---|---|
| **Collector** | Reporter | Pulls stories from RSS feeds (BBC Telugu, Google News AP by default) + stories typed in the News Desk |
| **Producer** | Shift in-charge | Ranks stories (AP politics first, fresh first), picks the top N, flags BREAKING |
| **Editor** | Script writer | Rewrites each story as a 45–90 word Telugu anchor script + headline + ticker line (LLM, or rule-based fallback) |
| **Director** | PCR | Breaking stories first, adds intro (with headlines) and outro, builds the ticker |
| **Anchor** | News reader | Records every segment as MP3 with free Microsoft Telugu neural voices (`te-IN-ShrutiNeural` / `te-IN-MohanNeural`) via `edge-tts` |

Pipeline: `Collector → Producer → Editor → Director → Anchor` (`app/pipeline.py`).
Each agent is a small class with `run(state)`, so it maps 1:1 to LangGraph nodes if
you later want branching, retries or an editor-approval step before air.

## Run

```bash
cd server
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional — edit LLM / feeds / voices
uvicorn app.main:app --reload --port 8000
```

Then in another terminal at the repo root: `npm run dev` and open
http://localhost:5173/newsroom. The page finds the server at
`http://localhost:8000` (change with `VITE_NEWSROOM_API`).

## LLM editor (optional, free options)

Any OpenAI-compatible endpoint works — set in `.env`:

- **Ollama (local, free):** `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=llama3.1` (or a model with good Telugu, e.g. `gemma2`)
- **Gemini (free tier):** `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`, `LLM_MODEL=gemini-2.0-flash`, `LLM_API_KEY=...`
- **Groq (free tier):** `LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_MODEL=llama-3.3-70b-versatile`, `LLM_API_KEY=...`

The prompt forces neutral, fact-only Telugu (no invented names/numbers, no
party bias) and supports Standard / Coastal / Uttarandhra flavour. Without an
LLM the Editor still writes a usable script from the headline + summary.

## Fallbacks (it never goes blank)

- No internet / feeds down → bundled demo stories (about the newsroom itself, never fake real-world news)
- LLM fails on a story → rule-based script for that story
- edge-tts unreachable → the page reads with the browser's Telugu voice, or runs a silent timed preview

## API

- `GET /api/health` — server, LLM and voice info
- `POST /api/bulletin` — `{voice: female|male, dialect: standard|coastal|uttarandhra, max_stories, use_llm, make_audio, manual_stories: [{title, summary, breaking}]}` → rundown + ticker + agent log
- `GET /api/bulletin/latest` — last generated bulletin
- `GET /media/<file>.mp3` — recorded segments (cached by script + voice)

## Offline anchor video (InfiniteTalk on a free Kaggle GPU)

Render the anchor as real talking video ahead of time; the website then just plays it,
with the TV graphics on top. Nothing extra runs on Render.

```bash
cd server && source .venv/bin/activate

# 1. Agents write + voice a bulletin and pack a render job
python -m app.render prepare                 # → server/renders/<id>.zip
#    options: --max-stories 5  --voice male|female  --dialect coastal  --frame my_frame.png

# 2. Kaggle (free): Datasets → New Dataset → upload the zip
#    Open render/infinitetalk_kaggle.ipynb on Kaggle → Add Input (the dataset)
#    Settings: GPU T4 x2, Internet On → Run All → download videos_<id>.zip from Output

# 3. Put the videos into the website
python -m app.render publish ~/Downloads/videos_<id>.zip
git add ../public/bulletins && git commit -m "Bulletin <id>" && git push

python -m app.render list                    # jobs and published bulletins
```

- The anchor frame is `public/anchor-frame.png` (960×540, same layout as the stage). Replace it
  to change the anchor; keep the person on the left so the graphics don't cover the face.
- `/newsroom` loads the newest bulletin from `public/bulletins/index.json` and plays its videos;
  a segment without a video falls back to the photo anchor + voice. The last 10 bulletins are kept.
- Speed on the free T4: roughly 10–25 min per 30 s of speech (fp8 low-memory mode). Try one segment
  first with `ONLY = ["01_story"]` in the notebook.
- Videos are committed to git, which grows the repo over time; for daily use, move them to a free
  object store or YouTube later.

## Deploy on Render

`render.yaml` at the repo root describes both services. To set them up by hand:

1. **Agent server**: Render → New → Web Service → this repo. Root Directory `server`,
   Build `pip install -r requirements.txt`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
   env `CORS_ORIGINS=https://tv24studio.onrender.com` and `PYTHON_VERSION=3.12.7`.
   Note its URL (for example `https://tv24-newsroom-api.onrender.com`).
2. **Website** (the existing `tv24studio` static site): add env `VITE_NEWSROOM_API=<agent server URL>`,
   and under Redirects/Rewrites add `/*` → `/index.html` (Rewrite) so `/newsroom` opens directly.
   Then redeploy.

The free web service sleeps after about 15 minutes idle, so the first bulletin after a pause
takes 30–60 seconds; until it wakes, the page runs the demo bulletin.

## Notes before going on air

- Always review generated scripts — an LLM can still get Telugu names or facts wrong.
- Feed text belongs to the publishers; the Editor rewrites it and the page shows the source link.
- For YouTube live: open `/newsroom`, press **Full screen**, and capture the window in OBS (or add it as an OBS Browser Source). Tick **24×7 loop** to refresh and replay automatically.
