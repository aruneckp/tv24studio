// Settings + offline demo data for the AI Newsroom page.
//
// The page talks to the FastAPI agent server in /server. If that server is
// not running, it builds this demo bulletin in the browser so the studio
// still works (and reads with the browser's own speech voice).

export const NEWSROOM_API = (import.meta.env.VITE_NEWSROOM_API || 'http://localhost:8000').replace(/\/$/, '')

// Put your base anchor video at public/anchor.mp4 (or set VITE_ANCHOR_VIDEO).
export const ANCHOR_VIDEO = import.meta.env.VITE_ANCHOR_VIDEO || '/anchor.mp4'

// Used when there is no anchor video: a cut-out photo of the news reader
// (transparent PNG) at public/anchor.png, or set VITE_ANCHOR_IMAGE.
export const ANCHOR_IMAGE = import.meta.env.VITE_ANCHOR_IMAGE || '/anchor.png'

export const DIALECTS = [
  { value: 'standard', label: 'Standard Telugu' },
  { value: 'coastal', label: 'Coastal Andhra' },
  { value: 'uttarandhra', label: 'Uttarandhra' },
]

const CHANNEL = 'TV24 స్టూడియో'

// Same demo stories as server/app/samples.py — about the newsroom itself,
// never real-world events, so a demo can't be mistaken for real news.
const DEMO_STORIES = [
  {
    headline: 'TV24 స్టూడియోలో AI న్యూస్ రీడర్',
    category: 'ప్రత్యేకం',
    script:
      'TV24 స్టూడియో కొత్త ఏజెంట్ ఆధారిత న్యూస్ రీడర్‌ను పరీక్షిస్తోంది. ఇది వార్తా ఫీడ్ల నుంచి తాజా వార్తలను సేకరించి, యాంకర్ శైలిలో స్క్రిప్ట్ రాసి, తెలుగు గొంతుతో చదువుతుంది.',
    ticker: 'TV24 స్టూడియోలో AI న్యూస్ రీడర్ ప్రారంభం',
  },
  {
    headline: 'ఇది డెమో బులెటిన్ మాత్రమే',
    category: 'డెమో',
    script:
      'ఇప్పుడు మీరు చూస్తున్నది డెమో బులెటిన్. న్యూస్‌రూమ్ సర్వర్ ప్రారంభించినప్పుడు, ఇక్కడ ప్రత్యక్ష వార్తా ఫీడ్ల నుంచి నిజమైన తాజా వార్తలు వస్తాయి.',
    ticker: 'సర్వర్ ప్రారంభిస్తే ప్రత్యక్ష వార్తలు',
  },
  {
    headline: 'మీ వార్తలను మీరే జోడించండి',
    category: 'డెస్క్',
    script:
      'డెస్క్ ప్యానెల్‌లో శీర్షిక, వివరాలు టైప్ చేయండి. ఎడిటర్ ఏజెంట్ దాన్ని యాంకర్ స్క్రిప్ట్‌గా మార్చి, బులెటిన్‌లో చేరుస్తుంది.',
    ticker: 'డెస్క్ నుంచి మీ వార్తలు నేరుగా బులెటిన్‌లోకి',
  },
  {
    headline: 'మీ సొంత యాంకర్ వీడియో',
    category: 'స్టూడియో',
    script:
      'పబ్లిక్ ఫోల్డర్‌లో anchor.mp4 పేరుతో బేస్ వీడియోను ఉంచండి. వార్త చదువుతున్నంత సేపు అదే వీడియో తెరపై ప్లే అవుతుంది.',
    ticker: 'anchor.mp4 తో మీ యాంకర్ తెరపై',
  },
]

let n = 0
const uid = () => `demo-${Date.now().toString(36)}-${n++}`

const greeting = () => {
  const h = new Date().getHours()
  if (h < 12) return 'శుభోదయం'
  if (h < 17) return 'నమస్కారం'
  return 'శుభ సాయంత్రం'
}

export function buildDemoBulletin({ maxStories = 6, manualStories = [] } = {}) {
  const desk = manualStories
    .filter((m) => m.title.trim())
    .map((m) => ({
      headline: m.title.trim(),
      category: 'డెస్క్',
      script: [m.title.trim().replace(/[.।]?$/, '.'), m.summary.trim()].filter(Boolean).join(' '),
      ticker: m.title.trim(),
      breaking: !!m.breaking,
      source: 'TV24 Desk',
    }))
  const stories = [...desk, ...DEMO_STORIES.map((s) => ({ ...s, breaking: false, source: 'TV24 Demo Desk' }))]
    .slice(0, maxStories)
    .sort((a, b) => Number(b.breaking) - Number(a.breaking))
    .map((s) => ({ ...s, id: uid(), kind: 'story', audio_url: null, link: '' }))

  const heads = stories.slice(0, 3).map((s) => `${s.headline}.`).join(' ')
  const intro = {
    id: uid(),
    kind: 'intro',
    headline: `${CHANNEL} వార్తలు`,
    category: 'ముఖ్యాంశాలు',
    script: `${greeting()}. ${CHANNEL} వార్తలకు స్వాగతం. ముందుగా ఈ గంట ముఖ్యాంశాలు. ${heads}`,
    audio_url: null,
    source: '',
  }
  const outro = {
    id: uid(),
    kind: 'outro',
    headline: 'ధన్యవాదాలు',
    category: CHANNEL,
    script: `ఇవీ ఈ గంట ముఖ్య వార్తలు. మరిన్ని తాజా వార్తల కోసం ${CHANNEL} యూట్యూబ్ ఛానల్‌ను సబ్‌స్క్రైబ్ చేయండి. ధన్యవాదాలు.`,
    audio_url: null,
    source: '',
  }
  return {
    id: uid(),
    mode: { collector: 'demo', editor: 'demo', voice: 'browser' },
    ticker: stories.map((s) => s.ticker),
    rundown: [intro, ...stories, outro],
    log: [
      { agent: 'Studio', level: 'warn', message: 'Agent server offline — running the in-browser demo bulletin' },
      { agent: 'Collector', level: 'info', message: `${stories.length} demo/desk stories loaded` },
      { agent: 'Director', level: 'info', message: `Rundown locked: intro + ${stories.length} stories + outro` },
      { agent: 'Anchor', level: 'info', message: 'Reading with the browser voice' },
    ],
  }
}

// Split a script into caption-sized sentences.
export function splitSentences(text) {
  return (text || '')
    .split(/(?<=[.!?।])\s+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

// Bulletins rendered offline (python -m app.render build) live in
// public/bulletins/ and play as pre-made anchor videos — no server needed.
export async function loadRenderedIndex() {
  try {
    const r = await fetch('/bulletins/index.json', { cache: 'no-cache' })
    if (!r.ok || !(r.headers.get('content-type') || '').includes('json')) return []
    const list = await r.json()
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

export async function loadRenderedBulletin(id) {
  const r = await fetch(`/bulletins/${id}/bulletin.json`, { cache: 'no-cache' })
  if (!r.ok) throw new Error(`Bulletin ${id} not found`)
  const b = await r.json()
  return {
    ...b,
    mode: { ...(b.mode || {}), video: 'rendered' },
    log: [{ agent: 'Studio', level: 'info', message: `Playing the rendered bulletin of ${new Date(b.created_ts * 1000).toLocaleString('en-IN')}` }],
  }
}
